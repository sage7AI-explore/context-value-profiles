#!/usr/bin/env bash
# Runs every experiment config in experiments/configs/ (resumable: completed cells are skipped by the runner).
# Implement the runner as `python -m mcv.run --config <yaml>` in Phase 4.
set -euo pipefail
cd "$(dirname "$0")/.."
export OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1
shopt -s nullglob
cfgs=(experiments/configs/*.yaml)
if [ ${#cfgs[@]} -eq 0 ]; then echo "no configs yet (Phase 4)"; exit 1; fi
for cfg in "${cfgs[@]}"; do
  echo "== $cfg $(date -u +%FT%TZ)"; vm_stat | head -5 >> logs/memory.log || true
  (cd code && uv run python -m mcv.run --config "../$cfg") 2>&1 | tee -a "logs/$(basename "$cfg" .yaml).log"
done
