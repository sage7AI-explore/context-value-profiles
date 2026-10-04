# REVIEW: Paper 03 "Context That Pays" (final state, 2026-10-03)

## Rules checklist
| Rule | Status | Evidence |
|---|---|---|
| No hand-typed result numbers | PASS | `check_paper.py` scans sections: every number is a `\R` macro from `results/processed/numbers.json`; tables and excerpts are generated (`paper/generated/`) |
| Real references only, DOI-resolving, abstracts read | PASS | `refs/VERIFY_REPORT.md`: 42/42 Crossref/DataCite + doi.org; `refs/abstracts/` |
| Local and free only | PASS | Ollama 0.35.0 (qwen3:4b-instruct, qwen3:8b, nomic-embed-text); no paid API |
| Pre-registration before test | PASS | `PLAN.md` commit 4c6491b (originally 944b921; see COMMIT_MAP.md) precedes all test manifests (`results/VERIFICATION.md`) |
| Honest reporting | PASS | H1 failure in the abstract; deviations in `PLAN.md` and the paper; `results/FAILED_RUNS.md` |
| Independent recomputation | MATCH | `results/RECOMPUTE.md` (161 quantities, incl. addendum) |
| Audit + reviewer | Done | `results/AUDIT.md` (16 issues fixed), `results/REVIEWS.md` (13 text requests addressed) |
| Format | PASS | IEEE Access-style template (accessstyle.sty), 12 pages, no IEEE logo |

## Number → macro → source (key results)
| Claim | Macro | Source |
|---|---|---|
| H1 diffs −0.025 / −0.053 / +0.007 | `\RHOne{Facts,History,Tool}Diff` | `results/processed/tests.csv` |
| Token cut at 8k 30.9% / 6.9% / 34.9% | `\RTokCut*` | `h1b.csv` |
| H2 pooled +0.003 | `\RHTwoPooledDiff` | `tests.csv` |
| H3 0.000 [0, 0], 240 pairs | `\RTransfer*` | `transfer.csv`, raw `transfer_8b_*` |
| Gold-session recall 64% vs 94% | `\RRecallOurs`, `\RRecallRel` | `history_recall.csv` |
| Profile values, CIs | `generated/profile_table.tex` | `profiles.csv` |
All other macros list their source in a comment in `paper/generated/numbers.tex`.

## Known weaknesses (stated in the paper)
Primary hypothesis failed; the 8k budget is non-binding (H1b is pruning); no relevance-with-stopping-rule baseline;
history is at ceiling from 2k; transfer outcomes are insensitive to the profile; one model family; single-decision
tasks; a checker defect was found after the test runs (disclosed, no effect on the hypothesis differences).

## Reproduce
`make all` (env → test → data → experiments → results → verify → figures → numbers → refs → paper → check), then
`make arxiv`. Experiments are cached in `results/cache/`. Without the cache they take about 17 h on an Apple-silicon
laptop.

## Compute used
About 20 h of local inference over 2026-10-02/03 (profiling, pilots, 6,180 main and 720 transfer episodes); $0 spent.
