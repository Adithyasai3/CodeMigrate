# Decision Log

Format: date — decision — reason.

- 2026-10-22 — Ground-truth labeling runs in Docker (`python:3.10-slim`, one venv per Django version). — Host Python is 3.13; Django 4.0 doesn't support it (it imports the `cgi` module, which 3.13 removed). Python 3.10 runs both Django 4.0 and 5.x.
- 2026-10-22 — `pip` + pinned `requirements.lock` instead of uv/poetry. — Nothing extra to install on team machines; this is the "boring" choice.
- 2026-10-22 — `behavior_changed` cases are labeled manually, flagged `method: manual`, and reported as a separate slice. — Execution can't observe most behavior changes; mixing them in would weaken the "labels by execution" claim.
- 2026-10-22 — The dev/test split is fixed with a seed before any tuning; final numbers come from test only. — Avoids tuning on the test set.
- 2026-10-22 — Hallucination is scored with one deterministic matcher (claimed symbol vs. in-range KB aliases) for every system. — Makes the metric comparable across systems that do and don't cite.
- 2026-10-22 — django-upgrade findings are derived from its rewrite diff hunks. — The tool doesn't emit findings; this mapping is documented as a threat to validity.
- 2026-10-22 — The offline fallback is a deterministic exact-match rule and is reported as its own system. — The demo works without keys, and its numbers never get mixed with LLM numbers.
