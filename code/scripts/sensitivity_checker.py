"""Sensitivity analysis for a checker defect found while reading transcripts after the test runs: the tool checker
compared list-valued arguments as JSON strings, so [-1, 2] failed against the allowed [-1.0, 2.0] (BFCL accepts an int
where a float is expected). The pre-registered checker stays primary; this script rescored every logged test answer
with element-wise numeric comparison and reports whether any hypothesis outcome changes. Profiles are not re-estimated
(they were measured with the checker in force at the time). Updates results/processed/numbers.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from mcv.eval import metrics as M  # noqa: E402

RAW, PROC = ROOT / "results/raw", ROOT / "results/processed"
BUDGETS, UNB = [1000, 2000, 4000, 8000], 1_000_000_000


def eq(a, v) -> bool:
    if not isinstance(a, bool) and not isinstance(v, bool):
        na, nv = M._num(a), M._num(v)
        if na is not None and nv is not None:
            return abs(na - nv) < 1e-6
    if isinstance(a, list) and isinstance(v, list):
        return len(a) == len(v) and all(eq(x, y) for x, y in zip(a, v))
    if isinstance(a, dict) and isinstance(v, dict):
        return a.keys() == v.keys() and all(eq(a[k], v[k]) for k in a)
    if isinstance(a, str) and isinstance(v, str):
        return M.normalize(a) == M.normalize(v)
    return a == v


def fixed_value_ok(v, allowed) -> bool:
    return any(not (a == "" or a is None) and eq(a, v) for a in allowed)


def main() -> None:
    inst = {json.loads(l)["iid"]: json.loads(l) for l in (ROOT / "data/processed/instances.jsonl").read_text().splitlines()}
    M._value_ok = fixed_value_ok
    succ, flips = {}, 0
    for run in ("main_4b", "main_4b_weak"):
        for line in (RAW / run / "episodes.jsonl").read_text().splitlines():
            r = json.loads(line)
            x = inst[r["iid"]]
            s = float(M.success(x["checker"], r["answer"], x["gold"]))
            flips += s != float(r["success"])
            succ.setdefault((r["family"], r["policy"], r["iid"]), {})[r["budget"]] = s

    def aubc(f, p):
        out = {}
        for (g, q, i), s in succ.items():
            if g == f and q == p:
                ys = [s[UNB]] * 4 if p == "B0" else [s.get(b) for b in BUDGETS]
                if None not in ys:
                    out[i] = M.aubc(BUDGETS, ys)
        return out

    num = json.loads((PROC / "numbers.json").read_text())
    num["RCheckerFlips"] = {"value": flips, "fmt": "int", "source": "sensitivity_checker.py"}
    lines = []
    for f, F in (("facts", "Facts"), ("history", "History"), ("tool", "Tool")):
        a, b = aubc(f, "OURS"), aubc(f, "B2")
        d = float(np.mean([a[i] - b[i] for i in a if i in b]))
        o = [succ[(f, "OURS", i)][8000] - succ[(f, "B0", i)][UNB] for (g, p, i) in succ if g == f and p == "OURS"]
        num[f"RSensHOne{F}"] = {"value": d, "fmt": "f3", "source": "sensitivity_checker.py"}
        num[f"RSensHOneb{F}"] = {"value": float(np.mean(o)), "fmt": "f3", "source": "sensitivity_checker.py"}
        lines.append(f"{f}: H1 diff {d:+.4f}; H1b success diff {np.mean(o):+.4f}")
    a = {(f, i): v for f in ("facts", "history", "tool") for i, v in aubc(f, "OURS").items()}
    b = {(f, i): v for f in ("facts", "history", "tool") for i, v in aubc(f, "OURS-A").items()}
    h2 = float(np.mean([a[k] - b[k] for k in a if k in b]))
    num["RSensHTwo"] = {"value": h2, "fmt": "f3", "source": "sensitivity_checker.py"}
    lines.append(f"H2 pooled diff {h2:+.4f}")
    (PROC / "numbers.json").write_text(json.dumps(num, indent=1, sort_keys=True))
    print("flipped episodes:", flips)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
