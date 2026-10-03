"""Addendum A calibration (PLAN.md): per family and policy (B2S, HYB), choose the tau with the lowest mean measured
prompt tokens at 8k on dev instances 41-60, subject to success >= success(B0) - 0.05; ties go to the smaller tau.
Reads results/raw/addendum_calib, writes results/processed/calibration.json (+ calibration_table.csv)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MARGIN = 0.05


def main() -> None:
    p = ROOT / "results/raw/addendum_calib/episodes.jsonl"
    df = pd.DataFrame([json.loads(l) for l in p.read_text().splitlines() if l.strip()])
    df = df[df.status == "ok"]
    out, rows = {}, []
    for fam, d in df.groupby("family"):
        b0 = d[d.policy == "B0"].success.astype(float).mean()
        out[fam] = {"B0_success": b0}
        for base in ("B2S", "HYB"):
            g = d[d.policy.str.startswith(base + "@")]
            agg = g.groupby("policy").agg(success=("success", "mean"), tokens=("prompt_tokens_measured", "mean"),
                                          n=("iid", "count")).reset_index()
            agg["tau"] = agg.policy.str.split("@").str[1]
            agg["eligible"] = agg.success >= b0 - MARGIN
            for _, r in agg.iterrows():
                rows.append({"family": fam, "policy": base, "tau": r.tau, "n": r.n, "success": r.success,
                             "tokens": r.tokens, "eligible": r.eligible, "b0_success": b0})
            el = agg[agg.eligible].assign(tf=agg.tau.astype(float)).sort_values(["tokens", "tf"])
            out[fam][base] = el.iloc[0].tau if len(el) else "-1.0"
    (ROOT / "results/processed/calibration.json").write_text(json.dumps(out, indent=1))
    pd.DataFrame(rows).to_csv(ROOT / "results/processed/calibration_table.csv", index=False)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
