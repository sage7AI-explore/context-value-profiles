"""Phase-5 gate: integrity checks on data, logs and processed results -> results/VERIFICATION.md (exit 1 on failure).
  1. data hashes match TEST.lock;
  2. profiling and pilot runs touched development instances only; evaluation runs touched test instances only;
  3. expected row counts per run, no non-ok statuses;
  4. every test run started after the pre-registration commit (manifest git commit is a descendant of it);
  5. success re-derived from the logged answer with the deterministic checker for a seeded sample of 50 episodes per
     family (gold-label re-check);
  6. tokenizer agreement: Hugging Face count of the rendered prompt vs Ollama's prompt_eval_count (chat template adds
     a constant overhead; we report the spread of the difference);
  7. independent recomputation (RECOMPUTE.md) says MATCH."""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from mcv.agent.loop import extract_answer  # noqa: E402
from mcv.eval.metrics import success  # noqa: E402

RAW = ROOT / "results/raw"
PREREG = "944b921"
ADDENDUM = "6401964"  # addendum runs must descend from the addendum commit
EXPECTED = {"main_4b": 3 * 100 * (1 + 4 * 4), "main_4b_weak": 3 * 30 * 3 * 4,
            "addendum_test": 3 * 100 * 2 * 4, "addendum_calib": 3 * 20 * 11, "transfer_8b": 3 * 40 * 2, "transfer_8b_t": 3 * 40 * 2, "transfer_8b_native": 3 * 40 * 2}


def rows(run):
    return [json.loads(l) for l in (RAW / run / "episodes.jsonl").read_text().splitlines() if l.strip()]


def main() -> int:
    L, fails = ["# Verification", ""], 0

    def item(ok, text):
        nonlocal fails
        fails += not ok
        L.append(f"- [{'x' if ok else ' '}] {text}")

    lock = json.loads((ROOT / "data/processed/TEST.lock").read_text())
    path = ROOT / "data/processed/instances.jsonl"
    item(hashlib.sha256(path.read_bytes()).hexdigest() == lock["instances_sha256"], "instances.jsonl matches TEST.lock")
    inst = {json.loads(l)["iid"]: json.loads(l) for l in path.read_text().splitlines()}
    split = {k: v["split"] for k, v in inst.items()}
    for run in sorted(p.name for p in RAW.iterdir() if p.is_dir()):
        R = rows(run)
        want = "dev" if run.startswith(("profile", "pilot", "addendum_calib")) else "test"
        bad = sum(split[r["iid"]] != want for r in R)
        item(bad == 0, f"{run}: {len(R)} rows, all on the {want} split ({bad} violations)")
        if run in EXPECTED:
            st = Counter(r["status"] for r in R)
            item(len(R) == EXPECTED[run] and set(st) == {"ok"}, f"{run}: expected {EXPECTED[run]} rows, got {len(R)}; "
                 f"statuses {dict(st)}")
        if run.startswith(("main", "transfer", "addendum")):
            commits = {json.loads(l)["git_commit"] for l in (RAW / run / "manifest.jsonl").read_text().splitlines() if l.strip()}
            ref = ADDENDUM if run.startswith("addendum") else PREREG
            ok = all(subprocess.run(["git", "merge-base", "--is-ancestor", ref, c], cwd=ROOT).returncode == 0
                     for c in commits)
            item(ok, f"{run}: all {len(commits)} manifest commit(s) descend from the pre-registration commit {ref}")
    ev = [r for run in EXPECTED if not run.endswith("calib") for r in rows(run)]
    rng = random.Random(0)
    for fam in ("facts", "history", "tool"):
        sample = rng.sample([r for r in ev if r["family"] == fam], 50)
        agree = sum(success(inst[r["iid"]]["checker"], r["answer"], inst[r["iid"]]["gold"]) == r["success"] for r in sample)
        item(agree == 50, f"{fam}: success re-derived from the logged answer for 50 sampled episodes: {agree}/50 agree")
        # extraction from the logged reply (replies are stored truncated to the last 600 chars)
        ext = sum(extract_answer(inst[r["iid"]]["checker"], r["reply"]) == r["answer"] for r in sample)
        L.append(f"  - answer re-extracted from the logged reply: {ext}/50 identical")
    for model in sorted({r["model"] for r in ev}):
        diffs = [r["ollama_prompt_tokens"] - r["prompt_tokens_measured"] for r in ev
                 if r["model"] == model and r.get("ollama_prompt_tokens")]
        c = Counter(diffs)
        top, n_top = c.most_common(1)[0]
        item(n_top / len(diffs) > 0.95, f"tokenizer ({model}): Ollama prompt count minus HF count equals {top} "
             f"(chat-template overhead) in {n_top}/{len(diffs)} episodes; range [{min(diffs)}, {max(diffs)}]")
    rec = (ROOT / "results/RECOMPUTE.md").read_text()
    item("RESULT: MATCH" in rec, "independent recomputation: " + rec.strip().splitlines()[-1])
    L += ["", "RESULT: " + ("PASS" if fails == 0 else f"FAIL ({fails})")]
    (ROOT / "results/VERIFICATION.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[-12:]))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
