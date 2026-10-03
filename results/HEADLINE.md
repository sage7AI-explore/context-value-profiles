# Headline findings (Paper 03, test split; numbers from results/processed/numbers.json)

1. **H1 (primary) FAILED.** MCV-compiled context did not beat embedding relevance (B2, the best baseline everywhere) in
   AUBC: facts −0.025 (n.s.), tool +0.007 (n.s.), history −0.053 (significant loss, Holm p < 0.001).
2. **Cause of the history loss:** at 1k the block ranker kept the session holding the answer in 64% of plans vs 94% for
   B2. Leave-one-block-out deltas are ~5% non-zero, and the learned ranker was never better than embedding similarity
   alone (CV rank correlation, history: 0.15 vs 0.27).
3. **H1b (efficiency; added after dev pilots, before test) SUPPORTED in 2/3.** At 8k MCV sent 34.9% fewer tokens on tool
   and 6.9% fewer on history with non-inferior success; facts −30.9% tokens, non-inferiority not shown. Caveat: 8k never
   binds (full contexts are 2.7k–4.2k tokens), so this is pruning, and no relevance-with-stopping-rule baseline was run.
4. **H2: interaction terms had no effect** on AUBC (+0.003, n.s.) although they changed 22–50% of the selections.
5. **H3: transfer 4B→8B non-inferior.** Outcomes were identical in 100% of 240 paired episodes, though only 35% of the
   selections were identical. This also signals low sensitivity to the type profile. Type values rank-correlate
   ρ = 0.88 (7 pooled pairs).
6. **Profiles as a diagnostic:** tool schemas (0.85) and documents (0.35) carry the value, while examples carry little.
   A length-neutral control reproduces the removal effects. Profiles stabilize with 10–20 dev instances.
7. **Cost:** 1,440 profiling calls (~3 h on a laptop); median CP-SAT solve 2.3 ms, all optimal.
8. **Integrity:** independent recomputation MATCH (155 quantities); verification PASS; one checker defect found and
   disclosed (22 episodes flipped, no hypothesis difference changed).
