#!/bin/sh
# Stage 2 (after 4B profiling): dev pilot on held-out dev instances (offset 40), then type-level profiles of 8B/12B.
set -e
cd "$(dirname "$0")/../code"
until grep -q PROFILE_DONE ../logs/profile_4b.log; do sleep 60; done
for fam in facts history tool; do
  uv run python -m mcv.run eval --model qwen3:4b-instruct --family $fam --split dev --offset 40 --limit 20 \
    --profile-model qwen3:4b-instruct --run pilot_dev_4b
done
echo PILOT_DONE
for m in qwen3:8b mistral-nemo:12b; do
  for fam in facts history tool; do
    uv run python -m mcv.run profile --model $m --family $fam --limit 20 --lobo 0
  done
done
uv run python -m mcv.run fit --model qwen3:8b || true
uv run python -m mcv.run fit --model mistral-nemo:12b || true
echo STAGE2_DONE
