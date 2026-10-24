# Novelty claims (draft — to be checked against related work)

Each claim lists the evidence in this repo and what must be checked before it goes in the paper.

| # | Claim | Evidence here | Check before claiming |
|---|---|---|---|
| 1 | LLM findings are reported only after a **deterministic** check that every citation was retrieved for that code reference, names the symbol on that line, and is in the version range. | `src/codemigrate/validation/citation_validator.py`; C vs. D ablation | Whether prior migration / RAG-for-code work validates citations against the code location, not just against the retrieved text |
| 2 | A benchmark whose labels come from **running the code** under each Django release (4.0.10–5.1.15), independent of the tool under test. | `benchmark/label_by_execution.py`, `benchmark/README.md` | Existing API-migration / breaking-change benchmarks and how they label (manual, commit-mined, compiler errors) |
| 3 | A sourced KB of 310 Django changes, every entry linked to its release-note section, with a logged auto/corrected/manual split. | `data/kb/`, `build_report.json` | Prior API-change KBs mined from changelogs / release notes |
| 4 | One hallucination metric applied identically to systems that do and don't cite. | `evaluation/metrics.py`, DECISIONS 2026-10-22 | Hallucination metrics in code-LLM evaluation |

## Not novel (state as engineering, not contribution)
- Hybrid retrieval with reciprocal rank fusion.
- AST-based import/alias resolution.
- Rename patches for mechanical changes.

## Open question
Claim 1 is only demonstrated with an LLM once systems B/C/D are run with an API key. With the
offline reasoner, C and D are identical (it never cites outside the evidence), so the offline
numbers cannot support claim 1 on their own.
