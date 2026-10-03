"""Post-hoc analyses of the profiling logs (no new model calls; embeddings come from the cache):
  1. profiling sample size: how close a profile estimated from k development instances is to the full profile;
  2. block-value model quality: grouped cross-validated rank correlation between predicted and observed
     leave-one-block-out deltas, against embedding similarity alone.
Both are exploratory (not pre-registered) and labeled as such in the paper. Updates results/processed/numbers.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from mcv.compile.policies import Embedder  # noqa: E402
from mcv.data.build import load  # noqa: E402
from mcv.ir.blocks import TokenCounter  # noqa: E402
from mcv.profile.estimate import estimate, lobo_targets  # noqa: E402
from mcv.profile.features import BlockValueModel, block_features  # noqa: E402

PROC = ROOT / "results/processed"
MODEL = "qwen3:4b-instruct"
FAMS = ("facts", "history", "tool")
KS = (5, 10, 20, 30)
DRAWS = 300


def records() -> pd.DataFrame:
    p = ROOT / "results/raw" / f"profile_{MODEL.replace(':', '-')}" / "episodes.jsonl"
    df = pd.DataFrame([json.loads(l) for l in p.read_text().splitlines() if l.strip()])
    return df[~df.condition.str.startswith("pad:")].drop_duplicates(["family", "iid", "condition"])


def sample_size(df: pd.DataFrame) -> pd.DataFrame:
    full = {f: estimate(df[df.family == f].to_dict("records")) for f in FAMS}
    keys = [(f, t) for f in FAMS for t in sorted(full[f]["mcv"])]
    ref = np.array([full[f]["mcv"][t]["raw"] for f, t in keys])
    rng = np.random.default_rng(0)
    rows = []
    for k in KS:
        for _ in range(DRAWS):
            vals, top_ok = [], []
            for f in FAMS:
                d = df[df.family == f]
                ids = rng.choice(sorted(d.iid.unique()), size=k, replace=False)
                p = estimate(d[d.iid.isin(ids)].to_dict("records"))
                vals += [p["mcv"][t]["raw"] for t in sorted(full[f]["mcv"])]
                top_ok.append(max(p["mcv"], key=lambda t: p["mcv"][t]["raw"])
                              == max(full[f]["mcv"], key=lambda t: full[f]["mcv"][t]["raw"]))
            v = np.array(vals)
            rows.append({"k": k, "mae": float(np.abs(v - ref).mean()), "rho": float(spearmanr(v, ref)[0]),
                         "top_type_all": float(all(top_ok))})
    return pd.DataFrame(rows)


def value_model_cv(df: pd.DataFrame) -> pd.DataFrame:
    counter = TokenCounter(MODEL)
    emb = Embedder(ROOT / "results/cache/embeddings.sqlite")
    rows = []
    for f in FAMS:
        recs = df[df.family == f].to_dict("records")
        prof = json.loads((PROC / "profiles" / f"{MODEL.replace(':', '-')}_{f}.json").read_text())
        insts = {x.iid: x for x in load("dev", f)}
        X, y, g, typ = [], [], [], []
        for t in lobo_targets(recs):
            feats = block_features(insts[t["iid"]], prof, counter, emb)
            X.append(feats[t["block_id"]])
            y.append(t["delta"])
            g.append(t["iid"])
            typ.append(insts[t["iid"]].by_id()[t["block_id"]].type.value)
        X, y, g, typ = np.asarray(X), np.asarray(y), np.asarray(g), np.asarray(typ)
        pred = np.zeros(len(y))
        for tr, te in GroupKFold(n_splits=5).split(X, y, g):
            pred[te] = BlockValueModel().fit(X[tr].tolist(), y[tr].tolist()).predict(X[te].tolist())
        main_type = {"facts": "fact", "history": "history_turn", "tool": "tool_schema"}[f]
        m = typ == main_type
        rows.append({"family": f, "n_targets": len(y), "n_main_type": int(m.sum()),
                     "nonzero_frac": float((y[m] != 0).mean()),
                     "rho_model": float(spearmanr(pred[m], y[m])[0]), "rho_sim": float(spearmanr(X[m, -1], y[m])[0])})
    return pd.DataFrame(rows)


def main() -> None:
    df = records()
    ss = sample_size(df)
    ss.to_csv(PROC / "profile_sample_size.csv", index=False)
    agg = ss.groupby("k").agg(mae=("mae", "mean"), rho=("rho", "median"), top=("top_type_all", "mean")).reset_index()
    vm = value_model_cv(df)
    vm.to_csv(PROC / "value_model_cv.csv", index=False)
    num = json.loads((PROC / "numbers.json").read_text())
    W = {5: "Five", 10: "Ten", 20: "Twenty", 30: "Thirty"}
    for _, r in agg.iterrows():
        num[f"RSsMae{W[int(r.k)]}"] = {"value": float(r.mae), "fmt": "f2", "source": "profile_sample_size.csv"}
        num[f"RSsRho{W[int(r.k)]}"] = {"value": float(r.rho), "fmt": "f2", "source": "profile_sample_size.csv"}
        num[f"RSsTop{W[int(r.k)]}"] = {"value": float(r.top), "fmt": "pct0", "source": "profile_sample_size.csv"}
    num["RSsDraws"] = {"value": DRAWS, "fmt": "int", "source": "analyze_profiles.py"}
    F = {"facts": "Facts", "history": "History", "tool": "Tool"}
    for _, r in vm.iterrows():
        num[f"RCvModel{F[r.family]}"] = {"value": r.rho_model, "fmt": "f2", "source": "value_model_cv.csv"}
        num[f"RCvSim{F[r.family]}"] = {"value": r.rho_sim, "fmt": "f2", "source": "value_model_cv.csv"}
        num[f"RCvNonzero{F[r.family]}"] = {"value": r.nonzero_frac, "fmt": "pct0", "source": "value_model_cv.csv"}
        num[f"RCvN{F[r.family]}"] = {"value": r.n_main_type, "fmt": "int", "source": "value_model_cv.csv"}
    (PROC / "numbers.json").write_text(json.dumps(num, indent=1, sort_keys=True))
    print(agg.round(3).to_string(index=False))
    print(vm.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
