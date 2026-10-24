# CodeMigrate — Phase 0 Plan

Status: phases 0–8 implemented (2026-10-24). Open: LLM runs for systems B/C/D need an API key;
`docker compose up` and `make paper` not yet run on a machine with Docker / LaTeX.

## 1. Architecture

```mermaid
flowchart LR
    subgraph Offline["Offline / build time"]
        RN[Official Django release notes<br/>4.0 … 5.2 (.txt sources)] --> P[build_kb.py<br/>scripted parser]
        P --> CORR[manual_corrections.yaml<br/>logged overrides]
        CORR --> KB[(data/kb/django_changes.jsonl)]
        KB --> IDX[Indexes: exact symbol map,<br/>BM25, MiniLM+FAISS]
    end

    subgraph Scan["Scan pipeline (pipeline.py)"]
        SRC[Repo dir / zip / pasted code] --> RS[repo_scanner<br/>skip venv, node_modules; tolerate SyntaxError]
        RS --> AST[ast_analyzer<br/>imports, aliases, attr chains,<br/>settings strings → CodeRef(symbol, line, col)]
        AST --> RET[hybrid retriever<br/>exact + BM25 + dense → RRF<br/>filter from &lt; v ≤ to]
        IDX --> RET
        RET --> EV[Evidence pack per CodeRef<br/>top-k KB entries]
        EV --> LLM[LLM reasoner<br/>evidence-only prompt, JSON schema,<br/>retry on invalid JSON]
        LLM --> VAL[citation_validator<br/>deterministic]
        EV --> VAL
        AST --> VAL
        VAL -->|VERIFIED| FIX[patching/fixer<br/>unified diff, re-parse check]
        VAL -->|rejected| LOG[(rejected_claims log<br/>→ hallucination metric)]
        FIX --> OUT[Findings: file, line, symbol,<br/>explanation, fix, diff, source_url]
    end

    subgraph LLMLayer["llm/"]
        BASE[base.LLMClient] --- A1[anthropic] & A2[openai] & A3[gemini] & A4[offline deterministic]
        CACHE[(disk cache: sha256(model+params+prompt))] --- BASE
        BUDGET[call/token/cost counter + hard cap] --- BASE
    end
    LLM --> BASE

    subgraph App["Phase 6"]
        UI[React + Vite + TS] --> API[FastAPI + JWT]
        API --> JOBS[async scan jobs<br/>PENDING→RUNNING→COMPLETED/FAILED]
        JOBS --> Scan
        API --> DB[(SQLite / Postgres via DATABASE_URL)]
    end

    subgraph Eval["Phases 4–5"]
        BENCH[benchmark cases<br/>real / synthetic / negative] --> LAB[label_by_execution.py<br/>Docker: Django 4.0 vs target, -W error]
        LAB --> GT[(labels/*.json with provenance)]
        GT --> EXP[run_experiments.py<br/>systems A–D, ablations, ≥3 seeds]
        EXP --> RES[results/: CSV, LaTeX, PNG/PDF, error_cases.md]
    end
```

## 2. Data schemas (Pydantic v2)

### KBEntry (`kb/schema.py`, one JSON line each)
| field | type | notes |
|---|---|---|
| id | str | stable, e.g. `django-5.0-removed-0012`; never reused |
| library | str | `django` (generic: any library) |
| version_introduced | str | version whose release notes contain the entry (PEP 440 compare) |
| change_type | enum | `removed` \| `deprecated` \| `behavior_changed` \| `renamed` |
| affected_api | str | canonical dotted path, e.g. `django.utils.encoding.force_text` |
| aliases | list[str] | other import paths / short names / setting names |
| description | str | text from the release note (verbatim or trimmed) |
| replacement | str \| null | canonical replacement API if one exists |
| source_url | HttpUrl | `https://docs.djangoproject.com/en/<ver>/releases/<ver>/#<anchor>` |
| source_section | str | e.g. "Features removed in 5.0" |
| severity | enum | `error` (removed/renamed → crash) \| `warning` (deprecated) \| `info` (behavior) |
| provenance | enum | `auto_parsed` \| `manually_corrected` \| `manual` (for the parse-quality log) |
| mechanical_fix | bool | replacement is a pure symbol/import rename → patcher may apply it |

Versions/libraries live in `kb/versions.py` + a data file (`data/kb/sources.yaml`: library, version, notes URL), so adding a library = adding data.

### CodeRef (analyzer output)
`file, line, col, end_col, symbol (fully resolved dotted path), raw_text, kind (import | attribute | call | setting_string | url_pattern | middleware_string), context (±3 source lines)`

### Finding (LLM output, strict JSON schema)
`symbol, line, change_type, explanation, suggested_fix, cited_ids: list[str], confidence`

