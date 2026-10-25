# Related work — reading list (TODO)

> Verified papers, a comparison table and the novelty argument are in
> [RELATED_WORK.md](RELATED_WORK.md) (checked 2026-10-25). Items below are still open.

Nothing here is verified yet. For each item: find the paper, confirm venue/year/authors,
add a checked BibTeX entry with DOI to `paper/refs.bib`, and write 1–2 sentences on how
CodeMigrate differs. Do not cite anything that was not read.

## API evolution and breaking changes
- [x] seed: Dig & Johnson, "How do APIs evolve?" (JSME 2006) — in refs.bib, verify fields
- [ ] Empirical studies of breaking changes in library ecosystems (Maven, npm, PyPI)
- [ ] Studies of deprecation practice in Python libraries
- [ ] Python-specific API evolution / deprecated-API usage detection tools

## Automated migration and upgrade tools
- [ ] Rule-based rewriters: django-upgrade, pyupgrade (cite repos/docs, they are the A baselines)
- [ ] Mining migration rules from client code or library changes
- [ ] LLM-based code migration / library upgrade papers (2023–2026)

## Retrieval-augmented generation for code
- [x] seed: Lewis et al., RAG (NeurIPS 2020)
- [ ] Retrieval-augmented code generation and repair
- [ ] Documentation-grounded code generation

## Hallucination and attribution
- [ ] Hallucinated APIs / packages in code LLM output
- [ ] Citation / attribution evaluation for LLM answers

## Retrieval components (background only)
- [x] BM25 (Robertson & Zaragoza 2009), Sentence-BERT (2019), FAISS (2019), RRF (SIGIR 2009) — verify

## Benchmarks
- [ ] Benchmarks for API migration / breaking-change detection and how they obtain labels
