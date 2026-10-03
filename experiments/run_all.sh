#!/bin/sh
# Test-split runs as pre-registered in PLAN.md (fast plan). Sequential Ollama (OLLAMA_NUM_PARALLEL=1).
set -e
cd "$(dirname "$0")/../code"
R="uv run python -m mcv.run"
# 1) 8B type-level profile (dev 1-20) + fit, padding control (4B, dev 1-20)
for fam in facts history tool; do $R profile --model qwen3:8b --family $fam --limit 20 --lobo 0; done
$R fit --model qwen3:8b || true
for fam in facts history tool; do $R profile --model qwen3:4b-instruct --family $fam --limit 20 --pad; done
# 2) main 4B grid: competitive policies on n=100 per family
for fam in facts history tool; do
  $R eval --model qwen3:4b-instruct --family $fam --limit 100 --profile-model qwen3:4b-instruct \
     --policies B0,B2,B4,OURS-A,OURS --run main_4b
done
# 3) weak baselines on n=30 per family
for fam in facts history tool; do
  $R eval --model qwen3:4b-instruct --family $fam --limit 30 --policies B1,B3,B5 --run main_4b_weak
done
# 4) transfer on 8B: n=40 per family, budgets 2000,8000
for fam in facts history tool; do
  $R eval --model qwen3:8b --family $fam --limit 40 --budgets 2000,8000 --policies B2 --run transfer_8b
  $R eval --model qwen3:8b --family $fam --limit 40 --budgets 2000,8000 --policies OURS --profile-model qwen3:4b-instruct --run transfer_8b_t
  $R eval --model qwen3:8b --family $fam --limit 40 --budgets 2000,8000 --policies OURS --profile-model qwen3:8b --value-model-from qwen3:4b-instruct --run transfer_8b_native
done
echo ALL_RUNS_DONE
