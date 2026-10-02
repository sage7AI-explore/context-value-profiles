# Novelty Audit — Paper 03 (MCV profiles)

Independent check, 2026-10-02. Inputs read: `IDEA.md`, `refs/NOVELTY.md`. Sources: arXiv API (export.arxiv.org),
OpenAlex `/works?search=` (filtered from 2025-06-01), Semantic Scholar graph search (one query succeeded; the second hit HTTP 429).
"Full text" means the arXiv HTML version was retrieved and searched. "In candidates.json" means the ID already appears in
`refs/candidates.json` (the original search retrieved it); "in NOVELTY.md" means it is discussed there.

**Kill criterion (from IDEA.md):** a paper that selects or assembles *heterogeneous* context blocks under a budget, using
*measured counterfactual task-success value with interaction terms*.

## Queries used (34)
arXiv (sorted by submission date, newest first):
1. `abs:"leave-one-out" AND abs:context AND abs:budget AND abs:agent` (0)
2. `abs:ablation AND abs:"context blocks" AND abs:LLM` (0)
3. `abs:"context selection" AND abs:counterfactual AND abs:"task success"` (0)
4. `abs:"context engineering" AND abs:"interaction" AND abs:ablation`
5. `abs:"prompt components" AND abs:ablation AND abs:knapsack` (0)
6. `abs:"Shapley" AND abs:"prompt" AND abs:"context" AND abs:selection`
7. `abs:"context budget" AND abs:"marginal value"` (0)
8. `abs:"interaction effects" AND abs:"prompt" AND abs:components AND abs:LLM`
9. `abs:"tool descriptions" AND abs:"skill" AND abs:context AND abs:budget AND abs:selection` (0)
10. `abs:"context assembly" AND abs:agent`
11. `abs:"data valuation" AND abs:"in-context" AND abs:selection AND abs:interaction`
12. `abs:"context utility" AND abs:agent AND abs:token`
13. `abs:ablation AND abs:context AND abs:agent AND abs:budget AND abs:selection`
14. `abs:"leave-one-out" AND abs:context AND abs:LLM AND abs:selection`
15. `abs:counterfactual AND abs:context AND abs:"token budget"`
16. `abs:"context components" AND abs:ablation AND abs:LLM` (0)
17. `abs:"system prompt" AND abs:components AND abs:ablation AND abs:"interaction"`
18. `abs:"context engineering" AND abs:budget AND abs:value`
19. `abs:"prompt compression" AND abs:"task success" AND abs:agent`
20. `abs:"which context" AND abs:agent`
21. `abs:"context value" AND abs:LLM`
22. `abs:"in-context" AND abs:"interaction" AND abs:Shapley AND abs:budget`
23. `abs:knapsack AND abs:context AND abs:LLM`
24. `abs:"skill" AND abs:"tool schema" AND abs:ablation` (0)
25. `abs:Shapley AND abs:agent AND abs:context AND abs:pruning`
26. `abs:"prompt sections" AND abs:ablation` (0)
27. `abs:valuation AND abs:context AND abs:agent AND abs:budget`
28. `abs:"interaction" AND abs:"leave-one-out" AND abs:context AND abs:agent`
29. `abs:"context ablation" AND abs:LLM`
30. `abs:transfer AND abs:"small model" AND abs:"context selection"`
31. `abs:"AGENTS.md" AND abs:ablation`
32. `abs:"counterfactual" AND abs:"context engineering"`
33. `abs:"prompt valuation"`; `abs:"context" AND abs:"Shapley" AND abs:"agent" AND abs:"token"` (0)

OpenAlex: "counterfactual ablation context blocks budget LLM agent interaction"; "leave-one-out context value token budget
agent prompt assembly"; "Shapley value prompt components interaction LLM context selection"; "marginal value of context LLM
agent knapsack". These returned mostly surveys and tangential work; the only relevant hit was 2608.19993, which NOVELTY.md
already covers.
Semantic Scholar: "ablation-based context selection LLM agent interaction budget" returned nothing relevant.

## Closest hits

