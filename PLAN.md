# Pre-registration — Context That Pays (Paper 03)

Committed 2026-10-03 ~00:00 CDT, BEFORE any test-split run (the first test-split run in experiments/run_all.sh starts
after the dev-split 8B profiling and padding control). Later changes only in § Deviations (dated, with reason).
Note: the previous commit "PRE-REGISTRATION ..." accidentally contained the empty template (a failed file write); this
commit holds the actual plan and precedes every test-split run (verifiable from results/raw/main_4b/manifest.jsonl).

## Hypotheses (primary first)
- **H1 (primary, as specified in PROMPT.md):** On qwen3:4b-instruct, OURS (MCV + interactions) has higher per-instance AUBC
  than the best of the baselines B1–B5 (best = highest mean test AUBC in that family), paired over instances, in at least
  2 of 3 families (Holm-adjusted two-sided Wilcoxon p < 0.05 and positive mean difference).
- **H1b (co-primary, efficiency; added from dev evidence before any test run):** At the 8,000-token budget, OURS uses fewer
  measured prompt tokens than B0 (full context) and than the best baseline, while its success is non-inferior to B0 with a
  margin of 0.05 (lower bound of the 95% paired bootstrap CI of success(OURS@8k) − success(B0) > −0.05), in at least 2 of
  3 families.
- **H2:** OURS (with interaction terms) has higher AUBC than OURS-A (additive), pooled over families (paired Wilcoxon).
- **H3 (transfer):** On qwen3:8b, the 4B-measured profile applied unchanged (OURS-T) is non-inferior to the 8B-measured
  profile (OURS-native; same 4B block-value model) with margin 0.05 in success, pooled over families and budgets
  (lower 95% CI bound of OURS-T − OURS-native > −0.05). Also reported: Spearman rho between 4B and 8B type MCVs.

## Primary metric and decision rules
- AUBC: per-instance normalized trapezoid area of success over log2(budget), budgets {1000, 2000, 4000, 8000}; B0 counts
  as constant across budgets. Success: deterministic checkers (BFCL-style AST match; normalized answer match).
- Holm family: H1 (3 families) + H1b (3 families) + H2 (1 pooled). H3 is CI-based and reported separately.
- If H1 fails, the abstract says so.

## Conditions
- B0 full context; B1 truncate-oldest; B2 embedding relevance top-k (nomic-embed-text); B3 LLMLingua-2 (bert-base
  multilingual meetingbank model); B4 PACMS-style coverage (re-implementation); B5 tier rules; OURS-A; OURS; OURS-T;
  OURS-native (8B type profile, 4B block-value model).
- Method frozen at commit "Freeze method: restore v2 block values" (block values = ridge regression on dev
  leave-one-block-out deltas with features incl. embedding similarity; type-pair interactions from the profile).

## Models
qwen3:4b-instruct (primary, profiling source) and qwen3:8b (transfer target); digests in results/raw/*/manifest.jsonl.
Greedy decoding (temperature 0), seed 0, num_ctx 16384, num_predict 96, thinking disabled.

## Data and splits
- data/processed/instances.jsonl + TEST.lock (hashes there): 3 families x 300; dev 60 / test 240 per family.
- Profiling: dev 1–40 (4B, with leave-one-block-out); dev 1–20 (8B, type level). Pilots: dev 41–60.
- Test subsets (deterministic: first n test instances per family in file order, itself a seeded shuffle):
  main grid n = 100 per family for B0, B2, B4, OURS-A, OURS; weak baselines B1, B3, B5 on the first 30 per family;
  transfer (8B) on the first 40 per family with policies B2, OURS-T, OURS-native at budgets {2000, 8000}.

## Power analysis (dev pilot 2, qwen3:4b-instruct, 20 instances per family)
- H1, smallest effect of interest 0.05 AUBC; paired SD of (OURS − best baseline) AUBC: facts 0.229, history 0.122,
  tool 0.112 -> n for 80% power (two-sided alpha 0.05): 165 / 47 / 40. With n = 100: about 58% (facts), >95% (history, tool).
- H1b, margin 0.05, discordance OURS@8k vs B0 about 0.05 -> n about 124 for 80% power (one-sided alpha 0.05); with n = 100
  about 72%. Token reduction in the pilot was large (about 31–37% on facts and tools) and is not power-limited.
- Weak baselines (B1, B3, B5) were 0.10–0.45 AUBC below the best baseline in the pilot; n = 30 confirms they are not the
  best baseline; if one is the best on its 30 instances, H1 for that family uses those 30 pairs.

## Statistical tests
Paired percentile bootstrap CIs (10,000 resamples, by instance), Wilcoxon signed-rank (zsplit) and paired sign-flip
permutation tests, effect size d_z, Holm correction as above. Independent recomputation must match exactly.

## Exclusion rules
No instance exclusions. "budget_error" episodes (mandatory blocks exceed budget) are reported and counted as failures.
Prompts exceeding the budget are reported with their overshoot.

## Compute estimate and run order
8B type profiling ~2 h; padding control ~0.3 h; main 4B grid ~10 h; weak baselines ~2.5 h; 8B transfer ~2 h; total ~17 h.
Within an instance, budgets and policies are interleaved; families run sequentially.

## Deviations (all before any test-split run)
- 2026-10-02: qwen3:4b (thinking-only tag that ignores the thinking switch) replaced by qwen3:4b-instruct.
- 2026-10-02: dev iteration 1 (lexical features) -> 2 (adds embedding similarity; pilot 2) -> 3 (apportion type MCV across
  blocks; pilot 3) rejected by the pre-stated rule (mean dev AUBC v2 0.758 > v3 0.736). All pilots are reported.
- 2026-10-03 (fast plan, user-approved): mistral-nemo:12b dropped (H3 within the Qwen family only); 8B transfer reduced to
  40 instances per family and 2 budgets; one reviewer subagent instead of three.

## Deviations after the test runs (disclosed in the paper)
- 2026-10-03: transcript reading found that the tool checker compared list-valued arguments as JSON strings
  ([-1, 2] vs [-1.0, 2.0]). The pre-registered checker remains primary; code/scripts/sensitivity_checker.py rescoring
  all logged test answers with element-wise numeric comparison flips 22 episodes across all policies and changes no
  hypothesis difference at three decimals.
- 2026-10-03: H1b p-values use a one-sided paired bootstrap (the plan named no specific non-inferiority test; a shifted
  Wilcoxon is invalid for binary outcomes). The CI-based decision rule is unchanged.
- 2026-10-03: exploratory, not pre-registered, analyses of existing logs: profiling sample size, block-value model
  cross-validation, failure excerpts. Labeled as exploratory in the paper.
