"""H1b, H3, profiles, padding control, token composition, profiling cost; writes CSVs and results/processed/numbers.json.
Run after process_results.py (reads its CSVs)."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from mcv.data.build import load  # noqa: E402
from mcv.ir.blocks import TokenCounter  # noqa: E402

RAW, PROC = ROOT / "results/raw", ROOT / "results/processed"
N_BOOT, MARGIN = 10_000, 0.05
FAM = {"facts": "Facts", "history": "History", "tool": "Tool", "pooled": "Pooled"}
PN = {"B0": "Full", "B1": "Trunc", "B2": "Rel", "B3": "Lingua", "B4": "Cov", "B5": "Tier", "OURS-A": "Additive", "OURS": "Ours"}
HN = {"H1": "HOne", "H1b": "HOneb", "H2": "HTwo"}
NUM: dict = {}


def put(name: str, value, fmt: str, source: str) -> None:
    NUM[name] = {"value": value, "fmt": fmt, "source": source}


def boot(d, seed=0):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), (N_BOOT, len(d)))].mean(1)
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def jl(run: str) -> pd.DataFrame:
    p = RAW / run / "episodes.jsonl"
    return pd.DataFrame([json.loads(l) for l in p.read_text().splitlines() if l.strip()]) if p.exists() else pd.DataFrame()


def h1b(main: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ok = main[main["status"] == "ok"]
    for fam, d in ok.groupby("family"):
        o = d[(d.policy == "OURS") & (d.budget == 8000)].set_index("iid")
        b0 = d[d.policy == "B0"].set_index("iid")
        b2 = d[(d.policy == "B2") & (d.budget == 8000)].set_index("iid")
        idx = o.index.intersection(b0.index)
        e, lo, hi = boot(o.loc[idx].success.astype(float).values - b0.loc[idx].success.astype(float).values)
        t_o, t_b0, t_b2 = o.prompt_tokens_measured.mean(), b0.prompt_tokens_measured.mean(), b2.prompt_tokens_measured.mean()
        rows.append({"family": fam, "n": len(idx), "tokens_ours": t_o, "tokens_b0": t_b0, "tokens_b2": t_b2,
                     "reduction_vs_b0": 1 - t_o / t_b0, "success_ours": o.success.mean(), "success_b0": b0.success.mean(),
                     "diff": e, "lo": lo, "hi": hi, "noninferior": lo > -MARGIN, "fewer_tokens": t_o < min(t_b0, t_b2)})
    return pd.DataFrame(rows)


def transfer() -> pd.DataFrame:
    parts = [jl(r) for r in ("transfer_8b", "transfer_8b_t", "transfer_8b_native")]
    df = pd.concat([p for p in parts if len(p)], ignore_index=True)
    df = df[df["status"] == "ok"].copy()
    df["cond"] = np.where(df.policy == "B2", "B2", df["label"])
    assert set(df["cond"]) <= {"B2", "OURS-T", "OURS-native"}, set(df["cond"])
    return df


def fidelity() -> dict:
    v4, v8, keys = [], [], []
    for fam in ("facts", "history", "tool"):
        p4 = json.loads((PROC / "profiles" / f"qwen3-4b-instruct_{fam}.json").read_text())
        p8 = json.loads((PROC / "profiles" / f"qwen3-8b_{fam}.json").read_text())
        for t in sorted(set(p4["mcv"]) & set(p8["mcv"])):
            keys.append(f"{fam}:{t}")
            v4.append(p4["mcv"][t]["raw"])
            v8.append(p8["mcv"][t]["raw"])
    rho, p = spearmanr(v4, v8)
    pd.DataFrame({"key": keys, "mcv_4b": v4, "mcv_8b": v8}).to_csv(PROC / "fidelity.csv", index=False)
    return {"rho": float(rho), "p": float(p), "n": len(keys)}


def profiles() -> pd.DataFrame:
    rows = []
    for f in sorted((PROC / "profiles").glob("*.json")):
        p = json.loads(f.read_text())
        for part in ("mcv", "short", "interaction"):
            for k, s in p.get(part, {}).items():
                rows.append({"model": p["model"], "family": p["family"], "part": part, "key": k, "raw": s["raw"],
                             "value": s["value"], "lo": s["lo"], "hi": s["hi"], "n": s["n"], "base": p["base"]})
    return pd.DataFrame(rows)


def padding() -> pd.DataFrame:
    df = jl("profile_qwen3-4b-instruct")
    rows = []
    for fam, d in df.groupby("family"):
        piv = d.pivot_table(index="iid", columns="condition", values="success", aggfunc="first").astype(float)
        for c in [c for c in piv.columns if c.startswith("pad:-")]:
            t = c[5:]
            sub = piv.dropna(subset=["full", c, f"-{t}"])
            rows.append({"family": fam, "type": t, "n": len(sub), "removal_effect": float((sub["full"] - sub[f"-{t}"]).mean()),
                         "padded_effect": float((sub["full"] - sub[c]).mean())})
    return pd.DataFrame(rows)


def composition(main: pd.DataFrame) -> pd.DataFrame:
    counter = TokenCounter("qwen3:4b-instruct")
    blocks = {x.iid: x for x in load("test")}
    acc = defaultdict(lambda: defaultdict(float))
    n = defaultdict(int)
    for _, r in main[(main.status == "ok") & (main.policy != "B3")].iterrows():
        inst = blocks[r.iid]
        key = (r.family, r.policy, r.budget)
        n[key] += 1
        for bid, var in r.selection.items():
            b = inst.by_id()[bid]
            acc[key][b.type.value] += counter.block_cost(b, var)
    rows = [{"family": k[0], "policy": k[1], "budget": k[2], "type": t, "tokens": v / n[k]} for k, d in acc.items() for t, v in d.items()]
    return pd.DataFrame(rows)


def cost(h: pd.DataFrame) -> pd.DataFrame:
    df = jl("profile_qwen3-4b-instruct")
    df = df[~df.condition.str.startswith("pad:")].drop_duplicates(["family", "iid", "condition"])
    rows = []
    for fam, d in df.groupby("family"):
        calls = len(d)
        fresh = d[~d.cached]
        ptoks = float(d.prompt_tokens.sum())
        saved = float(h.set_index("family").loc[fam, "tokens_b0"] - h.set_index("family").loc[fam, "tokens_ours"])
        rows.append({"family": fam, "profiling_calls": calls, "profiling_model_seconds": float(fresh.seconds.sum()),
                     "profiling_prompt_tokens": ptoks, "tokens_saved_per_query": saved,
                     "break_even_queries": ptoks / saved if saved > 0 else float("inf")})
    return pd.DataFrame(rows)


def recall_history(main: pd.DataFrame, budget: int = 1000) -> pd.DataFrame:
    """History family at the smallest budget: fraction of plans that keep every gold (latest-update) session, and
    success conditional on that."""
    gold = {x.iid: [b.id for b in x.blocks if b.meta.get("gold")] for x in load("test") if x.family == "history"}
    d = main[(main.family == "history") & (main.budget == budget) & (main.status == "ok")]
    rows = []
    for p, g in d.groupby("policy"):
        has = np.array([all(t in sel for t in gold[i]) for i, sel in zip(g.iid, g.selection)])
        suc = g.success.astype(float).values
        rows.append({"policy": p, "n": len(g), "recall": has.mean(), "succ_gold": suc[has].mean() if has.any() else np.nan,
                     "succ_no_gold": suc[~has].mean() if (~has).any() else np.nan})
    return pd.DataFrame(rows)


def facts_losses(main: pd.DataFrame) -> dict:
    gold = {x.iid: [b.id for b in x.blocks if b.meta.get("gold")] for x in load("test") if x.family == "facts"}
    d = main[(main.family == "facts") & (main.status == "ok")]
    o = d[(d.policy == "OURS") & (d.budget == 8000)].set_index("iid")
    b = d[d.policy == "B0"].set_index("iid")
    idx = o.index.intersection(b.index)
    lost = [i for i in idx if b.loc[i, "success"] and not o.loc[i, "success"]]
    gained = [i for i in idx if o.loc[i, "success"] and not b.loc[i, "success"]]
    return {"lost": len(lost), "gained": len(gained),
            "gold_dropped": sum(any(g not in o.loc[i, "selection"] for g in gold[i]) for i in lost)}


def selection_diagnostics(main: pd.DataFrame) -> dict:
    """How often interaction terms change the selection; note and example inclusion at 8k."""
    types = {x.iid: {b.id: b.type.value for b in x.blocks} for x in load("test")}
    d = main[main.policy.isin(["OURS", "OURS-A"]) & (main.status == "ok")]
    out = {}
    key = lambda r: json.dumps(r, sort_keys=True)  # noqa: E731
    for fam, g in d.groupby("family"):
        F = FAM[fam]
        a = g[g.policy == "OURS"].set_index(["iid", "budget"]).selection.map(key)
        b = g[g.policy == "OURS-A"].set_index(["iid", "budget"]).selection.map(key)
        idx = a.index.intersection(b.index)
        out[f"RSelDiff{F}"] = float((a.loc[idx] != b.loc[idx]).mean())
        for pol, nm in (("OURS", "Ours"), ("OURS-A", "Additive")):
            e = g[(g.policy == pol) & (g.budget == 8000)]
            has = lambda t: float(np.mean([any(types[i][k] == t for k in sel) for i, sel in zip(e.iid, e.selection)]))  # noqa: E731
            out[f"RHasExample{nm}{F}"] = has("example")
            if fam == "history":
                out[f"RHasNote{nm}{F}"] = has("note")
    return out


def dev_aubc(df: pd.DataFrame) -> float:
    from mcv.eval.metrics import aubc
    d = df[(df.status == "ok") & (df.policy == "OURS")]
    vals = []
    for _, g in d.groupby(["family", "iid"]):
        s = dict(zip(g.budget, g.success.astype(float)))
        if all(b in s for b in (1000, 2000, 4000, 8000)):
            vals.append(aubc([1000, 2000, 4000, 8000], [s[b] for b in (1000, 2000, 4000, 8000)]))
    return float(np.mean(vals))


def main() -> None:
    main_df = pd.concat([jl("main_4b"), jl("main_4b_weak")], ignore_index=True)
    h = h1b(main_df)
    h.to_csv(PROC / "h1b.csv", index=False)
    tr = transfer()
    T = []
    for (fam, b), d in tr.groupby(["family", "budget"]):
        for c, g in d.groupby("cond"):
            e, lo, hi = boot(g.success.astype(float).values)
            T.append({"family": fam, "budget": b, "cond": c, "n": len(g), "success": e, "lo": lo, "hi": hi,
                      "tokens": g.prompt_tokens_measured.mean()})
    pd.DataFrame(T).to_csv(PROC / "transfer.csv", index=False)
    a = tr[tr.cond == "OURS-T"].set_index(["family", "budget", "iid"]).success.astype(float)
    b = tr[tr.cond == "OURS-native"].set_index(["family", "budget", "iid"]).success.astype(float)
    idx = a.index.intersection(b.index)
    d3, lo3, hi3 = boot((a.loc[idx] - b.loc[idx]).values) if len(idx) else (np.nan,) * 3
    fid = fidelity()
    prof = profiles()
    prof.to_csv(PROC / "profiles.csv", index=False)
    pad = padding()
    pad.to_csv(PROC / "padding.csv", index=False)
    comp = composition(jl("main_4b"))
    comp.to_csv(PROC / "composition.csv", index=False)
    c = cost(h)
    c.to_csv(PROC / "cost.csv", index=False)

    # ---------------- numbers.json
    agg = pd.read_csv(PROC / "aubc.csv")
    tests = pd.read_csv(PROC / "tests.csv")
    for _, r in agg[agg.model == "qwen3:4b-instruct"].iterrows():
        nm = PN[r.policy]
        base = f"RAubc{FAM[r.family]}{nm}"
        put(base, r.aubc, "f3", "aubc.csv")
        put(base + "Lo", r.lo, "f3", "aubc.csv")
        put(base + "Hi", r.hi, "f3", "aubc.csv")
        put(f"RN{FAM[r.family]}{nm}", r.n, "int", "aubc.csv")
    for _, r in tests.iterrows():
        k = f"R{HN[r.hyp]}{FAM[r.family]}"
        put(k + "Diff", r["diff"], "f3", "tests.csv")
        put(k + "Lo", r.lo, "f3", "tests.csv")
        put(k + "Hi", r.hi, "f3", "tests.csv")
        put(k + "P", r.p_holm, "p3", "tests.csv")
    put("RHOneHistoryAbs", -float(tests[(tests.hyp == "H1") & (tests.family == "history")]["diff"].iloc[0]), "f3", "tests.csv")
    for _, r in h.iterrows():
        F = FAM[r.family]
        put(f"RTokOurs{F}", r.tokens_ours, "int", "h1b.csv")
        put(f"RTokFull{F}", r.tokens_b0, "int", "h1b.csv")
        put(f"RTokCut{F}", r.reduction_vs_b0, "pct1", "h1b.csv")
        put(f"RSucOursEight{F}", r.success_ours, "pct0", "h1b.csv")
        put(f"RSucFull{F}", r.success_b0, "pct0", "h1b.csv")
    put("RHOnebPass", int(h.noninferior.sum()), "int", "h1b.csv")
    put("RTransferDiff", d3, "f3", "transfer runs (pooled OURS-T minus OURS-native)")
    put("RTransferLo", lo3, "f3", "transfer runs")
    put("RTransferHi", hi3, "f3", "transfer runs")
    put("RTransferN", len(idx), "int", "transfer runs")
    put("RHThreeVerdict", "non-inferior" if lo3 > -MARGIN else "not shown", "raw", "transfer runs: lower CI bound vs margin")
    sel = {c: tr[tr.cond == c].set_index(["family", "budget", "iid"]).selection.map(lambda d: json.dumps(d, sort_keys=True))
           for c in ("OURS-T", "OURS-native")}
    same = sel["OURS-T"].loc[idx] == sel["OURS-native"].loc[idx]
    put("RTransferSameSel", float(same.mean()), "pct0", "transfer runs: identical selections OURS-T vs OURS-native")
    put("RRho", fid["rho"], "f2", "fidelity.csv")
    put("RRhoN", fid["n"], "int", "fidelity.csv")
    for _, r in c.iterrows():
        F = FAM[r.family]
        put(f"RProfCalls{F}", r.profiling_calls, "int", "cost.csv")
        put(f"RBreakEven{F}", r.break_even_queries, "int", "cost.csv")
    put("RProfCallsTotal", float(c.profiling_calls.sum()), "int", "cost.csv")
    put("RProfHours", float(c.profiling_model_seconds.sum()) / 3600, "f1", "cost.csv")
    for _, r in prof[(prof.model == "qwen3:4b-instruct") & (prof.part == "mcv")].iterrows():
        put(f"RMcv{FAM[r.family]}{r.key.title().replace('_', '')}", r.raw, "f2", "profiles.csv")
    for _, r in prof[(prof.model == "qwen3:4b-instruct") & (prof.part == "interaction")].iterrows():
        a_, b_ = r.key.split("|")
        put(f"RInt{FAM[r.family]}{a_.title().replace('_', '')}{b_.title().replace('_', '')}", r.raw, "f2", "profiles.csv")
    # per-budget success, over-budget prompts, solver statistics, history gold-turn recall, dev pilots, padding, 8B, transfer
    BW = {1000: "One", 2000: "Two", 4000: "Four", 8000: "Eight"}
    S = pd.read_csv(PROC / "success.csv")
    for _, r in S[(S.model == "qwen3:4b-instruct") & S.budget.isin(list(BW))].iterrows():
        put(f"RSuc{FAM[r.family]}{PN[r.policy]}{BW[r.budget]}", r.success, "pct0", "success.csv")
    sub = S[(S.policy != "B0")]
    put("ROverBudget", int(sub.over_budget.sum()), "int", "success.csv (budgeted episodes with measured prompt > budget)")
    put("RBudgetedEpisodes", int(sub.n.sum()), "int", "success.csv")
    ev = main_df[main_df.policy != "B0"]
    put("RBudgetedMain", len(ev), "int", "main runs, budgeted episodes")
    put("ROverBudgetMain", int((ev.prompt_tokens_measured > ev.budget).sum()), "int", "main runs")
    put("RMaxOvershoot", int((ev.prompt_tokens_measured - ev.budget).max()), "int", "max measured prompt minus budget")
    put("RMainEpisodes", len(main_df), "int", "main_4b + main_4b_weak")
    put("RStatusNotOk", int((main_df.status != "ok").sum()), "int", "main runs")
    oc = main_df[main_df.policy.isin(["OURS", "OURS-A"])]
    cert = pd.DataFrame(list(oc.certificate))
    put("RSolveMedianMs", float(cert.seconds.median()) * 1000, "f1", "certificates")
    put("RSolveNinetyNineMs", float(cert.seconds.quantile(0.99)) * 1000, "f1", "certificates")
    put("RSolveMaxMs", float(cert.seconds.max()) * 1000, "int", "certificates")
    put("RSolveOptimal", float((cert.status == "OPTIMAL").mean()), "pct1", "certificates")
    put("RSolveFallback", int(cert.fallback.sum()), "int", "certificates")
    put("RPlanMedianMs", float(oc.plan_seconds.median()) * 1000, "f1", "plan_seconds")
    put("RSolves", len(cert), "int", "certificates")
    fl = facts_losses(main_df)
    put("RFactsLost", fl["lost"], "int", "facts 8k: B0 correct, OURS wrong")
    put("RFactsGained", fl["gained"], "int", "facts 8k: OURS correct, B0 wrong")
    put("RFactsLostGoldDropped", fl["gold_dropped"], "int", "facts 8k losses with a supporting paragraph removed")
    sd = selection_diagnostics(main_df)
    for k, v in sd.items():
        put(k, v, "pct0", "selection diagnostics (main_4b)")
    rec = recall_history(main_df)
    rec.to_csv(PROC / "history_recall.csv", index=False)
    for _, r in rec.iterrows():
        put(f"RRecall{PN[r.policy]}", r.recall, "pct0", "history_recall.csv")
    put("RSucGivenNoGoldOurs", float(rec.set_index("policy").loc["OURS", "succ_no_gold"]), "pct0", "history_recall.csv")
    vm = json.loads((PROC / "profiles" / "qwen3-4b-instruct_history.json").read_text())["value_model"]["coef"]
    put("RCoefRecency", vm[-2], "f2", "history value model")
    put("RCoefSim", vm[-1], "f2", "history value model")
    put("RCoefLen", vm[-3], "f2", "history value model")
    for run, nm in [("pilot_dev_4b", "One"), ("pilot2_dev_4b", "Two"), ("pilot3_dev_4b", "Three")]:
        put(f"RDevAubc{nm}", dev_aubc(jl(run)), "f3", f"{run} (OURS, mean over families)")
    for _, r in pad.iterrows():
        F, T_ = FAM[r.family], r.type.title().replace("_", "")
        put(f"RRem{F}{T_}", r.removal_effect, "f2", "padding.csv")
        put(f"RPad{F}{T_}", r.padded_effect, "f2", "padding.csv")
    put("RPadN", int(pad.n.min()), "int", "padding.csv")
    put("RPadDiffMax", float((pad.removal_effect - pad.padded_effect).abs().max()), "f2", "padding.csv")
    for _, r in prof[(prof.model == "qwen3:8b") & (prof.part == "mcv")].iterrows():
        put(f"RMcvEight{FAM[r.family]}{r.key.title().replace('_', '')}", r.raw, "f2", "profiles.csv")
    for _, r in prof[(prof.model == "qwen3:4b-instruct") & (prof.part == "short")].iterrows():
        put(f"RShort{FAM[r.family]}{r.key.title().replace('_', '')}", r.raw, "f2", "profiles.csv")
    for _, r in prof[prof.part == "mcv"].drop_duplicates(["model", "family"]).iterrows():
        put(f"RBase{'Eight' if r.model == 'qwen3:8b' else 'Four'}{FAM[r.family]}", r.base, "pct0", "profiles.csv")
    CN = {"B2": "Rel", "OURS-T": "Transfer", "OURS-native": "Native"}
    for r in T:
        put(f"RTr{FAM[r['family']]}{CN[r['cond']]}{BW[r['budget']]}", r["success"], "pct0", "transfer.csv")
    put("RTrN", int(min(r["n"] for r in T)), "int", "transfer.csv")

    # design constants (read from code / data where they live, so the paper cannot drift from the implementation)
    from mcv.agent import loop
    from mcv.data import build
    from mcv.profile import estimate as est
    allx = load("dev") + load("test")
    put("RNPerFamily", build.N_PER_FAMILY, "int", "mcv/data/build.py")
    put("RNDev", sum(x.split == "dev" for x in allx) // 3, "int", "instances.jsonl")
    put("RNTest", sum(x.split == "test" for x in allx) // 3, "int", "instances.jsonl")
    put("RNMain", 100, "int", "experiments/run_all.sh --limit (main grid)")
    put("RNWeak", 30, "int", "experiments/run_all.sh --limit (weak baselines)")
    put("RNTransfer", 40, "int", "experiments/run_all.sh --limit (transfer)")
    put("RNProfFour", int(prof[(prof.model == "qwen3:4b-instruct") & (prof.part == "mcv")].n.max()), "int", "profiles.csv")
    put("RNProfEight", int(prof[(prof.model == "qwen3:8b") & (prof.part == "mcv")].n.max()), "int", "profiles.csv")
    put("RNLobo", 6, "int", "mcv/run.py --lobo default")
    put("RNZero", est.N0, "int", "mcv/profile/estimate.py")
    put("RNumCtx", loop.NUM_CTX, "int", "mcv/agent/loop.py")
    put("RNumPredict", 96, "int", "mcv/agent/loop.py num_predict")
    put("RNBoot", N_BOOT, "int", "analysis")
    put("RMargin", MARGIN, "f2", "PLAN.md")
    put("RSesoi", 0.05, "f2", "PLAN.md power analysis (smallest effect of interest)")
    put("RPowerFacts", 0.58, "pct0", "PLAN.md power analysis (facts, n = 100)")
    put("RTimeLimit", 2.0, "f1", "mcv/compile/knapsack.py")
    put("RScale", 10_000, "int", "mcv/compile/knapsack.py")
    fx = [x for x in allx if x.family == "tool"][0]
    put("RNumTools", sum(b.type.value == "tool_schema" for b in fx.blocks), "int", "instances.jsonl")
    hx = [x for x in allx if x.family == "history"][0]
    put("RNumSessions", sum(b.type.value == "history_turn" for b in hx.blocks), "int", "instances.jsonl")
    qx = [x for x in allx if x.family == "facts"][0]
    put("RNumDocs", sum(b.type.value == "fact" for b in qx.blocks), "int", "instances.jsonl")
    for fam in ("facts", "history", "tool"):
        c4 = TokenCounter("qwen3:4b-instruct")
        put(f"RFullTok{FAM[fam]}", float(np.mean([sum(c4.block_cost(b) for b in x.blocks) for x in allx if x.family == fam])),
            "int", "instances.jsonl (mean full-context tokens)")

    # code statistics: LOC of the package, test count (junit), line coverage of core modules (all but CLI and data build)
    loc = sum(len([l for l in f.read_text().splitlines() if l.strip()]) for f in (ROOT / "code/mcv").rglob("*.py"))
    put("RLoc", loc, "int", "code/mcv non-blank lines")
    import xml.etree.ElementTree as ET
    put("RTests", int(ET.parse(PROC / "tests.xml").getroot().find("testsuite").get("tests")), "int", "tests.xml")
    cov = json.loads((PROC / "coverage.json").read_text())["files"]
    core = [v["summary"] for k, v in cov.items() if not k.endswith(("run.py", "data/build.py"))]
    put("RCoverage", sum(c["covered_lines"] for c in core) / sum(c["num_statements"] for c in core), "pct0", "coverage.json")
    import re
    env = (ROOT / "results/ENVIRONMENT.md").read_text()
    put("ROllamaVersion", re.search(r"Ollama: .*?(\d+\.\d+\.\d+)", env).group(1), "raw", "ENVIRONMENT.md")
    (PROC / "numbers.json").write_text(json.dumps(NUM, indent=1, sort_keys=True))
    print(h.round(3).to_string(index=False))
    print(pd.DataFrame(T).round(3).to_string(index=False) if T else "no transfer rows")
    print("H3 pooled OURS-T - native:", round(d3, 3), [round(lo3, 3), round(hi3, 3)], "n", len(idx), "| rho", fid)
    print(pad.round(2).to_string(index=False))
    print(c.round(1).to_string(index=False))
    print(len(NUM), "numbers")


if __name__ == "__main__":
    main()
