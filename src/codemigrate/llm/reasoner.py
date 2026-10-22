"""Turn evidence (or raw code) into findings via an LLM client, with JSON retries."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from codemigrate.llm.base import LLMClient, parse_json_object
from codemigrate.llm.prompts import (
    GROUNDED_SYSTEM,
    LLM_ONLY_SYSTEM,
    grounded_prompt,
    llm_only_prompt,
)
from codemigrate.schemas import Evidence, Finding

log = logging.getLogger(__name__)
MAX_REFS_PER_PROMPT = 40


@dataclass
class ReasonerStats:
    calls: int = 0
    cached: int = 0
    invalid_json: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    errors: list[str] = field(default_factory=list)


def _ask(
    client: LLMClient,
    system: str,
    prompt: str,
    temperature: float,
    seed: int | None,
    stats: ReasonerStats,
    json_retries: int = 2,
) -> dict:
    attempt_prompt = prompt
    for attempt in range(json_retries + 1):
        resp = client.complete(system, attempt_prompt, temperature=temperature, seed=seed)
        stats.calls += 1
        stats.cached += int(resp.cached)
        stats.prompt_tokens += resp.prompt_tokens
        stats.completion_tokens += resp.completion_tokens
        stats.latency_s += resp.latency_s
        try:
            obj = parse_json_object(resp.text)
            if not isinstance(obj.get("findings", []), list):
                raise ValueError("'findings' is not a list")
            return obj
        except (ValueError, json.JSONDecodeError) as exc:
            stats.invalid_json += 1
            log.warning("invalid JSON from %s (attempt %d): %s", client.provider, attempt + 1, exc)
            attempt_prompt = (
                prompt + "\n\nYour previous answer was not valid JSON matching the schema "
                f"({exc}). Answer again with JSON only."
            )
    stats.errors.append("invalid JSON after retries")
    return {"findings": []}


def _to_findings(obj: dict, path: str, refs_by_id: dict[str, Evidence] | None) -> list[Finding]:
    out = []
    for raw in obj.get("findings", []):
        if not isinstance(raw, dict):
            continue
        line = raw.get("line")
        if (
            (line is None or not str(line).isdigit())
            and refs_by_id
            and raw.get("ref_id") in refs_by_id
        ):
            line = refs_by_id[raw["ref_id"]].ref.line
        try:
            line = int(line)
        except (TypeError, ValueError):
            log.warning("finding without usable line dropped: %s", raw)
            continue
        cited = raw.get("cited_ids") or []
        if isinstance(cited, str):
            cited = [cited]
        out.append(
            Finding(
                file=path,
                line=line,
                symbol=str(raw.get("symbol") or ""),
                change_type=str(raw.get("change_type") or ""),
                explanation=str(raw.get("explanation") or ""),
                suggested_fix=str(raw.get("suggested_fix") or ""),
                cited_ids=[str(c) for c in cited],
                confidence=float(raw.get("confidence") or 1.0)
                if _is_number(raw.get("confidence"))
                else 1.0,
            )
        )
    return out


def _is_number(x) -> bool:
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def reason_grounded(
    client: LLMClient,
    path: str,
    source: str,
    evidences: list[Evidence],
    from_version: str,
    to_version: str,
    temperature: float = 0.0,
    seed: int | None = None,
    stats: ReasonerStats | None = None,
) -> list[Finding]:
    """Systems C/D: findings restricted to retrieved evidence (one call per chunk of refs)."""
    stats = stats or ReasonerStats()
    findings: list[Finding] = []
    for start in range(0, len(evidences), MAX_REFS_PER_PROMPT):
        chunk = evidences[start : start + MAX_REFS_PER_PROMPT]
        prompt = grounded_prompt(path, source, chunk, from_version, to_version)
        obj = _ask(client, GROUNDED_SYSTEM, prompt, temperature, seed, stats)
        refs_by_id = {f"R{i}": ev for i, ev in enumerate(chunk, 1)}
        findings.extend(_to_findings(obj, path, refs_by_id))
    return findings


def reason_llm_only(
    client: LLMClient,
    path: str,
    source: str,
    from_version: str,
    to_version: str,
    temperature: float = 0.0,
    seed: int | None = None,
    stats: ReasonerStats | None = None,
) -> list[Finding]:
    """System B: the model sees only the code."""
    stats = stats or ReasonerStats()
    prompt = llm_only_prompt(path, source, from_version, to_version)
    return _to_findings(_ask(client, LLM_ONLY_SYSTEM, prompt, temperature, seed, stats), path, None)
