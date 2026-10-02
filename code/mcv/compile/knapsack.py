"""MCV compiler: dependency- and interaction-aware knapsack over typed blocks, solved with OR-Tools CP-SAT.

    maximize   sum_{b,v} val[b,v] * x[b,v]  +  sum_{T1<T2} I[T1,T2] * y[T1,T2]
    subject to sum_v x[b,v] <= 1                              (at most one variant per block)
               sum_v x[b,v]  = 1          for mandatory b      (goal, instructions)
               sum_v x[b,v] <= sum_v x[d,v]  for each dep d of b
               sum_{b,v} cost[b,v] * x[b,v] <= B               (hard token budget, target-model tokenizer)
               z[T] = OR_b x[b,*] for b of type T;  y[T1,T2] = z[T1] AND z[T2]
Values are scaled to integers. If the mandatory blocks alone exceed the budget, BudgetError is raised (never silent
truncation). On timeout the best feasible solution is returned with its status; if none, a greedy value-density
fallback is used and the certificate records it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from mcv.ir.blocks import Instance

SCALE = 10_000


class BudgetError(ValueError):
    """Mandatory blocks do not fit the budget."""


@dataclass
class Plan:
    selection: dict  # block_id -> variant
    tokens: int
    objective: float
    certificate: dict = field(default_factory=dict)


def _costs(inst: Instance, counter) -> dict:
    return {(b.id, v): counter.block_cost(b, v) for b in inst.blocks for v in b.variants}


def compile_plan(inst: Instance, counter, budget: int, values: dict, interactions: dict | None = None,
                 time_limit: float = 2.0, use_variants: bool = True, use_deps: bool = True) -> Plan:
    """values: {block_id: {variant: value}}; interactions: {(type_a, type_b): weight} on type-presence."""
    interactions = interactions or {}
    cost = _costs(inst, counter)
    mand = set(inst.mandatory_ids())
    m_cost = sum(cost[(b, "full")] for b in mand)
    if m_cost > budget:
        raise BudgetError(f"{inst.iid}: mandatory blocks need {m_cost} tokens > budget {budget}")
    t0 = time.perf_counter()
    model = cp_model.CpModel()
    x = {}
    for b in inst.blocks:
        vs = list(b.variants) if use_variants else ["full"]
        for v in vs:
            x[(b.id, v)] = model.NewBoolVar(f"x_{b.id}_{v}")
        model.Add(sum(x[(b.id, v)] for v in vs) <= 1)
        if b.id in mand:
            model.Add(sum(x[(b.id, v)] for v in vs) == 1)
    sel = {b.id: [x[k] for k in x if k[0] == b.id] for b in inst.blocks}
    if use_deps:
        for b in inst.blocks:
            for d in b.deps:
                model.Add(sum(sel[b.id]) <= sum(sel[d]))
    model.Add(sum(cost[k] * var for k, var in x.items()) <= budget)
    obj = [int(round(values.get(k[0], {}).get(k[1], 0.0) * SCALE)) * var for k, var in x.items()]
    z = {}
    for t in {b.type.value for b in inst.blocks}:
        z[t] = model.NewBoolVar(f"z_{t}")
        members = [var for k, var in x.items() if inst.by_id()[k[0]].type.value == t]
        model.AddMaxEquality(z[t], members)
    for (ta, tb), w in interactions.items():
        if ta in z and tb in z and abs(w) > 0:
            y = model.NewBoolVar(f"y_{ta}_{tb}")
            model.AddMultiplicationEquality(y, [z[ta], z[tb]])
            obj.append(int(round(w * SCALE)) * y)
    model.Maximize(sum(obj))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = 0
    st = solver.Solve(model)
    secs = time.perf_counter() - t0
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selection = {k[0]: k[1] for k, var in x.items() if solver.Value(var)}
        tokens = sum(cost[(b, v)] for b, v in selection.items())
        return Plan(selection, tokens, solver.ObjectiveValue() / SCALE,
                    {"status": solver.StatusName(st), "bound": solver.BestObjectiveBound() / SCALE,
                     "seconds": secs, "fallback": False})
    plan = greedy(inst, counter, budget, values)
    plan.certificate.update({"status": solver.StatusName(st), "seconds": secs, "fallback": True})
    return plan


def greedy(inst: Instance, counter, budget: int, values: dict) -> Plan:
    """Value-density greedy over full variants with dependencies; mandatory blocks first."""
    cost = _costs(inst, counter)
    mand = inst.mandatory_ids()
    selection = {b: "full" for b in mand}
    used = sum(cost[(b, "full")] for b in mand)
    if used > budget:
        raise BudgetError(f"{inst.iid}: mandatory blocks exceed budget")
    cand = [b for b in inst.blocks if b.id not in selection]
    cand.sort(key=lambda b: -values.get(b.id, {}).get("full", 0.0) / max(1, cost[(b.id, "full")]))
    for b in cand:
        if values.get(b.id, {}).get("full", 0.0) <= 0:
            continue
        need = [b] + [inst.by_id()[d] for d in b.deps if d not in selection]
        c = sum(cost[(n.id, "full")] for n in need)
        if used + c <= budget:
            for n in need:
                selection[n.id] = "full"
            used += c
    obj = sum(values.get(b, {}).get(v, 0.0) for b, v in selection.items())
    return Plan(selection, used, obj, {"status": "GREEDY", "fallback": True})
