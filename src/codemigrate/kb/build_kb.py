"""Build the knowledge base from official Django release notes.

Pipeline (re-runnable, deterministic):
  1. fetch ``docs/releases/<v>.txt`` at a pinned commit (cached under data/kb/raw/)
  2. parse "Backwards incompatible changes", "Features deprecated" and "Features removed"
  3. turn every bullet into one or more entries; resolve names with an AST symbol index
  4. apply data/kb/manual_corrections.yaml (each override logged)
  5. write data/kb/django_changes.jsonl and data/kb/build_report.json
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from codemigrate.config import REPO_ROOT
from codemigrate.kb.schema import ChangeType, KBEntry, Provenance, Severity, save_kb
from codemigrate.kb.symbol_index import SymbolIndex, build_index
from codemigrate.kb.versions import load_sources

log = logging.getLogger(__name__)

KB_DIR = REPO_ROOT / "data" / "kb"
RAW_DIR = KB_DIR / "raw"
WHEEL_DIR = KB_DIR / "django_src"
CORRECTIONS = KB_DIR / "manual_corrections.yaml"
REPORT = KB_DIR / "build_report.json"

SECTION_PATTERNS = {
    "incompatible": re.compile(r"^Backwards incompatible changes in (\d+\.\d+)$"),
    "deprecated": re.compile(r"^Features deprecated in (\d+\.\d+)$"),
    "removed": re.compile(r"^Features removed in (\d+\.\d+)$"),
}
ROLE_RE = re.compile(r":(\w+):`~?([^`<]+?)(?:\s*<([^>]+)>)?`")
LITERAL_RE = re.compile(r"``([^`]+)``")
SUBJECT_SPLIT_RE = re.compile(
    r"\b(is|are|was|were|has been|have been|will|now|no longer|must|should|can't|cannot|"
    r"removed|deprecated|renamed|changed)\b"
)
NOISE = {
    "True",
    "False",
    "None",
    "http",
    "https",
    "GET",
    "POST",
    "INSERT",
    "DEFAULT",
    "UUID",
    "CHAR(32)",
    "[]",
    "''",
    "str",
    "int",
    "bytes",
    "dict",
    "list",
    "tuple",
    "object",
}


@dataclass
class RawItem:
    """A bullet or paragraph from a change section, before conversion to entries."""

    version: str
    section: str  # incompatible | deprecated | removed
    subsection: str
    text: str
    children: list[str] = field(default_factory=list)
    lead: str = ""  # prose like "the following are deprecated:" introducing a bullet list


# ----------------------------------------------------------------------------- fetching


def fetch_notes(version: str, url_template: str, commit: str, refresh: bool = False) -> str:
    """Return release-note text for ``version``, downloading at ``commit`` if not cached."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cached = RAW_DIR / f"{version}.txt"
    if cached.exists() and not refresh:
        return cached.read_text(encoding="utf-8")
    url = url_template.format(commit=commit, version=version)
    log.info("fetching %s", url)
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    cached.write_text(text, encoding="utf-8", newline="\n")
    return text


def ensure_wheels(index_versions: list[str]) -> None:
    """Download Django wheels (no deps) used only for static AST name resolution."""
    WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    if len(list(WHEEL_DIR.glob("*.whl"))) >= len(index_versions):
        return
    for spec in index_versions:
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-q",
            "--no-deps",
            "--only-binary=:all:",
            "--python-version",
            "3.10",
            "-d",
            str(WHEEL_DIR),
            f"django=={spec}",
        ]
        subprocess.run(cmd, check=True)


# ----------------------------------------------------------------------------- parsing


def _headings(lines: list[str]) -> list[tuple[int, str, str]]:
    """Return (line_index, title, underline_char) for RST section headings."""
    out = []
    for i in range(len(lines) - 1):
        title, under = lines[i].rstrip(), lines[i + 1].rstrip()
        if (
            title
            and under
            and len(set(under)) == 1
            and under[0] in "=-~^"
            and len(under) >= len(title)
            and not title.startswith((" ", "*", ".."))
        ):
            out.append((i, title, under[0]))
    return out


