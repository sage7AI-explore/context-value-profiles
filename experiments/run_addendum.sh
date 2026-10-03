#!/usr/bin/env bash
# Addendum A (PLAN.md): dev calibration of tau, then test runs of calibrated B2S and HYB. Unattended.
set -euo pipefail
cd "$(dirname "$0")/../code"
R="uv run python -m mcv.run"
M=qwen3:4b-instruct
for fam in facts history tool; do
  G=$(python3 -c "import json;print(','.join(f'B2S@{t},HYB@{t}' for t in json.load(open('../results/processed/tau_grid.json'))['$fam']))")
  $R eval --model $M --family $fam --split dev --offset 40 --limit 20 --budgets 8000 --policies B0,$G \
     --profile-model $M --run addendum_calib
done
uv run python scripts/calibrate_tau.py
for fam in facts history tool; do
  P=$(python3 -c "import json;c=json.load(open('../results/processed/calibration.json'))['$fam'];print(f\"B2S@{c['B2S']},HYB@{c['HYB']}\")")
  $R eval --model $M --family $fam --limit 100 --policies $P --profile-model $M --run addendum_test
done
echo ADDENDUM_DONE
