# Decision Log

Format: date — decision — reason.

- 2026-10-22 — Ground-truth labeling runs in Docker (`python:3.10-slim`, one venv per Django version). — Host Python is 3.13; Django 4.0 doesn't support it (it imports the `cgi` module, which 3.13 removed). Python 3.10 runs both Django 4.0 and 5.x.
- 2026-10-22 — `pip` + pinned `requirements.lock` instead of uv/poetry. — Nothing extra to install on team machines; this is the "boring" choice.
- 2026-10-22 — `behavior_changed` cases are labeled manually, flagged `method: manual`, and reported as a separate slice. — Execution can't observe most behavior changes; mixing them in would weaken the "labels by execution" claim.
- 2026-10-22 — The dev/test split is fixed with a seed before any tuning; final numbers come from test only. — Avoids tuning on the test set.
- 2026-10-22 — Hallucination is scored with one deterministic matcher (claimed symbol vs. in-range KB aliases) for every system. — Makes the metric comparable across systems that do and don't cite.
- 2026-10-22 — django-upgrade findings are derived from its rewrite diff hunks. — The tool doesn't emit findings; this mapping is documented as a threat to validity.
- 2026-10-22 — The offline fallback is a deterministic exact-match rule and is reported as its own system. — The demo works without keys, and its numbers never get mixed with LLM numbers.
- 2026-10-22 — Release notes are fetched from django/django at pinned commit 79502d0 (raw `.txt` RST), not scraped from HTML. — Same source the docs are built from; the pinned commit makes the build reproducible.
- 2026-10-22 — Short names in the notes are resolved with an AST index of Django 4.0–5.2 wheels (no imports). Symbols that can't be resolved and aren't `django.*` (e.g. `asgiref`, `TypeError`) are dropped and logged. — Avoids guessing module paths and keeps third-party dependency notes out of the API KB.
- 2026-10-22 — `source_url` points at the section anchor on docs.djangoproject.com/en/dev (sub-section anchors aren't stable). Every anchor is checked online at build time. — Gives verifiable links.
- 2026-10-22 — Gemini free tier is the primary real LLM (user choice: free only). An OpenAI-compatible adapter also covers Groq. Calls are throttled (`LLM_MIN_INTERVAL_S`) and cached on disk.
- 2026-10-22 — Manual corrections live in `data/kb/manual_corrections.yaml`, each with a reason; counts go to build_report.json. Phase 1: 293 entries auto-parsed and unchanged, 13 corrected, 4 added, 2 dropped.
- 2026-10-22 — The analyzer resolves `self.x` through the first library base class of the enclosing class (e.g. `class V(LogoutView)`), and emits overridden methods as `Base.method`. — Real Django code reaches most changed APIs through subclassing (views, test cases, backends).
- 2026-10-22 — Calls on unknown receivers are only reported for distinctive KB member names. Generic names (`save`, `iterator`, `asc`, ...) are reported only when the receiver class is known. — Precision; documented as a recall limitation.
- 2026-10-22 — The retrieval benchmark derives queries from KB usage snippets, so it favors exact matching. It's reported as a sanity check; the end-to-end benchmark is the main evidence.
- 2026-10-22 — The offline reasoner parses the same prompt payload the LLM gets, and cites retrieved entries whose names match the referenced symbol. Behavior changes aren't flagged, and argument-specific entries only count when the call passes that argument. It's never cached.
- 2026-10-22 — "Support for <usage pattern> is removed" (no argument or call involved) is classified as `behavior_changed`. — The API still exists, and running the code doesn't fail.
- 2026-10-22 — Systems C and D share the same LLM outputs; D applies the validator after the fact. — This isolates the validator's effect and halves LLM calls (free-tier limits).
- 2026-10-22 — The patcher only handles same-parent renames and cross-module moves to an importable path, and rejects any patch that doesn't parse. — No patch is better than a wrong one.
- 2026-10-24 — Dunder method names (`__str__` etc.) are never treated as distinctive on unknown receivers; overrides are still reported when the class has a known library base. — `def __str__` in unrelated classes matched the removed `SitemapIndexItem.__str__`. Spotted in the test-split error analysis, confirmed on dev (same FP pattern) before changing; dev and test were then rerun from scratch.
