"""MCV estimator: type-level marginal values, short-variant values and pairwise interactions with bootstrap CIs.

Given paired ablation outcomes s(i, c) in {0,1} for instance i and condition c (see ablate.py):
  MCV(T)        = E_i[ s(i, full) - s(i, -T) ]
  short(T)      = E_i[ s(i, short:T) - s(i, -T) ]          value of T when rendered short
  I(T1, T2)     = E_i[ s(full) - s(-T1) - s(-T2) + s(-T1-T2) ]
                  > 0: complements (T1 worth more with T2), < 0: redundancy/conflict
Estimates are shrunk toward 0 by n / (n + N0) (sparse cells) and reported with paired percentile bootstrap CIs.
"""
from __future__ import annotations

import itertools
from collections import defaultdict

import numpy as np

N0 = 10
N_BOOT = 2000


def _boot(x: np.ndarray, seed: int = 0) -> tuple[float, float]:
    if len(x) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, len(x), (N_BOOT, len(x)))].mean(1)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def estimate(records: list, types: list | None = None) -> dict:
    """records: [{iid, condition, success}] for one (family, model). Returns a JSON-serializable profile."""
    s = defaultdict(dict)
    for r in records:
        s[r["iid"]][r["condition"]] = float(r["success"])
    if types is None:
        types = sorted({c[1:] for d in s.values() for c in d if c.startswith("-") and not c.startswith("-b:")
                        and c.count("-") == 1})
    prof = {"n_instances": len(s), "base": float(np.mean([d["full"] for d in s.values() if "full" in d])),
            "mcv": {}, "short": {}, "interaction": {}}

    def stat(vals: list) -> dict:
        x = np.asarray(vals, float)
        n = len(x)
        raw = float(x.mean()) if n else 0.0
        lo, hi = _boot(x)
        return {"raw": raw, "value": raw * n / (n + N0) if n else 0.0, "lo": lo, "hi": hi, "n": n}

    for t in types:
        d = [v["full"] - v[f"-{t}"] for v in s.values() if "full" in v and f"-{t}" in v]
        prof["mcv"][t] = stat(d)
        d2 = [v[f"short:{t}"] - v[f"-{t}"] for v in s.values() if f"short:{t}" in v and f"-{t}" in v]
        if d2:
            prof["short"][t] = stat(d2)
    for t1, t2 in itertools.combinations(types, 2):
        key = f"-{t1}-{t2}" if any(f"-{t1}-{t2}" in v for v in s.values()) else f"-{t2}-{t1}"
        d = [v["full"] - v[f"-{t1}"] - v[f"-{t2}"] + v[key] for v in s.values()
             if all(c in v for c in ("full", f"-{t1}", f"-{t2}", key))]
        if d:
            prof["interaction"][f"{t1}|{t2}"] = stat(d)
    return prof


def lobo_targets(records: list) -> list:
    """Leave-one-block-out targets: [{iid, block_id, delta}] with delta = s(full) - s(-b)."""
    s = defaultdict(dict)
    for r in records:
        s[r["iid"]][r["condition"]] = float(r["success"])
    out = []
    for iid, d in s.items():
        for c, v in d.items():
            if c.startswith("-b:") and "full" in d:
                out.append({"iid": iid, "block_id": c[3:], "delta": d["full"] - v})
    return out
