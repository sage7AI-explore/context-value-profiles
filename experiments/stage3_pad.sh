#!/bin/sh
# Length-neutral padding control on 20 dev instances per family (4B). Unchanged conditions are cache hits.
set -e
cd "$(dirname "$0")/../code"
until grep -q STAGE2_DONE ../logs/stage2.log; do sleep 60; done
for fam in facts history tool; do
  uv run python -m mcv.run profile --model qwen3:4b-instruct --family $fam --limit 20 --pad
done
echo PAD_DONE