### ValidatedFinding
Finding + `status: VERIFIED | UNVERIFIED | UNSUPPORTED_CLAIM`, `reject_reason`, `evidence: list[KBEntry]`, `patch: str | null`, `source_urls`.
Validator rules (deterministic): (1) every cited id ∈ retrieved evidence for that CodeRef; (2) the claimed symbol matches the entry's `affected_api`/`aliases` after alias resolution; (3) the line holds a CodeRef with that symbol; (4) entry version in range (from, to]. All pass → VERIFIED; a citation exists but the symbol/line check fails → UNVERIFIED; no valid citation → UNSUPPORTED_CLAIM. Only VERIFIED findings are reported; every rejection is logged.

### Benchmark case + label
```json
{"case_id": "syn-django-5.0-removed-0012-a", "split": "dev|test", "kind": "real|synthetic|negative",
 "files": ["case.py"], "origin": {"repo": "...", "commit": "...", "license": "...", "path": "..."},
 "labels": [{"file": "case.py", "line": 3, "symbol": "django.utils.encoding.force_text",
             "kb_id": "django-...", "evidence": "ImportError: cannot import name 'force_text'",
             "observed_under": "django==5.1.x", "baseline_ok_under": "django==4.0.x"}],
 "provenance": {"method": "execution", "docker_image": "python:3.10-slim@sha256:...", "date": "...", "script_version": "git sha"},
 "ambiguous": false, "notes": ""}
```

## 3. Key design decisions (also in DECISIONS.md)
1. **Labeling runs in Docker** (python:3.10-slim, two venvs: Django 4.0.x and the target). The host is on Python 3.13, which Django 4.0 doesn't support.
2. **What counts as ground truth by execution:** a line is positive if it runs cleanly (no warning) under 4.0 but raises ImportError/AttributeError/TypeError, or emits a `RemovedInDjango*Warning`/`RemovedAfterNextVersionWarning` attributed to that file+line, under the target with `-W error::DeprecationWarning`. Each case gets a small driver that imports the module and runs its code paths (Django settings configured in-process). `behavior_changed` entries mostly can't be detected by execution, so they are labeled with a separate `method: "manual"` flag and reported as their own slice, not mixed into the main execution-labeled numbers.
3. **Dev/test split** fixed with a seed before any system is tuned; all prompt/threshold tuning happens on dev only, and final tables use test only.
4. **Hallucination metric**: a reported finding is hallucinated if no in-range KB entry exists whose aliases match the claimed symbol, or (for citing systems) its citation doesn't support it. This uses the same deterministic matcher for every system, so A and B (which don't cite) are scored on whether their claimed change is real, and C and D also on citation accuracy.
5. **django-upgrade baseline**: it rewrites files and doesn't emit findings, so findings are derived from its diff hunks (file + changed line). This mapping is documented as a threat to validity.
6. **Offline LLM fallback** is a deterministic rule: emit a finding for every CodeRef whose top exact-match evidence matches, citing that entry. It powers the demo without keys and is reported as its own system ("D-offline").
7. Packaging: `pip` + `requirements.lock` (pinned), `pyproject.toml` with ruff/pytest config; CLI via `typer` (`codemigrate kb stats`, `codemigrate scan`).

## 4. Milestones
| Phase | Deliverable | Acceptance check |
|---|---|---|
| 0 | this plan, repo init | your OK |
| 1 | KB ≥150 sourced entries | schema test, `codemigrate kb stats`, parse log (auto vs corrected) |
| 2 | analyzer, scanner, 4 retrievers | unit tests; `make retrieval-bench` prints recall@{1,3,5} |
| 3 | LLM layer, validator, patcher, CLI scan | `codemigrate scan <p> --from 4.0 --to 5.1 --json` offline + with a key |
| 4 | ≥150 execution-labeled cases + dataset card | `make labels` rebuilds; distribution table |
| 5 | systems A–D, metrics, ablations, stats | `make results` regenerates results/ from scratch |
| 6 | API + UI | API smoke test + Playwright flow |
| 7 | docker-compose, CI, coverage ≥70%, docs | `docker compose up`, green CI |
| 8 | IEEE skeleton, outlines, NOVELTY/RELATED_WORK_TODO | builds with `make paper` (if LaTeX available, else TODO) |

## 5. Known risks
- **Execution labeling covers only executed paths.** Real repos need importable code plus minimal settings; some real files will fail for unrelated reasons (missing third-party deps). Those failures are logged and marked ambiguous, never silently dropped.
- **Release-note parsing quality**: these are RST with inconsistent phrasing; the parser extracts `:func:`/`:class:`/`:setting:` roles, and the rest goes through logged manual correction.
- **Real 4.0-era code with breaking usages may be scarce**, so the real split may be smaller than the synthetic one. I'll report the split sizes honestly.
- **LLM cost/nondeterminism**: disk cache + temperature 0 + ≥3 runs with different seeds/temperature where the provider allows it.