def parse_sections(version: str, text: str) -> list[RawItem]:
    """Extract bullet items (and prose items under titled subsections) from change sections."""
    lines = text.splitlines()
    heads = _headings(lines)
    items: list[RawItem] = []
    for idx, (start, title, ch) in enumerate(heads):
        if ch != "=":
            continue
        section = next((k for k, p in SECTION_PATTERNS.items() if p.match(title)), None)
        if section is None:
            continue
        end = next((h[0] for h in heads[idx + 1 :] if h[2] == "="), len(lines))
        sub_heads = {h[0]: h[1] for h in heads if start < h[0] < end and h[2] != "="}
        items.extend(_parse_block(version, section, title, lines, start + 2, end, sub_heads))
    return items


def _parse_block(version, section, title, lines, start, end, sub_heads) -> list[RawItem]:
    items: list[RawItem] = []
    subsection = title
    current: RawItem | None = None
    child: list[str] | None = None
    prose: list[str] = []
    lead = ""
    skip_until = -1

    def flush_prose() -> None:
        nonlocal prose, lead
        if prose and prose[-1].endswith(":"):
            lead = " ".join(prose)
            prose = []
            return
        # Prose only counts under a subsection whose title names code (e.g. "Using ``x``").
        if prose and "``" in subsection and section == "incompatible":
            items.append(RawItem(version, section, subsection, subsection + ". " + " ".join(prose)))
        prose = []

    i = start
    while i < end:
        line = lines[i]
        if i in sub_heads:
            flush_prose()
            current, child = None, None
            lead = ""
            subsection = sub_heads[i]
            skip_until = i + 1
            i += 2
            continue
        if i <= skip_until:
            i += 1
            continue
        stripped = line.strip()
        bullet_top = re.match(r"^[*+] (.*)", line)
        bullet_nested = re.match(r"^  [*+] (.*)", line)
        if bullet_top:
            flush_prose()
            current = RawItem(version, section, subsection, bullet_top.group(1).strip(), lead=lead)
            items.append(current)
            child = None
        elif bullet_nested and current is not None:
            current.children.append(bullet_nested.group(1).strip())
            child = current.children
        elif current is not None and line.startswith("    ") and child is not None:
            child[-1] += " " + stripped
        elif current is not None and line.startswith("  ") and stripped:
            if child is not None:  # paragraph continuation after nested list
                current.text += " " + stripped
            else:
                current.text += " " + stripped
        elif not stripped:
            if current is None:
                flush_prose()
            continue_bullet = i + 1 < end and lines[i + 1].startswith("  ")
            if not continue_bullet:
                current, child = None, None
        elif current is None and not stripped.startswith(".."):
            if prose or not line.startswith(" "):
                if not prose:
                    lead = ""
                prose.append(stripped)
        i += 1
    flush_prose()
    return items


# ----------------------------------------------------------------------------- conversion


