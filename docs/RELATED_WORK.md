# Related work: verified notes (for the team, not paper text)

Every item below was checked on its arXiv/project page on 2026-10-25. These are notes to read
from, not sentences to copy: the paper must be written in your own words (review rule:
<10% AI-generated text, <10% similarity). Read each paper before citing it. BibTeX keys refer
to `paper/refs.bib`.

## Comparison table

| Work | Task | Uses release notes / docs as evidence | Checks the LLM's claims | Labels from execution | Library |
|---|---|---|---|---|---|
| django-upgrade (tool) | rewrite code with fixed rules | no (hand-written fixers) | n/a (no LLM) | n/a | Django |
| pyupgrade (tool) | rewrite Python syntax | no | n/a | n/a | Python itself |
| Wang et al., ICSE'25 `wang2025deprecated` | measure deprecated API use in LLM *code completion*; REPLACEAPI / INSERTPROMPT baselines | INSERTPROMPT adds API info to the prompt | no | no (API mappings) | 8 Python data-science libs |
| Spracklen et al., USENIX Sec'25 `spracklen2025package` | measure *package* hallucination in generated code | mitigation incl. RAG | detects non-existent packages | no | Python, JavaScript |
| Chen et al., arXiv 2025 `chen2025apidocs` | RAG over API docs for code generation | yes (API docs) | no | no | 4 less common Python libs |
| CodeUpdateArena `liu2024codeupdatearena` | can models use synthetic API updates | update docs in prompt | no | unit tests | 7 Python packages, synthetic |
| GitChameleon `islah2024gitchameleon` | version-specific code *generation* | no | no | yes (unit tests) | Python libs |
| MigrateLib `islam2025migratelib` | migrate between *different* libraries | no | static + dynamic analysis | tests | Python |
| **CodeMigrate (ours)** | find + fix breaking API uses in *existing* code when upgrading a framework | yes: 310 sourced release-note entries | **yes: deterministic citation validator** | **yes: run under Django 4.0–5.1** | Django |

## What each one reports (numbers from the abstracts)

- **Wang et al. (ICSE 2025)**: 7 LLMs, 145 API mappings from 8 Python libraries, 28,125
  completion prompts; first evaluation of deprecated API usage in LLM completion. Usage rates are
  in the full paper (not in the abstract). https://arxiv.org/abs/2406.09834
- **Spracklen et al. (USENIX Security 2025)**: 16 code LLMs, 576,000 samples; hallucinated
  packages ≥5.2% (commercial) and 21.7% (open-source); 205,474 unique fake package names.
  https://arxiv.org/abs/2406.10279
- **Chen et al. (2025)**: RAG over API documentation improves code generation by 83%–220% on
  4 less common Python libraries (1,017 APIs); example code helps most.
  https://arxiv.org/abs/2503.15231
- **CodeUpdateArena (Liu et al.)**: 670 synthesis examples over 54 updated functions in 7
  packages; prepending update docs does *not* help open-source code LLMs use the change.
  https://arxiv.org/abs/2407.06249
- **GitChameleon (Islah et al.)**: 116 version-specific completion problems with unit tests;
  GPT-4o pass@10 39.9% (43.7% with error feedback). https://arxiv.org/abs/2411.05830
- **MigrateLib (Islam et al.)**: LLM + static + dynamic analysis for library-to-library
  migration; 32% of migrations fully correct on 717 real applications.
  https://arxiv.org/abs/2510.08810
- **django-upgrade**: rule-based rewriter ("changes code to avoid deprecation warnings and
  migrates some patterns to newer Django idioms"). https://github.com/adamchainz/django-upgrade

## How CodeMigrate differs (points to argue, with our evidence)

1. **Task.** Most LLM work above *generates* new code (completion, synthesis). We *audit existing
   code* for an upgrade and point to exact lines. Closest tool: django-upgrade, which only covers
   its hand-written fixers. Evidence: on our test split django-upgrade gets F1 0.02 vs ours 0.81
   (offline reasoner; 0.82 with Gemini); see `results/tables/comparison_test.tex`.
2. **Claims are checked, not just grounded.** Chen et al. and INSERTPROMPT put docs in the
   prompt; none verify the output. Our validator rejects any finding whose citation wasn't
   retrieved, doesn't name the symbol on that line, or is out of the version range. Evidence:
   B (LLM only) vs C (RAG, no validator) vs D (RAG + validator) hallucination rates; first
   result (gemini-3.5-flash-lite, 1 run): hallucinated findings B 29% → C 6% → D 0%,
   F1 0.71 / 0.83 / 0.82.
3. **Ground truth by execution.** Labels come from running each case under five Django releases,
   not from the tool or from API mappings. GitChameleon also executes, but for generation tasks.
4. **Every finding links to the official release note** (310 entries, auto-parsed with logged
   corrections).

## Honest limits of the comparison

- Published numbers above are on **different tasks and datasets**; they cannot go in the same
  table as ours. Use them to motivate the problem (LLMs use deprecated APIs and hallucinate) and
  to position the design, not as head-to-head scores.
- Head-to-head comparisons we can claim: django-upgrade, pyupgrade, and our own ablations
  (B/C/D, retrievers, top-k) on the same benchmark.
