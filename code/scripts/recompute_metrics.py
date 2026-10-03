"""Independent recomputation of the headline metrics from the raw logs, written without importing process_results.py,
analyze_extra.py or mcv.eval. Uses only json + math; must match results/processed exactly (|diff| < 1e-9).
Checks: per-policy mean AUBC (aubc.csv), paired mean differences of the tests (tests.csv), H1b token means (h1b.csv),
and success at each budget (success.csv)."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW, PROC = ROOT / "results/raw", ROOT / "results/processed"
BUDGETS = [1000, 2000, 4000, 8000]
UNB = 1_000_000_000


def episodes(runs):
    for run in runs:
        for line in (RAW / run / "episodes.jsonl").read_text().splitlines():
            if line.strip():
                yield json.loads(line)


def area(ys):
    xs = [math.log2(b) for b in BUDGETS]
    tot = sum((xs[i + 1] - xs[i]) * (ys[i] + ys[i + 1]) / 2 for i in range(len(xs) - 1))
    return tot / (xs[-1] - xs[0])


def main() -> int:
    succ = defaultdict(dict)  # (family, policy, iid) -> {budget: success}
    toks = defaultdict(dict)
    for r in episodes(["main_4b", "main_4b_weak"]):
        if r["status"] != "ok":
            continue
        k = (r["family"], r["policy"], r["iid"])
        succ[k][r["budget"]] = 1.0 if r["success"] else 0.0
        toks[k][r["budget"]] = r["prompt_tokens_measured"]
    per = defaultdict(dict)  # (family, policy) -> {iid: aubc}
    for (f, p, i), s in succ.items():
        ys = [s[UNB]] * 4 if p == "B0" else [s.get(b) for b in BUDGETS]
        if None not in ys:
            per[(f, p)][i] = area(ys)
    problems, checked = [], 0

    def check(what, mine, theirs):
        nonlocal checked
        checked += 1
        if abs(mine - theirs) > 1e-9:
            problems.append(f"{what}: recomputed {mine!r} vs processed {theirs!r}")

    for row in csv.DictReader((PROC / "aubc.csv").open()):
        if row["model"] != "qwen3:4b-instruct":
            continue
        v = per[(row["family"], row["policy"])]
        check(f"AUBC {row['family']}/{row['policy']}", sum(v.values()) / len(v), float(row["aubc"]))
        check(f"n {row['family']}/{row['policy']}", len(v), int(row["n"]))
    for row in csv.DictReader((PROC / "tests.csv").open()):
        f = row["family"]
        if row["hyp"] == "H1":
            a, b = per[(f, row["a"])], per[(f, row["b"])]
            d = [a[i] - b[i] for i in a if i in b]
        elif row["hyp"] == "H2":
            d = [per[(g, "OURS")][i] - per[(g, "OURS-A")][i] for g in ("facts", "history", "tool")
                 for i in per[(g, "OURS")] if i in per[(g, "OURS-A")]]
        else:  # H1b: success(OURS@8k) - success(B0)
            d = [succ[(f, "OURS", i)][8000] - succ[(f, "B0", i)][UNB] for (g, p, i) in list(succ)
                 if g == f and p == "OURS" and 8000 in succ[(f, "OURS", i)] and UNB in succ.get((f, "B0", i), {})]
        check(f"{row['hyp']} {f} diff", sum(d) / len(d), float(row["diff"]))
        check(f"{row['hyp']} {f} n", len(d), int(row["n"]))
    for row in csv.DictReader((PROC / "h1b.csv").open()):
        f = row["family"]
        o = [toks[(f, "OURS", i)][8000] for (g, p, i) in list(toks) if g == f and p == "OURS" and 8000 in toks[(g, p, i)]]
        b0 = [toks[(f, "B0", i)][UNB] for (g, p, i) in list(toks) if g == f and p == "B0"]
        check(f"H1b {f} tokens OURS", sum(o) / len(o), float(row["tokens_ours"]))
        check(f"H1b {f} tokens B0", sum(b0) / len(b0), float(row["tokens_b0"]))
    for row in csv.DictReader((PROC / "success.csv").open()):
        if row["model"] != "qwen3:4b-instruct":
            continue
        b = int(row["budget"])
        v = [s[b] for (g, p, i), s in succ.items() if g == row["family"] and p == row["policy"] and b in s]
        check(f"success {row['family']}/{row['policy']}@{b}", sum(v) / len(v), float(row["success"]))
    out = ["# Independent recomputation", "", f"Checked {checked} quantities from results/raw against results/processed.",
           "", "RESULT: " + ("MATCH" if not problems else f"MISMATCH ({len(problems)})")] + [f"- {p}" for p in problems]
    (ROOT / "results" / "RECOMPUTE.md").write_text("\n".join(out) + "\n")
    print(out[2], out[4])
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