def strip_rst(text: str) -> str:
    """Render RST roles/literals as plain text for descriptions."""
    text = ROLE_RE.sub(lambda m: (m.group(3) or m.group(2)).strip(), text)
    text = LITERAL_RE.sub(lambda m: m.group(1), text)
    text = re.sub(r"`([^`<]+?)\s*<[^>]+>`_", r"\1", text)
    text = re.sub(r"`([^`]+)`_", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Sym:
    name: str
    role: str  # literal | class | func | meth | setting | mod | attr | ...
    pos: int


def extract_symbols(text: str) -> list[Sym]:
    """Find code symbols (roles and double-backtick literals) in order of appearance."""
    syms: list[Sym] = []
    for m in ROLE_RE.finditer(text):
        target = (m.group(3) or m.group(2)).strip()
        if m.group(1) in {
            "ref",
            "doc",
            "pypi",
            "ticket",
            "rfc",
            "envvar",
            "option",
            "djadmin",
            "ttag",
            "tfilter",
            "lookup",
            "fieldlookup",
        }:
            if m.group(1) not in {"ttag", "tfilter", "djadmin"}:
                continue
        syms.append(Sym(target, m.group(1), m.start()))
    for m in LITERAL_RE.finditer(text):
        syms.append(Sym(m.group(1).strip(), "literal", m.start()))
    syms.sort(key=lambda s: s.pos)
    return [s for s in syms if _plausible(s.name)]


def _plausible(name: str) -> bool:
    n = name.removesuffix("()")
    if n in NOISE or len(n) < 2:
        return False
    if " " in n.strip() and not n.startswith("django/"):
        return False
    return bool(re.match(r"^[A-Za-z_][\w./\-]*(\(\))?$", n.strip("~.")))


def classify(section: str, text: str) -> tuple[ChangeType, Severity]:
    """Map section + wording to a change type and severity."""
    t = text.lower()
    renamed = " renamed" in t or " alias to " in t or " alias of " in t
    removed = bool(re.search(r"\b(is|are|was|were|been) removed\b|\bremoved\.$", t))
    # "Support for <a usage pattern/format> is removed" changes behavior; the API itself stays.
    if (
        removed
        and t.startswith("support for")
        and not re.search(r"argument|positional|passing|calling|parameter", t)
    ):
        removed = False
        if section == "removed":
            return ChangeType.BEHAVIOR_CHANGED, Severity.ERROR
    if section == "deprecated":
        return (ChangeType.RENAMED if renamed else ChangeType.DEPRECATED), Severity.WARNING
    if section == "removed":
        if renamed:
            return ChangeType.RENAMED, Severity.ERROR
        if removed:
            return ChangeType.REMOVED, Severity.ERROR
        return ChangeType.BEHAVIOR_CHANGED, Severity.ERROR
    if renamed:
        return ChangeType.RENAMED, Severity.ERROR
    if removed:
        return ChangeType.REMOVED, Severity.ERROR
    if "deprecat" in t:
        return ChangeType.DEPRECATED, Severity.WARNING
    return ChangeType.BEHAVIOR_CHANGED, Severity.INFO


def _split_subject(text: str) -> tuple[str, str]:
    m = SUBJECT_SPLIT_RE.search(text)
    if not m:
        return text, ""
    return text[: m.start()], text[m.start() :]


REPLACEMENT_RE = re.compile(
    r"(in favor of|renamed to|\buse\b|replaced by|alias (?:to|of))\s*",
    re.I,
)


def _replacement(text: str) -> str | None:
    """Return the first symbol directly following a replacement cue ("in favor of ``x``")."""
    for m in REPLACEMENT_RE.finditer(text):
        tail = re.sub(r"^(the|a|an)\s+", "", text[m.end() :])
        if not tail.startswith((":", "``")):
            continue
        syms = extract_symbols(tail)
        if not syms:
            continue
        name = syms[0].name.removesuffix("()").lstrip("~")
        if name == "default" or (name.islower() and "." not in name and "_" not in name):
            continue
        return name
    return None


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60] or "x"


def _setting_like(sym: Sym, text: str) -> bool:
    return sym.role == "setting" or (
        re.fullmatch(r"[A-Z][A-Z0-9_]+", sym.name) is not None and "setting" in text.lower()
    )


def make_names(sym: Sym, text: str, index: SymbolIndex) -> tuple[str, list[str], str] | None:
    """Return (affected_api, aliases, symbol_kind) for a symbol, or None if unresolvable."""
    name = sym.name.strip().lstrip("~").removesuffix("()")
    if _setting_like(sym, text):
        return f"settings.{name}", [name], "setting"
    if name.startswith("django/") or name.endswith((".html", ".txt")):
        return name, [name.rsplit("/", 1)[-1]], "template"
    if sym.role in {"ttag", "tfilter"}:
        return f"template:{name}", [name], "template"
    if sym.role == "djadmin":
        return f"manage.py {name}", [name], "other"
    name = name.lstrip(".")
    cands = index.resolve(name)
    if not cands and "." in name and not name.startswith("django."):
        head, _, tail = name.rpartition(".")
        heads = index.resolve(head)
        if heads:  # e.g. HttpRequest.is_ajax (method removed before the indexed versions)
            cands = [f"{heads[0]}.{tail}"]
    if not cands and "." not in name:
        # sibling symbol in the same sentence gives the module, e.g. "force_text() and smart_text()"
        for other in extract_symbols(text):
            o = other.name.removesuffix("()")
            if o.startswith("django.") and o.count(".") >= 2 and o.split(".")[-1] != name:
                mod = o.rsplit(".", 1)[0]
                if mod in index.modules:
                    cands = [f"{mod}.{name}"]
                    break
    if not cands and not name.startswith("django."):
        return None
    aliases: set[str] = {name, name.split(".")[-1]}
    if "." in name and not name.startswith("django."):
        aliases.add(".".join(name.split(".")[-2:]))
    if cands:
        canon = cands[0]
        for pub in index.public_paths(canon):
            aliases.add(pub)
        # A method on a re-exported class: add the public class path too.
        parts = canon.split(".")
        if len(parts) > 2:
            cls_path = ".".join(parts[:-1])
            for pub in index.public_paths(cls_path):
                aliases.add(f"{pub}.{parts[-1]}")
        affected = min([canon, *index.public_paths(canon)], key=len)
        aliases.add(canon)
        aliases.discard(affected)
        return affected, sorted(aliases), "python"
    aliases.discard(name)
    return name, sorted(aliases), "python"


