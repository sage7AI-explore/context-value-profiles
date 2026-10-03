"""Addendum A analysis (PLAN.md): calibrated relevance+stopping (B2S) and hybrid (HYB) vs the main-study policies.
H6: B2S@8k non-inferior to B0 (margin 0.05); token difference B2S@8k - OURS@8k.  H7: HYB AUBC > B2 (Wilcoxon).
H8: HYB@8k non-inferior to B0 with fewer tokens.  One Holm family of 9. Writes addendum.csv, addendum_tests.csv,
addendum_success.csv and adds macros to results/processed/numbers.json (run after analyze_extra.py)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[2]
RAW, PROC = ROOT / "results/raw", ROOT / "results/processed"
BUDGETS, UNB, N_BOOT, MARGIN = [1000, 2000, 4000, 8000], 1_000_000_000, 10_000, 0.05
FAMS = {"facts": "Facts", "history": "History", "tool": "Tool"}


def jl(run):
    return pd.DataFrame([json.loads(l) for l in (RAW / run / "episodes.jsonl").read_text().splitlines() if l.strip()])


def boot(d, seed=0):
    d = np.asarray(d, float)
    bs = d[np.random.default_rng(seed).integers(0, len(d), (N_BOOT, len(d)))].mean(1)
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), bs


def area(ys):
    x = np.log2(BUDGETS)
    return float(np.trapezoid(ys, x) / (x[-1] - x[0]))


def holm(ps):
    order, adj, run = np.argsort(ps), [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def main() -> None:
    main_df = jl("main_4b")
    add = jl("addendum_test")
    add["policy"] = add.policy.str.split("@").str[0]
    df = pd.concat([main_df, add], ignore_index=True)
    df = df[df.status == "ok"]
    df["success"] = df.success.astype(float)
    S = df.groupby(["family", "policy", "budget"]).agg(n=("iid", "count"), success=("success", "mean"),
                                                         tokens=("prompt_tokens_measured", "mean")).reset_index()
    S.to_csv(PROC / "addendum_success.csv", index=False)
    A = {}
    for (f, p, i), g in df.groupby(["family", "policy", "iid"]):
        s = dict(zip(g.budget, g.success))
        ys = [s.get(UNB)] * 4 if p == "B0" else [s.get(b) for b in BUDGETS]
        if None not in ys:
            A[(f, p, i)] = area(ys)
    num = json.loads((PROC / "numbers.json").read_text())

    def put(k, v, fmt, src):
        num[k] = {"value": v, "fmt": fmt, "source": src}

    cal = json.loads((PROC / "calibration.json").read_text())
    tests, rows = [], []
    for f, F in FAMS.items():
        for p, nm in (("B2S", "Stop"), ("HYB", "Hyb")):
            put(f"RTau{nm}{F}", float(cal[f][p]), "f3", "calibration.json")
        ids = sorted({i for (g, p, i) in A if g == f and p == "HYB"})
        aub = {p: np.array([A[(f, p, i)] for i in ids]) for p in ("B2", "OURS", "HYB", "B2S", "B0")}
        for p, nm in (("HYB", "Hyb"), ("B2S", "Stop")):
            e, lo, hi, _ = boot(aub[p])
            put(f"RAubc{F}{nm}", e, "f3", "addendum")
            put(f"RAubc{F}{nm}Lo", lo, "f3", "addendum")
            put(f"RAubc{F}{nm}Hi", hi, "f3", "addendum")
            rows.append({"family": f, "policy": p, "n": len(ids), "aubc": e, "lo": lo, "hi": hi})
        d = aub["HYB"] - aub["B2"]
        e, lo, hi, _ = boot(d)
        pw = float(wilcoxon(d, zero_method="zsplit").pvalue) if np.any(d != 0) else 1.0
        tests.append({"hyp": "H7", "family": f, "n": len(d), "diff": e, "lo": lo, "hi": hi, "p": pw})
        e2, lo2, hi2, _ = boot(aub["HYB"] - aub["OURS"])
        put(f"RHybVsOurs{F}", e2, "f3", "addendum")
        put(f"RHybVsOurs{F}Lo", lo2, "f3", "addendum")
        put(f"RHybVsOurs{F}Hi", hi2, "f3", "addendum")
        g = df[df.family == f]
        b0 = g[g.policy == "B0"].set_index("iid")
        for p, hyp in (("B2S", "H6"), ("HYB", "H8")):
            o = g[(g.policy == p) & (g.budget == 8000)].set_index("iid")
            idx = o.index.intersection(b0.index)
            e, lo, hi, bs = boot(o.loc[idx, "success"].values - b0.loc[idx, "success"].values)
            pb = float(((bs <= -MARGIN).sum() + 1) / (N_BOOT + 1))
            tests.append({"hyp": hyp, "family": f, "n": len(idx), "diff": e, "lo": lo, "hi": hi, "p": pb,
                          "tokens": float(o.loc[idx, "prompt_tokens_measured"].mean()),
                          "tokens_b0": float(b0.loc[idx, "prompt_tokens_measured"].mean())})
        o = g[(g.policy == "B2S") & (g.budget == 8000)].set_index("iid").prompt_tokens_measured
        u = g[(g.policy == "OURS") & (g.budget == 8000)].set_index("iid").prompt_tokens_measured
        idx = o.index.intersection(u.index)
        e, lo, hi, _ = boot((o.loc[idx] - u.loc[idx]).values)
        put(f"RStopMinusOursTok{F}", e, "int", "addendum")
        put(f"RStopMinusOursTok{F}Lo", lo, "int", "addendum")
        put(f"RStopMinusOursTok{F}Hi", hi, "int", "addendum")
    T = pd.DataFrame(tests)
    T["p_holm"] = holm(list(T.p))
    T.to_csv(PROC / "addendum_tests.csv", index=False)
    pd.DataFrame(rows).to_csv(PROC / "addendum.csv", index=False)
    HN = {"H6": "HSix", "H7": "HSeven", "H8": "HEight"}
    for _, r in T.iterrows():
        k = f"R{HN[r.hyp]}{FAMS[r.family]}"
        put(k + "Diff", r["diff"], "f3", "addendum_tests.csv")
        put(k + "Lo", r.lo, "f3", "addendum_tests.csv")
        put(k + "Hi", r.hi, "f3", "addendum_tests.csv")
        put(k + "P", r.p_holm, "p3", "addendum_tests.csv")
        if r.hyp in ("H6", "H8"):
            nm = "Stop" if r.hyp == "H6" else "Hyb"
            put(f"RTok{nm}{FAMS[r.family]}", r.tokens, "int", "addendum_tests.csv")
            put(f"RTokCut{nm}{FAMS[r.family]}", 1 - r.tokens / r.tokens_b0, "pct1", "addendum_tests.csv")
    BW = {1000: "One", 2000: "Two", 4000: "Four", 8000: "Eight"}
    for _, r in S[S.policy.isin(["B2S", "HYB"])].iterrows():
        put(f"RSuc{FAMS[r.family]}{'Stop' if r.policy == 'B2S' else 'Hyb'}{BW[r.budget]}", r.success, "pct0", "addendum_success.csv")
    sev = T[T.hyp == "H7"]
    put("RHSevenWins", int(((sev.p_holm < 0.05) & (sev["diff"] > 0)).sum()), "int", "addendum_tests.csv")
    for hyp, nm in (("H6", "Six"), ("H8", "Eight")):
        put(f"RH{nm}Pass", int((T[T.hyp == hyp].lo > -MARGIN).sum()), "int", "addendum_tests.csv")
    put("RNAddendumEpisodes", len(add), "int", "addendum_test")
    (PROC / "numbers.json").write_text(json.dumps(num, indent=1, sort_keys=True))
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print(T.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
