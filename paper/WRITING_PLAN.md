# Paper writing plan (cues only, you write the sentences)

One line = one sentence you write in your own words. Keep sentences short and simple.
Numbers are correct as given. It's a draft, so ~2.5–3 pages of text is enough; the tables and figures fill the rest.
Each "S" line becomes one sentence. Total: about 55 sentences.

## Abstract (6 sentences, write last)
- S1: Django upgrade → old code breaks (removed / deprecated APIs).
- S2: Existing tools: fixed rules only; LLMs make up changes.
- S3: Our tool: finds Django APIs in code → searches 310 release-note entries → LLM explains using only those → checker verifies every citation.
- S4: Test data: 235 cases, labels from actually running code on 5 Django versions.
- S5: Result: F1 0.82 vs 0.02 for django-upgrade.
- S6: Hallucinated findings 29% → 0%, accuracy almost same.

## I. Introduction (10 sentences)
- S1: Django releases often; old APIs get removed on a schedule.
- S2: So upgrading 4.0 → 5.1 can break code (ImportError, AttributeError).
- S3: Release notes list all changes but developers must check by hand.
- S4: django-upgrade / pyupgrade \cite{djangoupgrade,pyupgrade} fix only some patterns.
- S5: LLMs know more but invent changes \cite{spracklen2025package} and use old APIs \cite{wang2025deprecated}.
- S6: Our idea in one line: LLM may only use given evidence + every claim is checked by rules.
- S7–S10: Contributions C1–C4 (one sentence each, see FACTS in main.tex).

## II. Related Work (8 sentences)
- S1: Rule tools \cite{djangoupgrade,pyupgrade}: what they do, the limit.
- S2: \cite{wang2025deprecated}: LLMs suggest deprecated APIs.
- S3: \cite{liu2024codeupdatearena} + \cite{islah2024gitchameleon}: models struggle with version changes.
- S4: \cite{spracklen2025package}: LLMs invent packages (21.7% open-source).
- S5: RAG \cite{lewis2020rag}; \cite{chen2025apidocs}: API docs help code generation.
- S6: \cite{islam2025migratelib}: migration between libraries.
- S7: Gap: they generate new code / put docs in prompt; nobody checks each claim.
- S8: Ours: checks existing code + verifies each citation + labels by running code.

## III. Approach (12 sentences: 2 per subsection)
- KB: from official release notes; 310 entries; 293 auto, 13 corrected, 4 manual; Table kb.
- Code analysis: read code with libcst; find imports, aliases, settings, overridden methods.
- Retrieval: exact match + BM25 + embeddings, merged by RRF \cite{cormack2009rrf}; keep top 5 in version range.
- Reasoning: prompt has code + evidence only; JSON output; must cite entry ids; temperature 0.
- Validation: accept only if cited entry was retrieved, names the API on that line, is in range; else reject.
- Patching: only simple renames; patch must parse again.

## IV. Benchmark (5 sentences)
- S1: Task: code for 4.0, find lines that break up to 5.1.
- S2: Each case run on 5 Django versions; errors + warnings recorded with line numbers.
- S3: Positive line = breaks or warns in a later version only.
- S4: 235 cases, 168 positive lines (Table dataset); real + synthetic + negative.
- S5: Labels don't depend on our tool.

## V. Evaluation (10 sentences)
- Systems: A = existing tools, B = Gemini only, C = Gemini + RAG, D = full (ours). Model gemini-3.5-flash-lite.
- Metrics: precision, recall, F1 per line; hallucination rate.
- RQ1: D F1 0.82 vs A 0.02 / 0.00 vs B 0.71.
- RQ2: hallucination 29.4% → 5.6% → 0%; validator dropped 8 claims; F1 change not significant (p = 0.82).
- RQ3: retrievers all ~0.81, dense 0.83.
- RQ4: offline 0.1 s/case; RAG uses ~8× tokens (1,323 → 10,704); free tier.
- Error analysis: 12 missed + 24 wrong; one example (cached_property, ran fine but flagged).

## VI. Threats (4 sentences)
- Only executed lines are labelled. One framework only. One Gemini run. Few real positives (15 of 168).

## VII. Conclusion (3 sentences)
- What we built. Main result (0% hallucination, F1 0.82). Future: more libraries and models.
