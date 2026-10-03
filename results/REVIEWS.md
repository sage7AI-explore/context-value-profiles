# Review: Marginal Context Value Profiles (paper 03)

## Summary
The paper defines per-(model, task family) MCV profiles: type-removal values, short-variant values and pairwise interactions, estimated by ablation with bootstrap CIs and a padding control. It feeds them, with a ridge block-value model, into a CP-SAT budget compiler. In a pre-registered local study (Qwen3-4B, HotpotQA, BFCL, synthetic history) the primary hypothesis H1 fails: the method never significantly beats embedding relevance, and it is significantly worse on history. H1b (fewer tokens at 8k with non-inferior success) passes in 2 of 3 families. H2 (interactions) shows no effect, and H3 (4B to 8B transfer) is non-inferior.

## Strengths
1. The paper reports its failure honestly. The H1 failure appears in the abstract, the intro and Table 2, with a diagnosed cause and a cross-validation check showing the learned ranker never beat its own similarity feature.
2. Rigorous process: pre-registration, Holm correction, disclosed deviations, numbers generated from logs, a sensitivity rescoring and released transcripts.
3. The profiles are useful diagnostics: examples have near-zero value, short tool schemas lose most of their value, and the padding control separates content from length.
4. Solver cost is well characterized (100% optimal, 2.3 ms median).

## Weaknesses (ranked)
1. **H1b's comparison is weak by construction.** Mean full context is 2.7k to 4.2k tokens, so the 8k budget never binds, and the 4k budget does not bind on facts or history. "Fewer tokens than B0 and B2 at 8k" therefore means "dropped some blocks from full context". Fill-the-budget baselines cannot win on tokens there, and no relevance baseline with a stopping rule (threshold or top-k) was tested.
2. **The contribution is credited to the type profile, but the evidence points to the block ranker.** The tool-use savings come from dropping low-ranked schemas, which is a block-level decision. In the transfer test, outcomes were identical in 100% of episodes even though only 35% of selections matched, with CI [0, 0]. This fits a compiler that is insensitive to the profile at least as well as it fits a profile that transfers faithfully.
3. **Ceiling effects.** History is at 100% for all policies at 2k and above, so H1b-history, H2 and part of H3 have almost no room to show a difference. The 6.9% history saving is small.
4. **The note interaction is misdescribed.** In half the instances the note is current (build.py:177), so I(history, note) = -0.60 shows that history and note substitute for each other. It does not show that a "stale note is redundant".
5. **H1b was added after the dev pilots.** PLAN.md says so, but the paper presents it as co-primary without this caveat.
6. **Small samples.** Profiles use n=40, rho uses 7 pooled points, the weak baselines use n=30, and power on facts is 58%.

## Text-only requests
- **Eval §Setup / H1b paragraph:** state the mean full-context length next to the budgets. Say that 8k (and 4k for facts and history) is non-binding, so H1b tests pruning from full context, not budgeted selection.
- **Eval §Efficiency and Limits:** note that no relevance baseline with a stopping rule was evaluated, so the token savings are not shown to need MCV.
- **Abstract, Intro (H1b sentence), Conclusion:** add "added after development pilots, before any test run" to H1b.
- **Eval §Transfer, Abstract ("matched"):** report the 100% identical outcomes and the [0, 0] CI as a sign of low sensitivity. Say that H3 non-inferiority does not establish that the profile drives the decisions, since the block model is shared.
- **Limits §What the results mean ("type-level budgeter… cut prompt tokens on tool use"):** attribute the savings to block-level values that stop at value ≤ 0, or soften the claim.
- **Intro, Eval §Interactions and §Profiles, Limits:** replace "the stale note is redundant" with "history and the note substitute for each other (the note is current in half the instances)".
- **Eval §H2 ("substantive finding… rather than a power problem"):** add that history is at ceiling from 2k upward and that the large interaction involves a near-zero-value type, which limits what H2 can detect.
- **Eval §Cost and Fig. 6:** mark the facts break-even as conditional on a success loss (H1b not shown). Alternatively, report break-even only for tool use and history.
- **Abstract:** add "n = 7 pooled (family, type) pairs" after rho = 0.88. Also qualify "near-zero value of examples": the 8B history value is 0.10, and the example–document interaction on facts is +0.10.
- **Related §Positioning:** contrast directly with civalue2025 and ctxalloc2026, which also select by leave-one-out at assembly time. Explain that the novelty is type-level reuse across heterogeneous blocks, and that this specific component did not improve selection.
- **Intro, contributions list:** lead with the empirical findings (negative H1, diagnostic profiles, the limits of LOBO supervision) instead of the "certified compiler", whose certificate covers only the predicted objective.
- **Intro, pre-registration:** say where PLAN.md is archived and whether it is externally time-stamped.

## Remaining overclaims / unclear statements
- "The efficiency hypothesis held" (abstract) needs the non-binding-budget caveat.
- The meaning of "certified" should be defined in one sentence in the Intro.
- "Ten to twenty instances sufficed" is based on subsamples of the same 40 instances, which the eval section admits but the Practical Guidance section does not.

## Questions
1. How many 8k OURS plans drop a block that B2 would keep, by type?
2. What do the AUBC curves look like when restricted to the binding budgets (1k and 2k)?
3. Why does the history ridge put positive weight on token length?

## Future work only (needs new experiments)
- A relevance baseline with a value threshold or top-k stopping rule.
- The hybrid design (relevance within type, profile across types).
- Group or pairwise deletion supervision for the block model.
- Budgets that bind (below full-context length).
- Harder history tasks without ceiling effects.
- Transfer to a different model family, and an ablation that removes the type-MCV feature to test how sensitive the compiler is to the profile.
- Multi-step agent tasks.

## Score
5/10 (weak accept for a workshop; major revision for a journal). Confidence: 4/5.
