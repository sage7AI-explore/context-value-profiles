# Revision change log (2026-10-03, option C)

## Major substantive edits (supported by existing or newly run data)
1. **Reframing around three levels** (type value, block relevance, budget allocation): new subsection in the Problem
   section, an intro research question, a contribution, and the discussion. The claim is that measured type value was
   informative while block selection was best served by relevance.
2. **Measured vs predicted value** separated in notation and prose. The solver certificate is stated to cover the
   predicted objective only, never task success (Problem, Design, Intro, Abstract).
3. **Novelty narrowed** to reusable type-level value estimation across heterogeneous context classes, conditioned on model
   and task family, with uncertainty and constrained compilation. Prior leave-one-out and influence selection is
   acknowledged explicitly.
4. **New pre-specified post-hoc follow-up (Addendum A in PLAN.md, committed before its runs):**
   - B2S, relevance with a stopping rule calibrated on development data, and HYB, the hybrid.
   - Results: the hybrid beat relevance in 0/3 families. Relevance with a stopping rule matched or exceeded MCV's token
     savings (83.4% vs 34.9% on tool use, non-inferior), so the savings are not specific to MCV.
   - The hybrid and B2S produced the same outcome in about 99% of episodes.
   - The calibrated thresholds were too aggressive on facts and history (success −6 points).
5. **Efficiency recast as pruning** at a non-binding 8k budget, in the abstract, intro, results heading, limitations and
   conclusion.
6. **Transfer interpreted conservatively:** identical outcomes despite differing selections are consistent with transfer
   or with compiler insensitivity. No generalization beyond Qwen3 is claimed.
7. **Discussion rebuilt:**
   - "What the results mean" covers diagnosis vs selection.
   - A new "Design lesson and future work" section presents the hybrid pipeline as tested and not supported here, with
     open conditions.
   - The practical guidance now recommends relevance plus a calibrated stopping rule.
8. **Limitations** extended: follow-up is post-hoc on the same test set, calibration noise, and transfer cannot be told
   apart from insensitivity.
9. **Conclusion** now ends on the scientific lesson, not the compiler.
10. **Abstract rewritten** (1,891 characters): leads with the three questions; failure, diagnosis, pruning, follow-up,
    diagnostics and transfer caveat.
11. **Space:** the break-even figure was removed (its numbers remain in the text) to stay at 12 pages.

## Integrity of the new runs
- Calibration used only development instances 41–60 (never used for profiling).
- Verification PASS: all addendum test runs descend from the addendum commit, with the expected row counts.
- Independent recomputation MATCH (161 quantities).

## Experiments still worth running (NOT run; no results are claimed)
1. **Stopping thresholds calibrated on a larger development set** (for example all 60 dev instances, or
   cross-validated).
   - Hypothesis: relevance with a better-calibrated stopping rule is non-inferior to full context in all three families
     with large token savings.
   - Baselines: B0, OURS, B2S as run.
   - Metric: success at 8k (non-inferiority, margin 0.05), prompt tokens.
   - If it passes everywhere: stopping, not MCV, is the efficiency mechanism. If it fails on facts and history:
     conservative block values have a real role there.
2. **A non-Qwen model family** (for example a Llama or Gemma model via Ollama), with the same protocol.
   - Hypothesis: type profiles rank-correlate with Qwen3's, and relevance still matches or beats MCV at block selection.
   - Metric: profile ρ, AUBC vs B2.
   - Agreement would support generality of the diagnostic. Disagreement would mean profiles are model-specific and
     must always be re-measured.
3. **Hybrid under binding budgets and longer trajectories.**
   - Hypothesis: type-level admission helps when excluded types are large, numerous or harmful.
   - Design: tasks whose full context exceeds the budget, multi-step episodes.
   - Metric: AUBC, success at binding budgets.
   - A gain would validate the type level for allocation. A null result would confine MCV to diagnosis.
