"""results/raw -> results/processed/*.csv + numbers.json (pre-registered analysis; see PLAN.md).

Primary metric: per-instance AUBC = normalized trapezoid area of success over log2(budget) for budgets {1k,2k,4k,8k};
B0 (unbounded) is constant across budgets. Paired over instances: bootstrap CIs (10,000), Wilcoxon signed-rank and
paired sign-flip permutation tests; Holm correction across the H1/H2 family of comparisons.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from mcv.eval.metrics import aubc  # noqa: E402

RAW, PROC = ROOT / "results/raw", ROOT / "results/processed"
BUDGETS = [1000, 2000, 4000, 8000]
UNB = 10 ** 9
BASELINES = ["B1", "B2", "B3", "B4", "B5"]
N_BOOT = 10_000
MARGIN = 0.05


def load_eval(prefixes: tuple) -> pd.DataFrame:
    rows = []
    for d in sorted(RAW.iterdir()):
        if d.is_dir() and d.name.startswith(prefixes) and (d / "episodes.jsonl").exists():
            rows += [json.loads(l) for l in (d / "episodes.jsonl").read_text().splitlines() if l.strip()]
    df = pd.DataFrame(rows)
    if not len(df):
        return df
    df["policy_label"] = np.where((df["policy"] == "OURS") & (df["profile_model"] != df["model"]) & df["profile_model"].notna(),
                                  "OURS-T", df["policy"])
    if "label" in df:  # run.py records OURS-T / OURS-native explicitly
        df["policy_label"] = df["label"].fillna(df["policy_label"])
    return df


def boot_mean(x: np.ndarray, seed: int = 0) -> tuple:
    x = np.asarray(x, float)
    if len(x) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, len(x), (N_BOOT, len(x)))].mean(1)
    return float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def perm_p(d: np.ndarray, seed: int = 0) -> float:
    d = np.asarray(d, float)
    if np.allclose(d, 0):
        return 1.0
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1, 1], size=(N_BOOT, len(d)))
    return float(((np.abs((signs * d).mean(1)) >= abs(d.mean()) - 1e-12).sum() + 1) / (N_BOOT + 1))


def holm(ps: list) -> list:
    order = np.argsort(ps)
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def per_instance_aubc(df: pd.DataFrame) -> pd.DataFrame:
    """Rows: model, family, policy_label, iid, aubc (requires all budgets; B0 replicated)."""
    ok = df[df["status"] == "ok"]
    out = []
    for (m, f, p, iid), g in ok.groupby(["model", "family", "policy_label", "iid"]):
        s = dict(zip(g["budget"], g["success"].astype(float)))
        if p == "B0":
            ys = [s.get(UNB, np.nan)] * len(BUDGETS)
        else:
            ys = [s.get(b, np.nan) for b in BUDGETS]
        if any(np.isnan(ys)):
            continue
        out.append({"model": m, "family": f, "policy": p, "iid": iid, "aubc": aubc(BUDGETS, ys)})
    return pd.DataFrame(out)


def success_table(df: pd.DataFrame) -> pd.DataFrame:
    ok = df[df["status"] == "ok"]
    rows = []
    for (m, f, p, b), g in ok.groupby(["model", "family", "policy_label", "budget"]):
        e, lo, hi = boot_mean(g["success"].astype(float).values)
        rows.append({"model": m, "family": f, "policy": p, "budget": b, "n": len(g), "success": e, "lo": lo, "hi": hi,
                     "prompt_tokens": g["prompt_tokens_measured"].mean(),
                     "over_budget": int((g["prompt_tokens_measured"] > g["budget"]).sum())})
    return pd.DataFrame(rows)


def compare(A: pd.DataFrame, a: str, b: str) -> dict | None:
    x = A[A["policy"] == a].set_index("iid")["aubc"]
    y = A[A["policy"] == b].set_index("iid")["aubc"]
    idx = x.index.intersection(y.index)
    if len(idx) < 5:
        return None
    d = (x.loc[idx] - y.loc[idx]).values
    e, lo, hi = boot_mean(d)
    try:
        pw = float(wilcoxon(d, zero_method="zsplit").pvalue) if np.any(d != 0) else 1.0
    except ValueError:
        pw = 1.0
    sd = d.std(ddof=1)
    return {"a": a, "b": b, "n": len(idx), "diff": e, "lo": lo, "hi": hi, "p_wilcoxon": pw, "p_perm": perm_p(d),
            "dz": float(e / sd) if sd > 0 else np.nan}


def h1b_tests(df: pd.DataFrame, budget: int = 8000) -> list:
    """Non-inferiority of success(OURS@8k) vs B0 with margin MARGIN. p = one-sided paired bootstrap p-value for
    H0: mean d <= -MARGIN, i.e. (#{bootstrap means <= -MARGIN} + 1) / (N_BOOT + 1); a shifted Wilcoxon is invalid for
    binary outcomes with many ties."""
    ok, out = df[df["status"] == "ok"], []
    for (m, f), g in ok.groupby(["model", "family"]):
        o = g[(g["policy_label"] == "OURS") & (g["budget"] == budget)].set_index("iid")
        b = g[g["policy_label"] == "B0"].set_index("iid")
        idx = o.index.intersection(b.index)
        if len(idx) < 5:
            continue
        d = o.loc[idx, "success"].astype(float).values - b.loc[idx, "success"].astype(float).values
        e, lo, hi = boot_mean(d)
        bs = d[np.random.default_rng(0).integers(0, len(d), (N_BOOT, len(d)))].mean(1)
        pw = float(((bs <= -MARGIN).sum() + 1) / (N_BOOT + 1))
        sd = d.std(ddof=1)
        out.append({"model": m, "family": f, "hyp": "H1b", "best_baseline": "B0", "a": "OURS@8k", "b": "B0", "n": len(idx),
                    "diff": e, "lo": lo, "hi": hi, "p_wilcoxon": pw, "p_perm": np.nan, "dz": float(e / sd) if sd > 0 else np.nan,
                    "tokens_a": o.loc[idx, "prompt_tokens_measured"].mean(), "tokens_b": b.loc[idx, "prompt_tokens_measured"].mean()})
    return out


def main(prefix_main: str = "main_", prefix_transfer: str = "transfer_") -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    df = load_eval((prefix_main, prefix_transfer, "pilot_"))
    if not len(df):
        print("no eval runs yet")
        return
    df["split_run"] = df["run"].str.split("_").str[0]
    dev = df["run"].str.startswith("pilot")
    success_table(df[~dev]).to_csv(PROC / "success.csv", index=False)
    success_table(df[dev].assign(policy_label=df["run"] + ":" + df["policy_label"])).to_csv(PROC / "success_dev.csv", index=False)
    main_df = df[df["run"].str.startswith(prefix_main)]
    A = per_instance_aubc(main_df)
    A.to_csv(PROC / "aubc_per_instance.csv", index=False)
    rows = []
    for (m, f, p), g in A.groupby(["model", "family", "policy"]):
        e, lo, hi = boot_mean(g["aubc"].values)
        rows.append({"model": m, "family": f, "policy": p, "n": len(g), "aubc": e, "lo": lo, "hi": hi})
    agg = pd.DataFrame(rows)
    agg.to_csv(PROC / "aubc.csv", index=False)
    tests = []
    for (m, f), g in A.groupby(["model", "family"]):
        means = g.groupby("policy")["aubc"].mean()
        best = max((p for p in BASELINES if p in means), key=lambda p: means[p], default=None)
        if best and "OURS" in means:
            r = compare(g, "OURS", best)
            if r:
                tests.append({"model": m, "family": f, "hyp": "H1", "best_baseline": best, **r})
    for m, g in A.groupby("model"):  # H2 pooled over families
        g = g.assign(iid=g["family"] + "/" + g["iid"].astype(str))
        r = compare(g, "OURS", "OURS-A")
        if r:
            tests.append({"model": m, "family": "pooled", "hyp": "H2", "best_baseline": "", **r})
    tests += h1b_tests(main_df)
    T = pd.DataFrame(tests)
    if len(T):
        T["p_holm"] = holm(list(T["p_wilcoxon"]))
    T.to_csv(PROC / "tests.csv", index=False)
    print(agg.round(3).to_string(index=False))
    if len(T):
        print(T[["model", "family", "hyp", "best_baseline", "n", "diff", "lo", "hi", "p_wilcoxon", "p_holm"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
