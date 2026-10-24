PY ?= .venv/Scripts/python.exe
ifeq ($(OS),)
PY := .venv/bin/python
endif
SPLIT ?= test

.PHONY: install kb kb-stats test lint retrieval-bench benchmark labels dataset-card results results-dev paper api frontend up

install:
	python -m venv .venv && $(PY) -m pip install -r requirements.lock && $(PY) -m pip install -e . --no-deps

kb:                ## rebuild the knowledge base from official release notes
	$(PY) -m codemigrate.cli kb build

kb-stats:
	$(PY) -m codemigrate.cli kb stats

test:
	$(PY) -m pytest -q --cov=codemigrate --cov-report=term-missing

lint:
	$(PY) -m ruff check src tests evaluation baselines benchmark

retrieval-bench:   ## recall@k of each retriever
	$(PY) -m evaluation.retrieval_bench

benchmark:         ## benchmark inputs (no labels)
	$(PY) -m benchmark.build_benchmark

labels:            ## ground truth by execution (needs Docker)
	$(PY) -m benchmark.label_by_execution --backend docker

dataset-card:
	$(PY) -m benchmark.dataset_card

results:           ## every table/figure in results/ (uses cached LLM calls when present)
	$(PY) -m evaluation.retrieval_bench
	$(PY) -m evaluation.run_experiments --split $(SPLIT)
	$(PY) -m evaluation.plots --split $(SPLIT)
	$(PY) -m evaluation.error_analysis --split $(SPLIT)

results-dev:
	$(MAKE) results SPLIT=dev

paper:             ## needs a LaTeX install with latexmk; tables/figures come from results/
	@command -v latexmk >/dev/null 2>&1 || { echo "latexmk not found: install TeX Live / MiKTeX (TODO)"; exit 1; }
	cd paper && latexmk -pdf main.tex

api:
	$(PY) -m uvicorn codemigrate.api.main:app --reload --port 8000

frontend:
	cd frontend && npm install && npm run dev

up:
	docker compose up --build
