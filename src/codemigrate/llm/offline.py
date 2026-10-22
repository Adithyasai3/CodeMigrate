"""Deterministic offline 'LLM': applies fixed rules to the structured prompt payload.

It never sees anything the real LLM doesn't (it parses the same prompt), uses no network,
and is reported as its own system so its numbers are never mixed with LLM numbers.

Rules for grounded prompts: for each reference, cite every retrieved evidence entry that
  * names the referenced symbol (``exact_match``, computed by validation.matching), and
  * is a removed/deprecated/renamed change (behavior changes aren't flagged), and
  * if the entry is about a specific argument, the call actually passes that argument.
For LLM-only prompts it returns no findings (there is no knowledge without evidence).
"""

from __future__ import annotations

import json
import re

from codemigrate.llm.base import LLMClient, LLMResponse
from codemigrate.llm.prompts import extract_payload

FLAGGED_TYPES = {"removed", "deprecated", "renamed"}
_ARG_RE = re.compile(
    r"\b(?:the\s+)?(\w+)\s+(?:argument|parameter|keyword argument)s?\b|"
    r"passing\s+(\w+)=",
    re.I,
)
_POSITIONAL_RE = re.compile(r"positional arguments?", re.I)


def argument_condition(description: str) -> tuple[str, set[str]] | None:
    """Return ("kwarg", names) / ("positional", set()) if an entry concerns call arguments."""
    if _POSITIONAL_RE.search(description):
        return ("positional", set())
    names = {a or b for a, b in _ARG_RE.findall(description) if (a or b)}
    names -= {"the", "an", "a", "keyword", "positional", "new", "second", "first", "this"}
    return ("kwarg", names) if names else None


def applies(ref: dict, ev: dict) -> bool:
    """Deterministic applicability check for one evidence entry against one reference."""
    if ev["change_type"] not in FLAGGED_TYPES or not ev.get("exact_match"):
        return False
    cond = argument_condition(ev["description"])
    if cond is None:
        return True
    if ref["kind"] not in {"call", "method"}:
        return False  # an import or attribute access doesn't use the argument
    kind, names = cond
    if kind == "positional":
        return (ref.get("positional_args") or 0) > 0
    return bool(names & set(ref.get("keyword_args") or []))


class OfflineClient(LLMClient):
    provider = "offline"

    def __init__(self, model: str = "rules-v1", **kw) -> None:
        kw.setdefault("min_interval_s", 0.0)
        super().__init__(model, **kw)

    def _call(self, system, prompt, temperature, seed, json_mode) -> LLMResponse:
        payload = extract_payload(prompt)
        findings = []
        if payload.get("task") == "grounded":
            for ref in payload["references"]:
                cited = [ev for ev in ref["evidence"] if applies(ref, ev)]
                if not cited:
                    continue
                top = cited[0]
                findings.append(
                    {
                        "ref_id": ref["ref_id"],
                        "line": ref["line"],
                        "symbol": ref["symbol"]
                        if not ref["symbol"].startswith("*.")
                        else top["api"],
                        "change_type": top["change_type"],
                        "explanation": top["description"],
                        "suggested_fix": f"Use {top['replacement']}" if top["replacement"] else "",
                        "cited_ids": [ev["id"] for ev in cited],
                        "confidence": 1.0,
                    }
                )
        text = json.dumps({"findings": findings})
        return LLMResponse(text=text, model=self.model, prompt_tokens=0, completion_tokens=0)

    def complete(
        self, system, prompt, temperature=0.0, seed=None, json_mode=True, max_retries=1
    ) -> LLMResponse:
        """Rules are cheap and may change between runs, so results are never cached."""
        resp = self._call(system, prompt, temperature, seed, json_mode)
        self.tracker.record(resp)
        return resp
