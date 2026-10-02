# Novelty — Paper 03 (MCV profiles)

Sources: arXiv API, 2026-10-02 (`code/scripts/fetch_lit.py`): 20 seed IDs (all resolved; titles confirmed) + 13 queries,
194 candidates (`refs/candidates.json`, raw in `refs/raw/`). **[full text]** = PDF read/searched.

## Closest work and how this paper differs

- **Decision-Aware Memory Cards / CICL (2606.08151) [full text].** Ranks retrieved files, tests, traces, rules and memories
  by expected effect on the agent's next action; defines utility as V(x, C+) − V(x, C−) per candidate unit and instance,
  estimated by hosted LLM judges, local surrogates or rankers; evaluated on 50 SWE-bench Verified file-retrieval instances.
  *Differs:* CICL estimates per-instance utility with a judge/surrogate; MCV *measures* per-(block type, task class, model)
  marginal effects by ablation with pairwise interaction terms, compiles them with a dependency-aware knapsack, and tests
  small→large model transfer.
- **The Laws of Context Allocation (2608.23252) [full text].** Replaces relevance proxies with a teacher-forced causal
  leave-one-out probe of generative reliance on retrieved documents and studies budget allocation in a factorial grid for RAG.
  *Differs:* homogeneous retrieved documents and likelihood-based reliance; MCV values heterogeneous typed blocks by
  task-success change, with interactions and an optimizing compiler.
- **Optimal Skill Selection with Bicriteria Guarantees (2608.19993) [full text].** Budgeted skill selection as regularized
  monotone submodular maximization under a knapsack constraint (complementary coverage, diminishing returns, linear token
  penalty) with provable guarantees. Its own text names "interaction terms learned from execution feedback" as future work.
  *Differs:* MCV measures values and interactions from execution outcomes (the future work they name), over all block
  types, not only skills, and accepts non-submodular interactions by solving the ILP exactly (CP-SAT) instead of greedy.
- **PACMS (2606.20047) [full text].** Assembly-time selection as submodular maximum coverage under a knapsack constraint
  with a cost-aware greedy; pluggable selector (top-k, MMR, recency). *Differs:* coverage/relevance objective vs. measured
  counterfactual value; we re-implement a PACMS-style coverage selector as baseline B4.
- **ContextPipe (2609.00749) [full text].** Database-inspired five-phase context assembly with a data-source catalog and a
  deterministic cache-aware optimizer; notes that maximizing utility under a budget with precedence is a precedence-
  constrained knapsack and deliberately does not search it. *Differs:* we do solve the (dependency-constrained) knapsack,
  with values that are measured rather than assumed; a ContextPipe-style tier policy is baseline B5.
- **ContextRender (2609.37743).** Selects earlier tool results by observed reuse in an execution-dependency graph plus
  recency and relevance. *Differs:* reuse signal within one trajectory vs. counterfactual task-success value across types.
- **Context Assembly as the Controlled Variable (2607.25408).** Control-theoretic framing of context assembly (template,
  demonstrations, retrieval) as the controlled variable. *Differs:* framing vs. a measured value model and compiler.
- **ContextEvo (2609.34649).** Learns a context-management policy from long-horizon trajectories. *Differs:* policy
  learning from failures vs. explicit, inspectable value profiles with transfer.
- **ContextCite (2409.00729), AttriBoT (2411.15102).** Post-hoc attribution of a generation to context sources (surrogate /
  LOO approximation). *Differs:* attribution of one output vs. ex-ante budgeted assembly from profiled values.
- **LLMLingua-2 (2403.12968), COMI (2602.01719).** Token-level compression (learned / marginal information gain by relevance
  minus redundancy). *Differs:* compression by learned or semantic signals vs. block selection by measured task value;
  LLMLingua-2 is baseline B3.
- **ACE (2510.04618), DSPy (2310.03714).** Evolving playbooks and compiled LM pipelines. *Differs:* content optimization vs.
  budgeted selection among existing typed blocks.

## Novelty statement
No retrieved work assembles **heterogeneous typed context blocks** under a token budget using **measured counterfactual
task-success value with pairwise interaction terms**, nor tests whether such type-level value profiles **transfer** from a
small profiling model to larger models. The closest works estimate per-instance utility with judges (CICL), measure
reliance on homogeneous passages (Laws of Context Allocation), or model complementarity with an assumed submodular
coverage function while naming measured interaction terms as future work (Optimal Skill Selection). Kill criterion not met.

## Additions from the independent novelty audit (refs/NOVELTY_AUDIT.md), abstracts read 2026-10-02
- **SkillSV, What Is a Skill Worth? (2608.04562).** Structure-aware Shapley valuation of the *internal units of one fixed
  skill* (rules, examples, scripts, heuristics) under a fixed agent and task distribution, respecting unit dependencies
  and hierarchy; used for pruning. *Differs:* within one document and one agent, per skill; MCV profiles values per block
  *type* across heterogeneous types, assembles (not prunes) under a budget, and tests cross-model transfer. Closest work;
  we do not claim to be first to value context by removal cost.
- **Influence-guided context selection / CI value (2509.21359).** Leave-one-out-style influence of retrieved passages for
  RAG context selection. *Differs:* homogeneous passages, per query.
- **DemoShapley (2410.07523), Prompt valuation with Shapley (2312.15395).** Shapley valuation of demonstrations / prompts.
  *Differs:* one block type, per task.
- **DRSR (2609.27276).** Set-level deletion risk for agent history, accounting for redundancy among deleted units.
  *Differs:* history pruning only; no type-level profiles or transfer.
- **MeClear (2609.09115).** Cooperative-game attribution to clear memories with negative downstream utility.
  *Differs:* memories only, clearance rather than budgeted assembly.
- **SkillsInjector (2605.29794).** Dynamic skill exposure, budget and description construction. *Differs:* skills only.
- **Kernel surrogates for task attribution (2602.03783).** Surrogate models capturing second-order interactions for
  training-task attribution. *Differs:* training tasks, not context; cited for the interaction-surrogate method.
- **Do Context Files Help Coding Agents? (2607.27250).** Ablation finds AGENTS.md/CLAUDE.md-style context files do not
  measurably move correctness. Cited as evidence that block value must be measured, and that it can be ~0.

## Decision (2026-10-02, made autonomously under the user's "complete end to end" instruction; ASK gate not triggered)
Kill criterion not met (audit verdict PROCEED-WITH-CHANGES). Claim repositioned to: **reusable, offline, type-level value
profiles across heterogeneous block types, with cross-type interaction terms, transferable from a small to larger models,
consumed by a dependency-aware exact compiler**. Per-instance valuation (SkillSV, CI value, DemoShapley, DRSR, MeClear) is
related work and, where affordable, a baseline (online per-instance leave-one-out). Profiling adopts a length-neutral
padding control (sensitivity analysis) following SkillSV's concern about length confounds.