def item_to_entries(item: RawItem, index: SymbolIndex, docs_url: str) -> list[KBEntry]:
    """Convert one raw item into KB entries (one per affected symbol)."""
    anchor = slugify(_section_title(item)).replace("_", "-")
    source_url = docs_url.format(version=item.version, anchor=anchor)
    targets: list[tuple[str, Sym]] = []  # (description, symbol)
    text = item.text
    if item.children:
        for c in item.children:
            csyms = extract_symbols(c)
            if csyms:
                targets.append((f"{text} {c}", csyms[0]))
    if item.lead and not targets:
        bsyms = extract_symbols(text)
        if bsyms:
            targets = [(f"{item.lead} {text}", bsyms[0])]
            text = f"{item.lead} {text}"
    if not targets:
        subject, rest = _split_subject(text)
        subj_syms = extract_symbols(subject)
        all_syms = extract_symbols(text)
        if not all_syms:
            return []
        lower = subject.lower()
        if subj_syms and re.search(r"\b(argument|parameter|kwarg)s?\b", lower):
            # "The ``x`` argument of ``f()`` is removed" -> affected is f()
            after = extract_symbols(text[len(subject) :])
            owner = [s for s in subj_syms[1:]] or after[:1]
            chosen = owner[:1] or subj_syms[:1]
        elif subj_syms and re.search(r"\b(and|,)\b", subject) and len(subj_syms) <= 4:
            chosen = subj_syms
        else:
            chosen = subj_syms[:1] or all_syms[:1]
        targets = [(text, s) for s in chosen]

    replacement = _replacement(text)
    entries = []
    for desc, sym in targets:
        change_type, severity = classify(item.section, desc)
        names = make_names(sym, desc, index)
        if names is None:
            log.info("unresolvable symbol %r in %s/%s", sym.name, item.version, item.section)
            continue
        affected, aliases, kind = names
        repl = replacement if replacement and replacement not in {affected, *aliases} else None
        if repl and kind == "python":
            repl = _qualify_replacement(repl, affected, index)
        is_argument_change = bool(re.search(r"\b(argument|parameter|kwarg)s?\b", desc, re.I))
        mechanical = (
            bool(repl)
            and change_type in {ChangeType.RENAMED, ChangeType.DEPRECATED, ChangeType.REMOVED}
            and kind == "python"
            and not is_argument_change
            and bool(re.search(r"in favor of|renamed to|alias (to|of)", desc))
        )
        entries.append(
            KBEntry(
                id=f"django-{item.version}-{item.section}-{slugify(affected)}",
                library="django",
                version_introduced=item.version,
                change_type=change_type,
                affected_api=affected,
                aliases=aliases,
                description=strip_rst(desc),
                replacement=repl,
                source_url=source_url,
                source_section=f"{_section_title(item)} / {strip_rst(item.subsection)}"
                if item.subsection != _section_title(item)
                else _section_title(item),
                severity=severity,
                provenance=Provenance.AUTO_PARSED,
                mechanical_fix=mechanical,
                symbol_kind=kind,
            )
        )
    return entries


def _qualify_replacement(repl: str, affected: str, index: SymbolIndex) -> str:
    """Turn a short replacement ("reorder_tests") into a dotted path next to ``affected``."""
    if repl.startswith(("django.", "datetime.")):
        return repl
    parent = affected.rsplit(".", 1)[0]
    if "." not in repl:
        return f"{parent}.{repl}"
    # "DatabaseOperations.lookup_cast" next to "...operations.DatabaseOperations.field_cast_sql"
    head = repl.split(".")[0]
    if f".{head}." in f".{affected}.":
        return affected[: affected.index(head)] + repl
    cands = index.resolve(repl)
    return cands[0] if cands else repl


def _section_title(item: RawItem) -> str:
    return {
        "incompatible": f"Backwards incompatible changes in {item.version}",
        "deprecated": f"Features deprecated in {item.version}",
        "removed": f"Features removed in {item.version}",
    }[item.section]


# ----------------------------------------------------------------------------- corrections


