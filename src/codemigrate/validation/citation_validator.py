"""Deterministic citation validator: "no proof, no claim".

A finding is VERIFIED only if at least one cited id
  1. exists in the KB,
  2. was retrieved as evidence for a code reference on the claimed line,
  3. is within the requested version range,
  4. denotes the claimed symbol and the code reference's symbol (validation.matching).
Findings with no valid citation are UNSUPPORTED_CLAIM (no citation, unknown id, or id not in
the evidence for that line). Findings whose citations exist but fail the line/symbol/version
checks are UNVERIFIED. Every rejection is logged with its reason.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from codemigrate.kb.schema import KBEntry
from codemigrate.kb.versions import in_range
from codemigrate.schemas import Evidence, Finding, FindingStatus, ValidatedFinding
from codemigrate.validation.matching import symbol_matches

log = logging.getLogger(__name__)


class CitationValidator:
    def __init__(
        self,
        kb: list[KBEntry],
        from_version: str,
        to_version: str,
        rejected_log: Path | None = None,
    ) -> None:
        self.kb = {e.id: e for e in kb}
        self.from_version = from_version
        self.to_version = to_version
        self.rejected_log = rejected_log

    def validate(self, finding: Finding, evidences: list[Evidence]) -> ValidatedFinding:
        """Classify one finding against the evidence retrieved for its file."""
        on_line = [ev for ev in evidences if ev.ref.line == finding.line]
        retrieved = {s.entry.id for ev in on_line for s in ev.entries}
        cited = list(dict.fromkeys(finding.cited_ids))

        if not cited:
            return self._reject(finding, FindingStatus.UNSUPPORTED_CLAIM, "no citation")
        unknown = [c for c in cited if c not in self.kb]
        known = [c for c in cited if c in self.kb]
        not_retrieved = [c for c in known if c not in retrieved]
        grounded = [c for c in known if c in retrieved]
        if not grounded:
            reason = (
                f"cited ids not in KB: {unknown}"
                if unknown and not known
                else f"cited ids not retrieved for line {finding.line}: {not_retrieved + unknown}"
            )
            return self._reject(finding, FindingStatus.UNSUPPORTED_CLAIM, reason)

        problems: list[str] = []
        valid: list[KBEntry] = []
        for cid in grounded:
            e = self.kb[cid]
            if not in_range(e.version_introduced, self.from_version, self.to_version):
                problems.append(f"{cid}: version {e.version_introduced} outside range")
                continue
            if not symbol_matches(finding.symbol, e):
                problems.append(f"{cid}: claimed symbol {finding.symbol!r} does not match entry")
                continue
            if not any(symbol_matches(ev.ref.symbol, e) for ev in on_line):
                problems.append(f"{cid}: code at line {finding.line} does not reference the API")
                continue
            valid.append(e)
        if not valid:
            return self._reject(finding, FindingStatus.UNVERIFIED, "; ".join(problems))
        if unknown or not_retrieved or problems:
            log.info(
                "dropped invalid citations on %s:%d: %s",
                finding.file,
                finding.line,
                {"unknown": unknown, "not_retrieved": not_retrieved, "problems": problems},
            )
        return ValidatedFinding(
            **{**finding.model_dump(), "cited_ids": [e.id for e in valid]},
            status=FindingStatus.VERIFIED,
            evidence=valid,
            source_urls=sorted({str(e.source_url) for e in valid}),
        )

    def _reject(self, finding: Finding, status: FindingStatus, reason: str) -> ValidatedFinding:
        vf = ValidatedFinding(**finding.model_dump(), status=status, reject_reason=reason)
        log.info(
            "rejected %s %s:%d %s: %s",
            status.value,
            finding.file,
            finding.line,
            finding.symbol,
            reason,
        )
        if self.rejected_log:
            self.rejected_log.parent.mkdir(parents=True, exist_ok=True)
            with self.rejected_log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(vf.model_dump(mode="json")) + "\n")
        return vf


def accept_all(finding: Finding, kb: dict[str, KBEntry]) -> ValidatedFinding:
    """No-validator mode (system C): every claim is reported; citations are attached if they
    exist in the KB but are not checked."""
    ev = [kb[c] for c in finding.cited_ids if c in kb]
    return ValidatedFinding(
        **finding.model_dump(),
        status=FindingStatus.UNVERIFIED,
        evidence=ev,
        source_urls=sorted({str(e.source_url) for e in ev}),
    )
