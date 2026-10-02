"""Experiment runner (resumable). Profiling on dev, evaluation on test, smoke test.

  uv run python -m mcv.run profile --model qwen3:4b --family facts [--limit N] [--pad]
  uv run python -m mcv.run fit --model qwen3:4b                     # profiles + value models from profiling logs
  uv run python -m mcv.run eval --model qwen3:8b --family facts --policies B1,B2,OURS --budgets 1000,2000 --profile-model qwen3:4b
  uv run python -m mcv.run --smoke
Every call is logged as JSONL in results/raw/<run>/episodes.jsonl with a manifest (git commit, model digest, data hash).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pickle
import subprocess
import sys
import time
from pathlib import Path

import httpx

from mcv.agent.loop import Cache, call, extract_answer
from mcv.compile.knapsack import BudgetError
from mcv.compile.policies import POLICIES, Embedder, prompt_for
from mcv.data.build import load
from mcv.eval.metrics import success
from mcv.ir.blocks import TokenCounter
from mcv.profile.ablate import conditions, render_condition
from mcv.profile.estimate import estimate, lobo_targets
from mcv.profile.features import BlockValueModel, block_features

ROOT = Path(__file__).resolve().parents[2]
RAW, PROC = ROOT / "results/raw", ROOT / "results/processed"
UNBOUNDED = 10 ** 9


def _manifest(run_dir: Path, args: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        tags = httpx.get("http://localhost:11434/api/tags", timeout=10).json()["models"]
    except Exception:  # noqa: BLE001
        tags = []
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout.splitlines()[:6]
    seg = {"started": dt.datetime.now(dt.timezone.utc).isoformat(), "git_commit": commit, "args": args,
           "model_digests": {t["name"]: t["digest"] for t in tags},
           "data_lock": json.loads((ROOT / "data/processed/TEST.lock").read_text()), "vm_stat": vm}
    p = run_dir / "manifest.jsonl"
    with p.open("a") as f:
        f.write(json.dumps(seg) + "\n")


def _done(path: Path, keyf) -> set:
    if not path.exists():
        return set()
    return {keyf(json.loads(l)) for l in path.read_text().splitlines() if l.strip()}


def profile(model: str, family: str, limit: int | None, pad: bool, seed: int = 0, lobo: int = 6) -> None:
    run = RAW / f"profile_{model.replace(':', '-')}"
    _manifest(run, {"cmd": "profile", "model": model, "family": family, "limit": limit, "pad": pad})
    out = run / "episodes.jsonl"
    done = _done(out, lambda r: (r["iid"], r["condition"], r["seed"]))
    counter = TokenCounter(model)
    cache = Cache(ROOT / "results/cache/responses.sqlite")
    insts = load("dev", family)[:limit] if limit else load("dev", family)
    with httpx.Client() as http:
        for inst in insts:
            for name, selection in conditions(inst, n_lobo=lobo, pad=pad).items():
                if (inst.iid, name, seed) in done:
                    continue
                prompt = render_condition(inst, name, selection, counter)
                r = call(http, model, seed, prompt, cache)
                ans = extract_answer(inst.checker, r["text"])
                rec = {"run": run.name, "iid": inst.iid, "family": family, "model": model, "seed": seed,
                       "condition": name, "success": success(inst.checker, ans, inst.gold), "answer": ans,
                       "reply": r["text"][-600:], "prompt_tokens": r["prompt_tokens"], "seconds": r["seconds"],
                       "cached": r["cached"], "cache_key": r["key"],
                       "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
                with out.open("a") as f:
                    f.write(json.dumps(rec) + "\n")


def fit(model: str) -> None:
    """Estimate per-family profiles and fit block-value models from the profiling log of ``model``."""
    rows = [json.loads(l) for l in (RAW / f"profile_{model.replace(':', '-')}" / "episodes.jsonl").read_text().splitlines()]
    counter = TokenCounter(model)
    outdir = PROC / "profiles"
    outdir.mkdir(parents=True, exist_ok=True)
    for family in sorted({r["family"] for r in rows}):
        recs = [r for r in rows if r["family"] == family and not r["condition"].startswith("pad:")]
        prof = estimate(recs)
        prof.update({"model": model, "family": family})
        insts = {x.iid: x for x in load("dev", family)}
        X, y = [], []
        for t in lobo_targets(recs):
            f = block_features(insts[t["iid"]], prof, counter)
            X.append(f[t["block_id"]])
            y.append(t["delta"])
        vm = BlockValueModel().fit(X, y)
        prof["value_model"] = {"n": len(y), "coef": vm.m.coef_.tolist() if vm.fitted else None,
                               "intercept": float(vm.m.intercept_) if vm.fitted else None}
        (outdir / f"{model.replace(':', '-')}_{family}.json").write_text(json.dumps(prof, indent=1))
        with (outdir / f"{model.replace(':', '-')}_{family}.pkl").open("wb") as fh:
            pickle.dump(vm, fh)
        print(family, "base", round(prof["base"], 3), {k: round(v["value"], 3) for k, v in prof["mcv"].items()})


def _load_profile(model: str, family: str, value_model_from: str | None = None):
    """Type-level profile of ``model``; the instance-level block-value model comes from ``value_model_from`` when given
    (shared between native and transferred conditions so that transfer tests isolate the type-level profile)."""
    stem = PROC / "profiles" / f"{model.replace(':', '-')}_{family}"
    prof = json.loads(stem.with_suffix(".json").read_text())
    vstem = PROC / "profiles" / f"{(value_model_from or model).replace(':', '-')}_{family}"
    with vstem.with_suffix(".pkl").open("rb") as fh:
        vm = pickle.load(fh)
    return prof, vm


def evaluate(model: str, family: str, policies: list, budgets: list, profile_model: str | None, limit: int | None,
             run_name: str, seed: int = 0, variants: bool = True, deps: bool = True, split: str = "test",
             offset: int = 0, value_model_from: str | None = None) -> None:
    run = RAW / run_name
    _manifest(run, {"cmd": "eval", "model": model, "family": family, "policies": policies, "budgets": budgets,
                    "profile_model": profile_model, "value_model_from": value_model_from, "limit": limit, "variants": variants, "deps": deps, "split": split})
    out = run / "episodes.jsonl"
    done = _done(out, lambda r: (r["iid"], r["policy"], r["budget"], r["seed"]))
    counter = TokenCounter(model)
    cache = Cache(ROOT / "results/cache/responses.sqlite")
    insts = load(split, family)[offset:]
    insts = insts[:limit] if limit else insts
    with httpx.Client() as http:
        ctx = {"embedder": Embedder(ROOT / "results/cache/embeddings.sqlite", http), "variants": variants, "deps": deps}
        if profile_model:
            ctx["profile"], ctx["value_model"] = _load_profile(profile_model, family, value_model_from)
        for inst in insts:  # interleave policies and budgets within each instance
            for budget in budgets:
                for pol in policies:
                    b = UNBOUNDED if pol == "B0" else budget
                    if pol == "B0" and budget != budgets[0]:
                        continue
                    if (inst.iid, pol, b, seed) in done:
                        continue
                    t0 = time.perf_counter()
                    try:
                        plan = POLICIES[pol](inst, counter, b, ctx)
                    except BudgetError as e:
                        rec = {"iid": inst.iid, "policy": pol, "budget": b, "seed": seed, "status": "budget_error",
                               "error": str(e)}
                        with out.open("a") as f:
                            f.write(json.dumps(rec) + "\n")
                        continue
                    plan_s = time.perf_counter() - t0
                    prompt = prompt_for(inst, plan)
                    r = call(http, model, seed, prompt, cache)
                    ans = extract_answer(inst.checker, r["text"])
                    rec = {"run": run_name, "iid": inst.iid, "family": family, "model": model, "seed": seed,
                           "policy": pol, "budget": b, "profile_model": profile_model,
                           "value_model_from": value_model_from, "status": "ok",
                           "success": success(inst.checker, ans, inst.gold), "answer": ans, "reply": r["text"][-600:],
                           "selection": plan.selection, "plan_tokens": plan.tokens,
                           "prompt_tokens_measured": counter.count(prompt), "ollama_prompt_tokens": r["prompt_tokens"],
                           "plan_seconds": plan_s, "llm_seconds": r["seconds"], "cached": r["cached"],
                           "cache_key": r["key"], "certificate": {k: v for k, v in plan.certificate.items()
                                                                  if k != "prompt_override"},
                           "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
                    with out.open("a") as f:
                        f.write(json.dumps(rec) + "\n")


def main() -> None:
    if "--smoke" in sys.argv:
        profile("qwen3:4b-instruct", "facts", limit=2, pad=False)
        fit("qwen3:4b-instruct")
        evaluate("qwen3:4b-instruct", "facts", ["B1", "B5", "OURS"], [1000], "qwen3:4b-instruct", limit=2, run_name="smoke", split="dev")
        print("smoke ok")
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["profile", "fit", "eval"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--family")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--pad", action="store_true")
    ap.add_argument("--policies", default="B0,B1,B2,B3,B4,B5,OURS-A,OURS")
    ap.add_argument("--budgets", default="1000,2000,4000,8000")
    ap.add_argument("--profile-model")
    ap.add_argument("--run")
    ap.add_argument("--split", default="test")
    ap.add_argument("--no-variants", action="store_true")
    ap.add_argument("--no-deps", action="store_true")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--value-model-from")
    ap.add_argument("--lobo", type=int, default=6, help="leave-one-block-out samples per instance (0 = type level only)")
    a = ap.parse_args()
    if a.cmd == "profile":
        profile(a.model, a.family, a.limit, a.pad, lobo=a.lobo)
    elif a.cmd == "fit":
        fit(a.model)
    else:
        evaluate(a.model, a.family, a.policies.split(","), [int(x) for x in a.budgets.split(",")], a.profile_model,
                 a.limit, a.run or f"eval_{a.model.replace(':', '-')}", variants=not a.no_variants,
                 deps=not a.no_deps, split=a.split, offset=a.offset, value_model_from=a.value_model_from)


if __name__ == "__main__":
    main()
