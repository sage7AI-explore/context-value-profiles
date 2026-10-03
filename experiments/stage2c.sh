#!/bin/sh
# Final dev iteration (2026-10-02): MCV apportioned across blocks of a type. Pilot 3 (MCV policies only; baselines are
# unchanged and come from pilot2), then resume 8B/12B type-level profiles and the padding control.
set -e
cd "$(dirname "$0")/../code"
for fam in facts history tool; do
  uv run python -m mcv.run eval --model qwen3:4b-instruct --family $fam --split dev --offset 40 --limit 20 \
    --profile-model qwen3:4b-instruct --policies OURS-A,OURS --run pilot3_dev_4b
done
echo PILOT3_DONE
for m in qwen3:8b mistral-nemo:12b; do
  for fam in facts history tool; do
    uv run python -m mcv.run profile --model $m --family $fam --limit 20 --lobo 0
  done
  uv run python -m mcv.run fit --model $m || true
done
for fam in facts history tool; do
  uv run python -m mcv.run profile --model qwen3:4b-instruct --family $fam --limit 20 --pad
done
echo STAGE2C_DONE
