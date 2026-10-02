#!/bin/sh
# Dev-split profiling of the transfer-source model (40 dev instances per family). Sequential Ollama.
set -e
cd "$(dirname "$0")/../code"
for fam in facts history tool; do
  uv run python -m mcv.run profile --model qwen3:4b-instruct --family $fam --limit 40
done
uv run python -m mcv.run fit --model qwen3:4b-instruct
echo PROFILE_DONE