def apply_corrections(
    entries: list[KBEntry], path: Path = CORRECTIONS
) -> tuple[list[KBEntry], dict]:
    """Apply manual overrides: ``set`` fields, ``drop`` entries, ``add`` new ones. Logs each."""
    stats = {"corrected": 0, "dropped": 0, "added": 0, "unmatched": []}
    if not path.exists():
        return entries, stats
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    by_id = {e.id: e for e in entries}
    for fix in spec.get("set", []):
        e = by_id.get(fix["id"])
        if e is None:
            stats["unmatched"].append(fix["id"])
            log.warning("correction targets unknown id %s", fix["id"])
            continue
        data = e.model_dump()
        data.update(fix["fields"])
        data["provenance"] = Provenance.MANUALLY_CORRECTED
        by_id[e.id] = KBEntry.model_validate(data)
        stats["corrected"] += 1
        log.info("corrected %s: %s (%s)", e.id, list(fix["fields"]), fix.get("reason", ""))
    for drop in spec.get("drop", []):
        if by_id.pop(drop["id"], None) is None:
            stats["unmatched"].append(drop["id"])
            log.warning("drop targets unknown id %s", drop["id"])
        else:
            stats["dropped"] += 1
            log.info("dropped %s (%s)", drop["id"], drop.get("reason", ""))
    for add in spec.get("add", []):
        add = {**add, "provenance": Provenance.MANUAL}
        e = KBEntry.model_validate(add)
        by_id[e.id] = e
        stats["added"] += 1
    return list(by_id.values()), stats


# ----------------------------------------------------------------------------- driver


def verify_anchors(entries: list[KBEntry]) -> dict[str, bool]:
    """Check every distinct source_url anchor exists in the live docs page (network)."""
    results: dict[str, bool] = {}
    pages: dict[str, str] = {}
    for url in sorted({str(e.source_url) for e in entries}):
        page, _, anchor = url.partition("#")
        if page not in pages:
            try:
                with urllib.request.urlopen(page, timeout=30) as resp:
                    pages[page] = resp.read().decode("utf-8", errors="replace")
            except Exception as exc:  # noqa: BLE001 - logged and reported as invalid
                log.error("cannot fetch %s: %s", page, exc)
                pages[page] = ""
        results[url] = f'id="{anchor}"' in pages[page]
    return results


def build(refresh: bool = False, check_urls: bool = True) -> dict:
    """Run the full build and return the report dict (also written to build_report.json)."""
    cfg = load_sources()["libraries"]["django"]
    ensure_wheels(cfg["index_versions"])
    index = build_index(WHEEL_DIR)
    raw_items: list[RawItem] = []
    for v in cfg["versions"]:
        text = fetch_notes(str(v["version"]), cfg["notes_url"], cfg["commit"], refresh)
        raw_items.extend(parse_sections(str(v["version"]), text))
    entries: dict[str, KBEntry] = {}
    skipped: list[str] = []
    for item in raw_items:
        made = item_to_entries(item, index, cfg["docs_url"])
        if not made:
            skipped.append(f"{item.version}/{item.section}: {strip_rst(item.text)[:120]}")
        for e in made:
            eid, n = e.id, 2
            while eid in entries:
                eid = f"{e.id}_{n}"
                n += 1
            entries[eid] = e.model_copy(update={"id": eid})
    auto_count = len(entries)
    final, corr = apply_corrections(list(entries.values()))
    report = {
        "commit": cfg["commit"],
        "raw_items": len(raw_items),
        "items_without_code_symbol_skipped": len(skipped),
        "auto_parsed_entries": auto_count,
        "manual_corrections": corr,
        "final_entries": len(final),
        "provenance_counts": _count(final, "provenance"),
        "skipped_examples": skipped,
    }
    if check_urls:
        anchors = verify_anchors(final)
        report["source_urls_checked"] = len(anchors)
        report["source_urls_invalid"] = [u for u, ok in anchors.items() if not ok]
    save_kb(final, KB_DIR / "django_changes.jsonl")
    REPORT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log.info("KB built: %d entries (%d auto-parsed, %s)", len(final), auto_count, corr)
    return report


def _count(entries: list[KBEntry], attr: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in entries:
        k = str(getattr(e, attr).value if hasattr(getattr(e, attr), "value") else getattr(e, attr))
        out[k] = out.get(k, 0) + 1
    return out


if __name__ == "__main__":
    print(json.dumps({k: v for k, v in build().items() if k != "skipped_examples"}, indent=2))