| arXiv id | Title (as returned) | What it does (abstract / text) | In NOVELTY.md? | Overlap with kill criterion |
|---|---|---|---|---|
| 2608.04562 | What Is a Skill Worth? Structure-Aware Shapley Valuation of Agent Skills | **[full text]** SkillSV compiles *one skill* into units (rules, examples, scripts, heuristics) with dependencies and hierarchy. It estimates Shapley values from **agent rollouts on a task distribution** (paired deletion plus length-neutral padding to separate content value from context-occupancy cost), recovers unit **interactions**, and uses the values for safe pruning and compression. Baselines include Closure-LOO and an LLM judge; the target agent is GPT-5.5. | **No** (not in candidates.json) | **Partial, and the strongest so far.** It measures counterfactual task-success value with interactions and dependency closure, and uses it to cut context. It does not cover heterogeneous block types (only units inside a skill), does not solve a budgeted knapsack or ILP assembly, has no per-(type × task-class × model) profiles, and has no small→large transfer. |
| 2609.27276 | DRSR: Learning Set-Level Deletion Risk for Efficient Long-Horizon Agents | Offline, it builds exact counterfactual supervision by **jointly deleting** history blocks and measuring the change in teacher-forced likelihood of the recorded next output. A scorer predicts set-level harm using **pairwise set structure**, and the method deletes the largest safe set under budget and protocol constraints. Reward goes from 0.699 to 0.802 and tokens drop ~21%. | **No** (not in candidates.json) | **Partial.** It has set-level counterfactuals with pair interactions under a budget. But the signal is likelihood, not task success; it covers only history blocks; it prunes by deletion rather than assembling typed blocks; and it does not transfer across models. |
| 2609.09115 | MeClear: Cooperative Game-Theoretic Attribution and Risk-Aware Memory Clearance for Long-Horizon LLM Agents | Combines LOO screening with sampled Shapley attribution across **interacting** memories ("redundant conflict masking where single removal fails"). It removes negative-utility memories and checks that the task recovers. | No (in candidates.json, not discussed) | **Partial.** It uses counterfactual task utility with interactions, but only for memory items and per query. It removes harmful items rather than assembling under a budget, and has no type profiles or transfer. |
| 2509.21359 | Influence Guided Context Selection for Effective Retrieval-Augmented Generation | The CI value is the performance drop when each context is removed (LOO). A surrogate with "global inter-context interactions" predicts it, and contexts with CI > 0 are kept. | No (in candidates.json, not discussed) | **Partial.** It has LOO task-performance value and modelled interactions, but covers only homogeneous RAG passages, uses a threshold instead of a budgeted optimizer, and has no transfer study. |
| 2605.29794 | SkillsInjector: Dynamic Skill Context Construction for LLM Agents | A context planner learns "execution-grounded skill preferences", sets an adaptive skill budget, and uses a set-aware renderer conditioned on co-injected skills. | No (in candidates.json) | Partial or low. It uses execution feedback and co-injection effects, but only for skills, through a learned policy rather than measured ablation values. |
| 2410.07523 | DemoShapley: Valuation of Demonstrations for In-Context Learning | Shapley value of ICL demonstrations computed over prompt permutations, then used for selection. | No (in candidates.json) | Low. It uses measured marginal value, but only for homogeneous demonstrations. |
| 2312.15395 | Prompt Valuation Based on Shapley Values | Shapley valuation of prompts. | No (in candidates.json) | Low. It values prompts, not budgeted assembly of blocks. |
| 2609.08279 | What Eviction Destroys: A Restore-Counterfactual Audit of Forgetting in Agent Memory | A paired restore counterfactual that audits eviction policies under token budgets. | No | None or low. It is an audit, not a selection method. |
| 2607.27250 | Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories | A controlled ablation of AGENTS.md-style context injection (288 runs). It finds no measurable effect on correctness. | No | None. But it is useful motivation and caution: whole-block ablation effects can be null. |
| 2602.03783 | Efficient Estimation of Kernel Surrogate Models for Task Attribution | Kernel surrogates that capture second-order (XOR-type) interactions for attribution, including ICL; it reports +25% correlation with LOO ground truth compared with linear surrogates. | No | None for the kill criterion. It is relevant as a method for the interaction-regression estimator. |
| 2608.19993 | Optimal Skill Selection for LLM Agents with Provable Bicriteria Guarantees | (Found again via OpenAlex.) | Yes | Partial, as NOVELTY.md already states. |

## Verdict: **PROCEED-WITH-CHANGES**

No retrieved paper meets the full kill criterion. None assembles *heterogeneous typed* blocks (goal, instructions, tool
schemas, skill docs, facts, examples, history, notes) under a token budget by solving an optimization over *measured
task-success* values *with interaction terms*. None profiles values per (block type × task class × model) or tests
small→large transfer.

However, the space between the pieces has shrunk since NOVELTY.md was written:
- **SkillSV (2608.04562)** already does "value context by what removing it costs" with interactions, dependency closure,
  rollout-measured task success, and pruning under context cost. It does this within a single skill document. That takes
  the headline sentence's core idea and the "dependency-aware counterfactual" mechanism. The paper must cite it prominently
  and must not claim to be first to measure interaction-aware counterfactual value of context units for agents.
- **DRSR (2609.27276)** and **MeClear (2609.09115)**, both from September 2026, do set-level and pairwise-interaction
  counterfactual pruning for history and memory. **CI value (2509.21359)** does LOO-based selection with modelled
  inter-context interactions for RAG.

Required changes:
1. **Reposition the novelty claim** onto three things together: (a) *type-level, reusable, offline* profiles (amortized across
   instances, unlike the per-instance or per-skill valuation in SkillSV, MeClear, CI value and DRSR); (b) *cross-type*
   interactions such as schema × skill-doc, which none of these papers can express because each values one homogeneous unit
   kind; (c) *small→large transfer*. The exact ILP or knapsack compiler is secondary.
2. **Add baselines or comparisons:** a SkillSV-style Shapley-pruning baseline applied per block type (or run Closure-LOO,
   which SkillSV itself uses as a baseline) and a CI-value-style "keep if LOO > 0" selector. Report how much the profile
   transfer and the cross-type interactions add over these.
3. **Borrow SkillSV's length-neutral padding control**, or justify not using it, so content value is separated from
   context-occupancy cost. A reviewer will ask for it.
4. Plan for a possible null result. 2607.27250 found that whole-file context ablations had no measurable effect for frontier
   coding agents. Choose task families where block types demonstrably matter.

## Related work NOVELTY.md should add
- 2608.04562 SkillSV (**must-cite, closest**). Was not in candidates.json.
- 2609.27276 DRSR (set-level counterfactual deletion with pair interactions, Sept 2026). Was not in candidates.json.
- 2609.09115 MeClear (LOO plus Shapley over interacting memories, Sept 2026).
- 2509.21359 Influence Guided Context Selection / CI value (LOO task-value context selection with interaction surrogate).
- 2410.07523 DemoShapley; 2312.15395 Prompt Valuation Based on Shapley Values (valuation lineage).
- 2605.29794 SkillsInjector (execution-grounded, set-aware skill injection under adaptive budget).
- 2602.03783 Kernel surrogate models for task attribution (estimator for second-order interactions).
- 2607.27250 Do Context Files Help Coding Agents? (null-effect ablation; motivation and risk).
