# Independent audit (paper 03)

**Verdict: PASS-WITH-FIXES.** Every number checked traces correctly to the logs. Test data was not used for fitting: the profile and value model come only from `profile_qwen3-4b-instruct` (dev), and the main runs were made at the pre-registration commit 944b921. PLAN.md changes since then are append-only. Holm runs over 7 tests, as pre-registered. Several sentences are contradicted by the logs, though, and the PDF currently has undefined macros.

1. **Major: the PDF is built from stale macros.** limits.tex:34-35 uses `\RCheckerFlips` and `\RSensHOneTool`. Both are in numbers.json but missing from paper/generated/numbers.tex (written 10:35, before numbers.json at 10:41), and main.log reports "Undefined control sequence". *Fix:* rerun export_paper_numbers.py, rebuild the PDF, and add a check that fails on undefined macros.

2. **Major: "Blocks with non-positive predicted value are never selected" is false for OURS.** Affected text: design.tex:50-51, intro.tex:36-37 and 50-51, eval.tex:110, limits.tex:8. Recomputing predicted values for the logged selections (cached embeddings only, no Ollama calls) found 300 selected blocks with value ≤ 0 under OURS and 0 under OURS-A. At 8k, plans with a strictly negative block: facts 15/100, tool 23/100 (examples pulled in by the positive interaction terms). History 63/100 contain zero-valued blocks, which the solver is indifferent to. *Fix:* state the property for OURS-A only, or add constraints x=0 for v≤0 (and a tie-break penalty).

3. **Major: H2 text is contradicted by the selections.** eval.tex:139-141 says the additive compiler "drops the note anyway" and that interactions don't change the compiler's choices. In fact OURS-A keeps the note in 49/100 history plans at 4k/8k, while OURS drops it. Selections differ between OURS and OURS-A in 121/400 (facts), 198/400 (history) and 89/400 (tool) plans. Only AUBC is unchanged. *Fix:* say the choices changed but success did not.

4. **Major: "MCV drops worked examples" / "dead weight in every family" is overstated.** Affected text: Fig. 5 caption (eval.tex:131-132), limits.tex:5, abstract:13-14. OURS includes examples in 100% of facts plans and 76% of tool plans at 8k (mean example tokens 31 of 67 and 50 of 186). The 4B facts profile has example|fact interaction +0.10 with CI [0.025, 0.20], so examples are complementary with documents there. The 8B history example value is 0.10 [0, 0.25], which contradicts "hold across … models" (eval.tex:144). *Fix:* say "reduces", and qualify for facts and 8B.

5. **Major: "without model calls" is not accurate.** Affected text: abstract:7, intro:17, Fig. 1 caption, eval.tex:224. Planning computes nomic-embed-text embeddings (features.py `block_features`). The 6.9 ms median comes from cache hits. *Fix:* say "without LLM calls (one embedding call per block, cached)" and report the uncached planning time.

6. **Major: H3 is claimed on incomplete, facts-only data.** Affected text: eval.tex:172-177, Fig. 4 caption, Tab. 2 line 76, abstract:15, limits:41-42. `RTransferN` = 80 = facts only (2 budgets × 40); there are no native history or tool runs yet, so "pooled over families" isn't met. `\RHThreeVerdict` is auto-set and could flip. The 8B history profile differs (examples 0.10, note 0.05), so "this is expected" may not hold for history. *Fix:* gate the H3 text on complete runs, or label it interim with the families covered.

7. **Minor: "did not exceed it anywhere" (abstract:10, eval.tex:83, conclusion:4).** On tool, OURS − B2 = +0.007. *Fix:* "did not significantly exceed".

8. **Minor: "beat the other baselines by wide margins at small budgets" (eval.tex:88) is overgeneralized.** On history at 1k, OURS scored 64% against 70% for B1 and B5. In AUBC, OURS (0.937) is below B1 and B5 (0.950) on history and below B3 on facts (0.550 vs 0.556). *Fix:* restrict the claim to tool, and to facts at 1k.

9. **Minor: "The entire history gap arises at 1k" (eval.tex:94).** The 1k budget contributes −0.050 of −0.053; 2k is 99% vs 100%. *Fix:* "almost entirely".

10. **Minor: wrong denominator for over-budget prompts (eval.tex:33-34).** `\RBudgetedEpisodes` = 6,201, which includes 321 incomplete 8B transfer episodes. All 34 overshoots are in the 4B main runs (5,880 budgeted episodes). *Fix:* use the main runs only (analyze_extra.py around the `ROverBudget` lines).

11. **Minor: ρ = 0.88 is pooled over 7 (family, type) pairs (intro:42, eval.tex:171).** Between-family scale dominates it, and agreement within families is untested. *Fix:* caveat it, or report the per-family pattern.

12. **Minor: the sensitivity claim is broader than what was checked (limits.tex:34-35).** "Every pre-registered paired difference unchanged": sensitivity_checker.py checks only the H1 and H1b mean differences, not H2, H3, CIs or p-values. *Fix:* narrow the wording or extend the script.

13. **Minor: number formatting.** "lost by \RHOneHistoryDiff" (abstract:11) prints "lost by -0.053", a double negative. Holm p prints as "0.000". *Fix:* use the absolute value, and write "<0.001".

14. **Minor: padding is not exactly length-equal.** Filler is "approximately equal" in length (ablate.py:53), but the paper says "equal" (design.tex:26, eval.tex:150).

15. **Minor, robustness:** analyze_extra.py:63 labels every non-B2 transfer row outside `transfer_8b_t` as OURS-native. *Fix:* use the logged `label` field, as process_results.py does.

16. **Minor: the H1b test choice is a deviation, but the paper doesn't say so.** PLAN.md records the one-sided bootstrap as a deviation; eval.tex:31 states it without saying so. *Fix:* add "(deviation, see PLAN)".

Verified OK: B2 is the best baseline in every family. H1, H1b and H2 numbers match tests.csv and h1b.csv, including the token cuts and the requirement to use fewer tokens than both B0 and B2. History recall is 64% vs 94%, with 0% success without the gold session. OURS selects later sessions at 1k (mean relative position 0.80 vs 0.50 for B2), which supports the recency diagnosis. "Never better than similarity": 0.2678 vs 0.2679 on tool. Facts at 8k: lost 6, gained 2, gold dropped in 2. Solver: 2,400 solves, all optimal. Single worker, renderer order, short variants and shrinkage n/(n+10) match the code. Profiling used dev instances 1–40 (4B) and 1–20 (8B); pilots used dev instances 41–60.
