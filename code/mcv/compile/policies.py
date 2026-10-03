"""Context-assembly policies behind one interface: ``policy(inst, counter, budget, ctx) -> Plan``.

Every policy always includes the mandatory blocks (goal, instructions) and respects the hard token budget measured with
the target model's tokenizer.
  B0  full          every block (unbounded reference)
  B1  truncate      concatenate in instance order, keep the longest suffix that fits (drop oldest first)
  B2  relevance     embedding cosine(goal, block), fill the budget in descending order
  B3  llmlingua2    compress all optional blocks with LLMLingua-2 to the remaining budget
  B4  coverage      PACMS-style facility-location coverage (query + candidate pool), cost-aware greedy
  B5  tiers         fixed type priorities (tools > facts > examples > notes > history newest-first)
  OURS-A            MCV compiler, additive values only
  OURS              MCV compiler with type-pair interaction terms
  B2S@tau           relevance with a stopping rule: like B2, but blocks with cosine < tau are never added
  HYB@tau           hybrid (post-hoc addendum): the type profile admits only types whose MCV interval excludes zero;
                    embedding relevance ranks blocks within admitted types (value = cosine - tau, so blocks below tau
                    are never worth sending); the CP-SAT compiler enforces budget, dependencies and variants
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path

import httpx
import numpy as np

from mcv.compile.knapsack import BudgetError, Plan, compile_plan
from mcv.ir.blocks import BlockType, Instance
from mcv.ir.render import render, render_block

EMBED_MODEL = "nomic-embed-text"
TIER = [BlockType.TOOL_SCHEMA, BlockType.SKILL_DOC, BlockType.FACT, BlockType.EXAMPLE, BlockType.NOTE,
        BlockType.HISTORY_TURN]


def _mandatory(inst: Instance, counter, budget: int) -> tuple[dict, int]:
    sel = {b: "full" for b in inst.mandatory_ids()}
    used = sum(counter.block_cost(inst.by_id()[b]) for b in sel)
    if used > budget:
        raise BudgetError(f"{inst.iid}: mandatory blocks need {used} > {budget}")
    return sel, used


def _fill(inst: Instance, counter, budget: int, order: list, stop_at_first_miss: bool = False) -> Plan:
    sel, used = _mandatory(inst, counter, budget)
    for b in order:
        if b.id in sel:
            continue
        c = counter.block_cost(b)
        if used + c <= budget:
            sel[b.id] = "full"
            used += c
        elif stop_at_first_miss:
            break
    return Plan(sel, used, 0.0, {"status": "RULE"})


def full(inst, counter, budget, ctx=None) -> Plan:
    sel = {b.id: "full" for b in inst.blocks}
    return Plan(sel, sum(counter.block_cost(b) for b in inst.blocks), 0.0, {"status": "FULL"})


def truncate(inst, counter, budget, ctx=None) -> Plan:
    opt = [b for b in inst.blocks if b.id not in inst.mandatory_ids()]
    return _fill(inst, counter, budget, list(reversed(opt)), stop_at_first_miss=True)


class Embedder:
    """Ollama embeddings with an SQLite cache."""

    def __init__(self, cache_path: Path, http: httpx.Client | None = None):
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(cache_path), check_same_thread=False)
        self.con.execute("CREATE TABLE IF NOT EXISTS e (k TEXT PRIMARY KEY, v TEXT)")
        self.http = http or httpx.Client()
        self.lock = threading.Lock()

    def embed(self, texts: list) -> np.ndarray:
        out, miss = [None] * len(texts), []
        for i, t in enumerate(texts):
            k = hashlib.sha256(t.encode()).hexdigest()
            with self.lock:
                row = self.con.execute("SELECT v FROM e WHERE k=?", (k,)).fetchone()
            if row:
                out[i] = json.loads(row[0])
            else:
                miss.append(i)
        for j in range(0, len(miss), 32):
            chunk = miss[j:j + 32]
            r = self.http.post("http://localhost:11434/api/embed", json={"model": EMBED_MODEL,
                               "input": [texts[i][:8000] for i in chunk]}, timeout=600)
            r.raise_for_status()
            for i, v in zip(chunk, r.json()["embeddings"]):
                out[i] = v
                with self.lock:
                    self.con.execute("INSERT OR REPLACE INTO e VALUES (?,?)",
                                     (hashlib.sha256(texts[i].encode()).hexdigest(), json.dumps(v)))
            with self.lock:
                self.con.commit()
        a = np.asarray(out, float)
        return a / np.clip(np.linalg.norm(a, axis=1, keepdims=True), 1e-9, None)


def relevance(inst, counter, budget, ctx) -> Plan:
    opt = [b for b in inst.blocks if b.id not in inst.mandatory_ids()]
    E = ctx["embedder"].embed([inst.goal_text()] + [b.text for b in opt])
    sims = E[1:] @ E[0]
    order = [opt[i] for i in np.argsort(-sims, kind="stable")]
    return _fill(inst, counter, budget, order)


def coverage(inst, counter, budget, ctx, query_weight: float = 3.0) -> Plan:
    """PACMS-style: maximize sum_u w_u * max_{s in S} sim(u, s) over u in {query} u candidates, cost-aware greedy,
    compared with the best single affordable block (standard knapsack-submodular safeguard)."""
    sel, used = _mandatory(inst, counter, budget)
    opt = [b for b in inst.blocks if b.id not in sel]
    if not opt:
        return Plan(sel, used, 0.0, {"status": "COVERAGE"})
    E = ctx["embedder"].embed([inst.goal_text()] + [b.text for b in opt])
    U = E  # universe: query + candidates
    w = np.ones(len(U))
    w[0] = query_weight
    S = np.clip(U @ E[1:].T, 0, None)  # |U| x |opt|
    cost = np.array([counter.block_cost(b) for b in opt], float)
    best = np.zeros(len(U))
    chosen = []
    remaining = budget - used
    while True:
        gains = (w[:, None] * np.maximum(S - best[:, None], 0)).sum(0)
        ratio = np.where(cost <= remaining, gains / cost, -1)
        for j in chosen:
            ratio[j] = -1
        j = int(np.argmax(ratio))
        if ratio[j] <= 0:
            break
        chosen.append(j)
        remaining -= cost[j]
        best = np.maximum(best, S[:, j])
    greedy_val = float((w * best).sum())
    single = [(float((w * S[:, j]).sum()), j) for j in range(len(opt)) if cost[j] <= budget - used]
    if single and max(single)[0] > greedy_val:
        chosen = [max(single)[1]]
    for j in chosen:
        sel[opt[j].id] = "full"
        used += int(cost[j])
    return Plan(sel, used, 0.0, {"status": "COVERAGE"})


def tiers(inst, counter, budget, ctx=None) -> Plan:
    order = []
    for t in TIER:
        bs = inst.of_type(t)
        order += list(reversed(bs)) if t == BlockType.HISTORY_TURN else bs
    return _fill(inst, counter, budget, order)


_LINGUA = {}


def llmlingua2(inst, counter, budget, ctx=None) -> Plan:
    """Compress the rendered optional blocks with LLMLingua-2 to fit the remaining budget (target-model tokens)."""
    from llmlingua import PromptCompressor
    if "c" not in _LINGUA:
        _LINGUA["c"] = PromptCompressor(model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
                                        use_llmlingua2=True, device_map="mps")
    sel, used = _mandatory(inst, counter, budget)
    opt = [b for b in inst.blocks if b.id not in sel]
    text = render(opt, all_blocks=inst.blocks)
    room = budget - used
    if counter.count(text) <= room:
        sel.update({b.id: "full" for b in opt})
        return Plan(sel, used + counter.count(text), 0.0, {"status": "LINGUA_NOOP"})
    target = room
    compressed = ""
    for _ in range(6):
        if target <= 0:
            break
        out = _LINGUA["c"].compress_prompt(text, target_token=int(target), force_tokens=["\n", "#", "?", ":"])
        compressed = out["compressed_prompt"]
        n = counter.count(compressed)
        if n <= room:
            break
        target = int(target * room / n * 0.95)
    if counter.count(compressed) > room:
        compressed = ""
    plan = Plan(sel, used + counter.count(compressed), 0.0, {"status": "LINGUA"})
    plan.certificate["prompt_override"] = compressed
    return plan


def mcv_values(inst: Instance, counter, profile: dict, value_model, short_ok: bool = True, embedder=None) -> dict:
    from mcv.profile.features import block_features
    feats = block_features(inst, profile, counter, embedder)
    ids = list(feats)
    pred = value_model.predict([feats[i] for i in ids])
    vals = {}
    for i, v in zip(ids, pred):
        b = inst.by_id()[i]
        vals[i] = {"full": float(v)}
        if short_ok and "short" in b.variants:
            m = profile["mcv"].get(b.type.value, {}).get("value", 0.0)
            sv = profile["short"].get(b.type.value, {}).get("value", 0.0)
            ratio = float(np.clip(sv / m, 0.0, 1.0)) if m > 1e-9 else 0.0
            vals[i]["short"] = float(v) * ratio
    return vals


def interactions(profile: dict, min_abs: float = 0.0) -> dict:
    out = {}
    for k, s in profile.get("interaction", {}).items():
        a, b = k.split("|")
        if abs(s["value"]) > min_abs:
            out[(a, b)] = s["value"]
    return out


def ours(inst, counter, budget, ctx, additive: bool = False) -> Plan:
    prof = ctx["profile"]
    vals = mcv_values(inst, counter, prof, ctx["value_model"], short_ok=ctx.get("variants", True),
                      embedder=ctx.get("embedder"))
    return compile_plan(inst, counter, budget, vals, {} if additive else interactions(prof),
                        use_variants=ctx.get("variants", True), use_deps=ctx.get("deps", True))


def _goal_sims(inst: Instance, ctx, blocks: list) -> np.ndarray:
    E = ctx["embedder"].embed([inst.goal_text()] + [b.text for b in blocks])
    return E[1:] @ E[0]


def relevance_stop(inst, counter, budget, ctx, tau: float) -> Plan:
    opt = [b for b in inst.blocks if b.id not in inst.mandatory_ids()]
    sims = _goal_sims(inst, ctx, opt)
    order = [opt[i] for i in np.argsort(-sims, kind="stable") if sims[i] >= tau]
    return _fill(inst, counter, budget, order)


def admitted_types(profile: dict) -> set:
    """Types whose measured MCV interval excludes zero (lower bootstrap bound > 0)."""
    return {t for t, s in profile.get("mcv", {}).items() if s.get("lo", 0.0) > 0}


def hybrid(inst, counter, budget, ctx, tau: float) -> Plan:
    prof = ctx["profile"]
    ok = admitted_types(prof)
    opt = [b for b in inst.blocks if b.id not in inst.mandatory_ids()]
    sims = _goal_sims(inst, ctx, opt)
    vals = {}
    for b, sim in zip(opt, sims):
        if b.type.value not in ok or sim < tau:
            vals[b.id] = {v: -1.0 for v in b.variants}  # never worth sending
            continue
        v = float(sim - tau) + 1e-3
        vals[b.id] = {"full": v}
        if "short" in b.variants:
            m = prof["mcv"].get(b.type.value, {}).get("value", 0.0)
            sv = prof.get("short", {}).get(b.type.value, {}).get("value", 0.0)
            vals[b.id]["short"] = v * (float(np.clip(sv / m, 0.0, 1.0)) if m > 1e-9 else 0.0)
    return compile_plan(inst, counter, budget, vals, {}, use_variants=ctx.get("variants", True),
                        use_deps=ctx.get("deps", True))


def get_policy(name: str):
    """Resolve a policy name; parameterized policies are written NAME@tau (e.g. B2S@0.62)."""
    if "@" in name:
        base, tau = name.split("@")
        fn = {"B2S": relevance_stop, "HYB": hybrid}[base]
        return lambda i, c, b, x: fn(i, c, b, x, float(tau))
    return POLICIES[name]


def prompt_for(inst: Instance, plan: Plan) -> str:
    """Render a plan; LLMLingua-2 plans insert their compressed text before the goal."""
    override = plan.certificate.get("prompt_override")
    if override is not None:
        mand = [inst.by_id()[b] for b in plan.selection]
        instr = [b for b in mand if b.type == BlockType.INSTRUCTIONS]
        goal = [b for b in mand if b.type == BlockType.GOAL]
        parts = [render_block(b) for b in instr] + ([f"### Context\n{override.strip()}\n"] if override else [])
        return "\n".join(parts + [render_block(b) for b in goal])
    return render([inst.by_id()[b] for b in plan.selection], plan.selection, all_blocks=inst.blocks)


POLICIES = {"B0": full, "B1": truncate, "B2": relevance, "B3": llmlingua2, "B4": coverage, "B5": tiers,
            "OURS-A": lambda i, c, b, x: ours(i, c, b, x, additive=True), "OURS": ours}
