# Context That Pays: Ablation-Calibrated Marginal Context Value Profiles for Budgeted Context Assembly

Venkata Sangaraju (Independent Researcher) and Sudhir Vissa (SAGE7 AI)

Code, data adapters, pre-registration, logs of every model call, and the scripts that regenerate every number, table
and figure in the paper.

## What the paper finds
LLM agents assemble prompts from heterogeneous context (tool schemas, documents, examples, notes, history) under a
token budget. We separate three questions:
- **Type value:** which context types matter for a model and task family.
- **Block relevance:** which blocks matter for an instance.
- **Budget allocation:** what to send.

*Marginal context value (MCV) profiles* answer the first question by counterfactual ablation; a CP-SAT compiler
handles the third. In a pre-registered, fully local evaluation (Qwen3-4B/8B via Ollama; HotpotQA, BFCL, synthetic
history):
- **The primary hypothesis failed.** MCV did not beat embedding relevance at block selection. Single-block deletions
  were too sparse to train a block ranker, which leaned on recency and length.
- **The profiles were informative as diagnostics.** Value concentrates in tool schemas, documents and history; worked
  examples carry little individual value; shortened tool schemas lose most of theirs.
- **Token savings are a stopping effect.** In a pre-specified follow-up, relevance with a calibrated stopping rule
  pruned 83% of tool-use tokens with non-inferior success. A hybrid (profile admits types, relevance ranks blocks) did
  not beat relevance.

Plain-language summary of every experiment: [`EXPERIMENTS_SUMMARY.md`](EXPERIMENTS_SUMMARY.md).

## Layout
| Path | Contents |
|---|---|
| `code/mcv/` | package: typed block IR, profiler, estimator, block-value model, CP-SAT compiler, policies |
| `code/scripts/` | analysis, independent recomputation, verification, figures, tables, paper checks |
| `code/tests/` | unit tests |
| `data/` | instance builders' output (`processed/instances.jsonl`, locked split `TEST.lock`), licenses |
| `PLAN.md` | pre-registration and Addendum A, with dated deviations |
| `experiments/` | exact run scripts |
| `results/raw/` | every model call: selection, reply, success, token counts, solver certificate, run manifests |
| `results/processed/` | all tables and `numbers.json` (the source of every number in the paper) |
| `results/VERIFICATION.md`, `results/RECOMPUTE.md` | integrity checks and independent recomputation |
| `paper/` | LaTeX sources (IEEE Access-style and TMLR-style builds) |
| `COMMIT_MAP.md` | maps original commit hashes recorded in run manifests to this repository's history |

## Reproduce
```bash
cd code && uv sync
make results verify figures numbers paper   # from the repository root: analysis from the logs, no model calls
make all                                    # full pipeline incl. experiments (needs Ollama + qwen3:4b-instruct,
                                            # qwen3:8b, nomic-embed-text; about a day on an Apple-silicon laptop)
```
HotpotQA raw files are not committed (size); `make data` rebuilds the instances from the public sources.

## License
Code: MIT (`code/LICENSE`). Data: HotpotQA (CC BY-SA 4.0) and BFCL v3 (Apache-2.0) under their own licenses; see
`data/LICENSES.md`.

## Citation
Citation details will be added when the preprint is posted.
