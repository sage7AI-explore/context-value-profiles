"""Exploratory (not pre-registered) analysis of the existing logs: the profile note as a fallback at small budgets.

Question: the 4B profile measures MCV(note) = 0 because it is a leave-one-type-out effect *from the full context*,
where history already supplies the answer. At the 1k history budget, does excluding the note remove a fallback when the
session holding the latest update is not selected?

For every history episode at 1k we record whether the gold (update) session(s) and the note were selected, and whether
the note is current (meta.stale_note == False). Writes results/processed/note_fallback.csv and adds macros to
results/processed/numbers.json. No model calls. Run after analyze_addendum.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW, PROC = ROOT / "results/raw", ROOT / "results/processed"
RUNS = ("main_4b", "main_4b_weak", "addendum_test")
BUDGET = 1000


def main() -> None:
    inst = {}
    for line in (ROOT / "data/processed/instances.jsonl").read_text().splitlines():
        d = json.loads(line)
        if d["family"] == "history":
            inst[d["iid"]] = {"stale": bool(d["meta"]["stale_note"]),
                              "gold": [b["id"] for b in d["blocks"] if b["meta"].get("gold")]}
    rows = []
    for run in RUNS:
        for line in (RAW / run / "episodes.jsonl").read_text().splitlines():
            e = json.loads(line)
            if e["family"] != "history" or e["budget"] != BUDGET:
                continue
            sel, meta = e["selection"], inst[e["iid"]]
            rows.append({"run": run, "policy": e["label"].split("@")[0], "iid": e["iid"], "success": bool(e["success"]),
                         "gold_in": all(g in sel for g in meta["gold"]), "note_in": "note" in sel,
                         "note_current": not meta["stale"]})
    D = pd.DataFrame(rows)
    D = D[D.policy != "B3"]  # LLMLingua-2 compresses all blocks; block-level membership is not defined for it
    D.groupby(["policy", "gold_in", "note_in", "note_current"]).success.agg(["mean", "size"]).reset_index() \
        .to_csv(PROC / "note_fallback.csv", index=False)

    ours = D[D.policy == "OURS"]
    fail = ours[~ours.success]
    lost_with_current_note = fail[(~fail.gold_in) & fail.note_current]
    # Rescue rate: policies that KEPT the note, missed the gold session, and the note was current.
    resc = D[(D.policy.isin(["B1", "B4", "B5"])) & (~D.gold_in) & D.note_in & D.note_current]
    num = json.loads((PROC / "numbers.json").read_text())

    def put(k, v, fmt, src="note_fallback.csv (exploratory)"):
        num[k] = {"value": v, "fmt": fmt, "source": src}

    put("RNoteInOursOne", float(ours.note_in.mean()), "pct0")
    put("RNoteInRelOne", float(D[D.policy == "B2"].note_in.mean()), "pct0")
    put("ROursFailHistOne", int(len(fail)), "int")
    put("ROursFailCurrentNote", int(len(lost_with_current_note)), "int")
    put("RNoteRescueRate", float(resc.success.mean()), "pct0")
    put("RNoteRescueN", int(len(resc)), "int")
    # Share of paired (instance, budget) episodes where OURS and OURS-A differ in outcome (main grid).
    main = [json.loads(l) for l in (RAW / "main_4b" / "episodes.jsonl").read_text().splitlines() if l.strip()]
    succ = {(e["label"], e["family"], e["iid"], e["budget"]): e["success"] for e in main}
    for fam, nm in (("facts", "Facts"), ("history", "History"), ("tool", "Tool")):
        keys = [k for k in succ if k[0] == "OURS" and k[1] == fam]
        diff = sum(succ[k] != succ[("OURS-A",) + k[1:]] for k in keys) / len(keys)
        put(f"RSelOutcomeDiff{nm}", float(diff), "pct1", "main_4b (OURS vs OURS-A outcome differs)")
    (PROC / "numbers.json").write_text(json.dumps(num, indent=1, sort_keys=True))
    print(f"OURS@1k history: {len(fail)} failures; {len(lost_with_current_note)} had a current note that was not sent; "
          f"note sent in {ours.note_in.mean():.0%} of OURS plans; policies that kept a current note without the gold "
          f"session succeeded in {resc.success.mean():.0%} of {len(resc)} episodes")


if __name__ == "__main__":
    main()
