#!/bin/sh
# Dev iteration (2026-10-02, before PLAN.md): add embedding-similarity feature to the block-value model, refit the 4B
# profile, re-run the dev pilot (baseline prompts are cache hits), then type-level profiles of 8B/12B and padding control.
set -e
cd "$(dirname "$0")/../code"
until grep -q PILOT_DONE ../logs/stage2.log; do sleep 30; done
pkill -f stage2.sh || true
pkill -f "mcv.run profile --model qwen3:8b" || true
sleep 5
uv run python -m mcv.run fit --model qwen3:4b-instruct
for fam in facts history tool; do
  uv run python -m mcv.run eval --model qwen3:4b-instruct --family $fam --split dev --offset 40 --limit 20 \
    --profile-model qwen3:4b-instruct --run pilot2_dev_4b
done
echo PILOT2_DONE
for m in qwen3:8b mistral-nemo:12b; do
  for fam in facts history tool; do
    uv run python -m mcv.run profile --model $m --family $fam --limit 20 --lobo 0
  done
  uv run python -m mcv.run fit --model $m || true
done
for fam in facts history tool; do
  uv run python -m mcv.run profile --model qwen3:4b-instruct --family $fam --limit 20 --pad
done
echo STAGE2B_DONE
