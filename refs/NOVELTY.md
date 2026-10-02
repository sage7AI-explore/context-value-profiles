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
