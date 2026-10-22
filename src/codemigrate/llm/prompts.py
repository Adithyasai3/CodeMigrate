"""Prompt templates. Inputs are embedded as a JSON block so every client sees identical data."""

from __future__ import annotations

import json

from codemigrate.schemas import Evidence
from codemigrate.validation.matching import symbol_matches

PAYLOAD_START = "<<<INPUT_JSON"
PAYLOAD_END = "INPUT_JSON>>>"

FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ref_id": {"type": "string"},
                    "line": {"type": "integer"},
                    "symbol": {"type": "string"},
                    "change_type": {"type": "string"},
                    "explanation": {"type": "string"},
                    "suggested_fix": {"type": "string"},
                    "cited_ids": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": ["line", "symbol", "explanation", "cited_ids"],
            },
        }
    },
    "required": ["findings"],
}

GROUNDED_SYSTEM = """You audit Python code for breaking API changes when upgrading Django.
Rules:
1. Use ONLY the evidence entries given for each code reference. Do not use outside knowledge.
2. Report a finding only if an evidence entry clearly applies to the code at that line
   (same API; if the entry is about a specific argument or usage pattern, the code must
   actually use it).
3. Every finding must cite the id(s) of the evidence entries that support it in "cited_ids".
4. If no evidence applies, return {"findings": []}.
Return JSON only, matching this schema:
""" + json.dumps(FINDINGS_SCHEMA)

LLM_ONLY_SYSTEM = """You audit Python code for breaking API changes when upgrading Django.
List every line that will break or emit a deprecation warning when upgrading between the
given versions. Return JSON only: {"findings": [{"line": int, "symbol": "fully.qualified.api",
"change_type": "removed|deprecated|renamed|behavior_changed", "explanation": str,
"suggested_fix": str, "cited_ids": []}]}. Return {"findings": []} if nothing breaks."""


def numbered(source: str, max_lines: int = 400) -> str:
    lines = source.splitlines()
    shown = lines[:max_lines]
    body = "\n".join(f"{i:>4}| {line}" for i, line in enumerate(shown, 1))
    if len(lines) > max_lines:
        body += f"\n... ({len(lines) - max_lines} more lines omitted)"
    return body


def grounded_prompt(
    path: str, source: str, evidences: list[Evidence], from_version: str, to_version: str
) -> str:
    """Prompt with code refs and their retrieved evidence (systems C and D)."""
    payload = {
        "task": "grounded",
        "file": path,
        "from_version": from_version,
        "to_version": to_version,
        "references": [
            {
                "ref_id": f"R{i}",
                "line": ev.ref.line,
                "symbol": ev.ref.symbol,
                "kind": ev.ref.kind.value,
                "code": ev.ref.raw_text,
                "positional_args": ev.ref.call_args,
                "keyword_args": ev.ref.call_kwargs,
                "evidence": [
                    {
                        "id": s.entry.id,
                        "version": s.entry.version_introduced,
                        "change_type": s.entry.change_type.value,
                        "api": s.entry.affected_api,
                        "description": s.entry.description,
                        "replacement": s.entry.replacement,
                        "retrieval_score": round(s.score, 4),
                        "retriever": s.retriever,
                        "exact_match": symbol_matches(ev.ref.symbol, s.entry),
                    }
                    for s in ev.entries
                ],
            }
            for i, ev in enumerate(evidences, 1)
        ],
    }
    return (
        f"Upgrade: Django {from_version} -> {to_version}\nFile: {path}\n\n"
        f"Source (line numbers on the left):\n{numbered(source)}\n\n"
        f"Code references and retrieved evidence:\n{PAYLOAD_START}\n"
        f"{json.dumps(payload, indent=1)}\n{PAYLOAD_END}\n"
    )


def llm_only_prompt(path: str, source: str, from_version: str, to_version: str) -> str:
    """Prompt with code only (system B)."""
    payload = {
        "task": "llm_only",
        "file": path,
        "from_version": from_version,
        "to_version": to_version,
    }
    return (
        f"Upgrade: Django {from_version} -> {to_version}\nFile: {path}\n\n"
        f"Source (line numbers on the left):\n{numbered(source)}\n\n"
        f"{PAYLOAD_START}\n{json.dumps(payload)}\n{PAYLOAD_END}\n"
    )


def extract_payload(prompt: str) -> dict:
    start = prompt.index(PAYLOAD_START) + len(PAYLOAD_START)
    end = prompt.index(PAYLOAD_END)
    return json.loads(prompt[start:end])
