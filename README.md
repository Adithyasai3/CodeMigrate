# CodeMigrate

Evidence-grounded detection of breaking API changes when upgrading Django (4.0 → 5.x).

CodeMigrate parses your code with an AST analyzer, retrieves the matching entries from a
knowledge base built from Django's official release notes, asks an LLM (or a deterministic
offline reasoner) to explain each breakage **citing only that evidence**, and then runs a
deterministic citation validator. A finding is reported only if every claim is backed by a
retrieved, in-range KB entry whose API matches the symbol on that line. Mechanical renames
come with a patch that is checked to re-parse.

```
code ─► AST analyzer ─► hybrid retrieval (exact + BM25 + dense, RRF) ─► LLM reasoner
                                     │                                     │
                     KB: 310 sourced entries                    citation validator ─► findings + patches
```

See [docs/PLAN.md](docs/PLAN.md) for the architecture and schemas, and
[docs/DECISIONS.md](docs/DECISIONS.md) for the decision log.

## Quick start

```bash
make install                         # venv + pinned deps (requirements.lock)
cp .env.example .env                 # optional: add GEMINI_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY
codemigrate scan path/to/project --from 4.0 --to 5.1          # offline reasoner if no key
codemigrate scan app.py --to 5.1 --provider gemini --json --show-rejected
codemigrate scan path/to/project --to 5.1 --write-fixed fixed/   # write updated files (inputs untouched)
codemigrate kb stats
```

**Updated code.** Besides findings, a scan returns each affected file with the fixes applied:
safe renames are always applied; with an LLM reasoner, the LLM also rewrites the remaining
lines, and that rewrite is kept only if it parses, changes little else, and a deterministic
re-scan confirms the flagged lines are fixed with nothing new flagged. Whatever is left is marked
with a `# TODO(codemigrate): ...` comment. In the web app see the **Updated code** and
**Changes** tabs (copy / download).

Web app (React UI + FastAPI, JWT auth, async scan jobs, history, compare, PDF/JSON reports):

```bash
make api                             # uvicorn on :8000 (SQLite by default) · API docs at /docs
make frontend                        # UI on http://localhost:5173, proxies /api
```

Optional, if you have Docker: `docker compose up --build` runs Postgres + API + UI
(UI on http://localhost:8080). It is not needed for anything else in this repo.

## Components

| Path | What it does |
|---|---|
| `src/codemigrate/kb/` | Parses Django 4.0–5.2 release notes (pinned commit) into `data/kb/django_changes.jsonl`; logged manual corrections |
| `src/codemigrate/analysis/` | Repo scanner + AST analyzer: imports, aliases, attribute chains, subclass methods, settings and template references |
| `src/codemigrate/retrieval/` | Exact, BM25, dense (MiniLM + FAISS) and hybrid (RRF) retrievers with version-range filtering |
| `src/codemigrate/llm/` | Gemini / Anthropic / OpenAI-compatible / offline clients, disk cache, call/cost budget |
| `src/codemigrate/validation/` | Deterministic citation validator (VERIFIED / UNVERIFIED / UNSUPPORTED_CLAIM) |
| `src/codemigrate/patching/` | Unified-diff patches for mechanical renames, rejected unless they parse |
| `src/codemigrate/api/` | FastAPI app: auth, scan jobs, reports |
| `frontend/` | React + Vite + TypeScript UI, Playwright end-to-end test |
| `benchmark/` | 235 usable cases (real / synthetic / negative), labeled **by execution** under Django 4.0–5.1 in Docker — see [benchmark/README.md](benchmark/README.md) |
| `baselines/`, `evaluation/` | Baseline systems, metrics, ablations, statistics, plots, error analysis |
| `paper/` | IEEE paper skeleton |

## Knowledge base

310 entries from Django 4.0–5.2 release notes (89 removed, 92 deprecated, 121 behavior changed,
8 renamed); 293 parsed automatically, 13 manually corrected, 4 added by hand. Every entry links
to its section of the official notes.

## Results (test split, 160 cases)

`make results` regenerates everything under `results/` (CSV, LaTeX tables in `results/tables/`,
figures in `results/figures/`, `results/error_cases.md`).

| System | Precision | Recall | F1 [95% CI] | Hallucination |
|---|---:|---:|---:|---:|
| A: django-upgrade (diff hunks) | 0.09 | 0.01 | 0.02 [0.00, 0.06] | – |
| A: pyupgrade | 0.00 | 0.00 | 0.00 | – |
| D: full pipeline, offline reasoner | 0.71 | 0.89 | 0.79 [0.72, 0.86] | 0.00 |

These rows use the deterministic offline reasoner only. The LLM systems (B: LLM without
retrieval; C/D with an LLM) need an API key; with `GEMINI_API_KEY` set,
`make results` runs them with 3 seeds and caches every call in `.cache/llm/`.
In the ablations, the dense retriever gives the best offline F1 (0.80) because it retrieves fewer
spurious entries; top-k has no effect on the offline reasoner. With the offline reasoner C and D
are identical (it never cites outside the evidence), so the validator's effect can only be
measured with an LLM.

## Development

```bash
make test     # pytest + coverage (CI fails under 70%)
make lint     # ruff
cd frontend && npx playwright test     # starts API + Vite itself
make labels   # rebuild ground truth (needs Docker)
```

CI (`.github/workflows/ci.yml`) runs lint, tests with the coverage gate, the frontend build,
the Playwright flow and the Docker image build.

## Limitations

- Ground truth only covers executed code paths; behavior-change entries are not labeled.
- django-upgrade rewrites files instead of reporting findings, so its findings are derived from
  diff hunks (a threat to validity, see DECISIONS.md).
- Only Django is in the KB, although adding a library only needs a sources entry and notes parser.

## License

MIT
