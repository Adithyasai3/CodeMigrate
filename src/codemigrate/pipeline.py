"""End-to-end scan: analyze -> retrieve -> reason -> validate -> patch."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from codemigrate.analysis.repo_scanner import iter_sources, scan_sources
from codemigrate.config import get_settings
from codemigrate.kb.schema import KBEntry, load_kb
from codemigrate.llm import get_client
from codemigrate.llm.base import LLMClient
from codemigrate.llm.reasoner import ReasonerStats, reason_grounded, reason_llm_only
from codemigrate.patching.fixer import make_patch
from codemigrate.retrieval import build_retriever
from codemigrate.retrieval.base import Retriever
from codemigrate.retrieval.exact import method_names, template_names
from codemigrate.schemas import Evidence, FindingStatus, ScanResult, ValidatedFinding
from codemigrate.validation.citation_validator import CitationValidator, accept_all

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SystemConfig:
    """One configuration of the system under test (also used for ablations)."""

    name: str = "full"
    retriever: str = "hybrid"
    top_k: int = 5
    use_retrieval: bool = True  # False -> LLM-only (system B)
    use_validator: bool = True  # False -> system C
    provider: str = "offline"
    model: str | None = None
    temperature: float = 0.0
    seed: int | None = 0
    make_patches: bool = True


@lru_cache(maxsize=1)
def default_kb() -> tuple[KBEntry, ...]:
    return tuple(load_kb(get_settings().kb_path))


_RETRIEVERS: dict[tuple[str, tuple[str, ...]], Retriever] = {}


def _retriever(name: str, kb: tuple[KBEntry, ...]) -> Retriever:
    """Build (once per KB content) a retriever; dense models are expensive to load."""
    key = (name, tuple(e.id for e in kb))
    if key not in _RETRIEVERS:
        _RETRIEVERS[key] = build_retriever(name, list(kb))
    return _RETRIEVERS[key]


class Pipeline:
    def __init__(
        self,
        config: SystemConfig,
        kb: list[KBEntry] | None = None,
        client: LLMClient | None = None,
        rejected_log: Path | None = None,
    ) -> None:
        self.config = config
        self.kb = tuple(kb) if kb is not None else default_kb()
        self.client = client or get_client(config.provider, config.model)
        self.retriever = _retriever(config.retriever, self.kb) if config.use_retrieval else None
        self.methods = method_names(list(self.kb))
        self.templates = template_names(list(self.kb))
        self.rejected_log = rejected_log

    def scan_path(self, path: Path, from_version: str, to_version: str) -> ScanResult:
        """Scan a directory, file or zip."""
        return self.scan_sources(list(iter_sources(path)), from_version, to_version)

    def scan_sources(
        self, sources: list[tuple[str, str]], from_version: str, to_version: str
    ) -> ScanResult:
        """Scan in-memory (path, text) pairs."""
        t0 = time.perf_counter()
        cfg = self.config
        files = scan_sources(iter(sources), self.methods, self.templates)
        stats = ReasonerStats()
        validator = CitationValidator(list(self.kb), from_version, to_version, self.rejected_log)
        kb_by_id = {e.id: e for e in self.kb}
        result = ScanResult(from_version=from_version, to_version=to_version, system=cfg.name)
        result.files_scanned = len(files)
        for f in files:
            if f.error:
                result.file_errors[f.path] = f.error
            result.refs_found += len(f.refs)
            source = f.source or ""
            if not cfg.use_retrieval:
                if f.error or not f.path.endswith(".py"):
                    continue
                findings = reason_llm_only(
                    self.client,
                    f.path,
                    source,
                    from_version,
                    to_version,
                    cfg.temperature,
                    cfg.seed,
                    stats,
                )
                result.findings.extend(accept_all(x, kb_by_id) for x in findings)
                continue
            evidences = []
            for ref in f.refs:
                hits = self.retriever.search(ref, cfg.top_k, from_version, to_version)
                if hits:
                    evidences.append(Evidence(ref=ref, entries=hits))
            if not evidences:
                continue
            findings = reason_grounded(
                self.client,
                f.path,
                source,
                evidences,
                from_version,
                to_version,
                cfg.temperature,
                cfg.seed,
                stats,
            )
            for finding in findings:
                if not cfg.use_validator:
                    result.findings.append(accept_all(finding, kb_by_id))
                    continue
                vf = validator.validate(finding, evidences)
                if vf.status is FindingStatus.VERIFIED:
                    if cfg.make_patches:
                        vf.patch = make_patch(source, vf, f.path)
                    result.findings.append(vf)
                else:
                    result.rejected.append(vf)
        result.findings = _dedupe(result.findings)
        result.llm_calls = stats.calls - stats.cached
        result.cached_calls = stats.cached
        result.prompt_tokens = stats.prompt_tokens
        result.completion_tokens = stats.completion_tokens
        tracker = self.client.tracker
        result.cost_usd = (
            stats.prompt_tokens * tracker.price_in_per_mtok
            + stats.completion_tokens * tracker.price_out_per_mtok
        ) / 1e6
        result.latency_s = time.perf_counter() - t0
        return result


def _dedupe(findings: list[ValidatedFinding]) -> list[ValidatedFinding]:
    """One finding per (file, line, symbol); citations are merged."""
    merged: dict[tuple, ValidatedFinding] = {}
    for f in findings:
        key = (f.file, f.line, f.symbol)
        if key in merged:
            m = merged[key]
            m.cited_ids = list(dict.fromkeys(m.cited_ids + f.cited_ids))
            known = {e.id for e in m.evidence}
            m.evidence += [e for e in f.evidence if e.id not in known]
            m.source_urls = sorted(set(m.source_urls) | set(f.source_urls))
        else:
            merged[key] = f
    return sorted(merged.values(), key=lambda f: (f.file, f.line, f.symbol))
