# Verification

- [x] instances.jsonl matches TEST.lock
- [x] addendum_calib: 660 rows, all on the dev split (0 violations)
- [x] addendum_calib: expected 660 rows, got 660; statuses {'ok': 660}
- [x] addendum_calib: all 2 manifest commit(s) descend from the pre-registration commit 2691500
- [x] addendum_test: 2400 rows, all on the test split (0 violations)
- [x] addendum_test: expected 2400 rows, got 2400; statuses {'ok': 2400}
- [x] addendum_test: all 1 manifest commit(s) descend from the pre-registration commit 2691500
- [x] main_4b: 5100 rows, all on the test split (0 violations)
- [x] main_4b: expected 5100 rows, got 5100; statuses {'ok': 5100}
- [x] main_4b: all 1 manifest commit(s) descend from the pre-registration commit 4c6491b
- [x] main_4b_weak: 1080 rows, all on the test split (0 violations)
- [x] main_4b_weak: expected 1080 rows, got 1080; statuses {'ok': 1080}
- [x] main_4b_weak: all 1 manifest commit(s) descend from the pre-registration commit 4c6491b
- [x] pilot2_dev_4b: 1740 rows, all on the dev split (0 violations)
- [x] pilot3_dev_4b: 480 rows, all on the dev split (0 violations)
- [x] pilot_dev_4b: 1166 rows, all on the dev split (0 violations)
- [x] profile_qwen3-4b-instruct: 1580 rows, all on the dev split (0 violations)
- [x] profile_qwen3-8b: 360 rows, all on the dev split (0 violations)
- [x] transfer_8b: 240 rows, all on the test split (0 violations)
- [x] transfer_8b: expected 240 rows, got 240; statuses {'ok': 240}
- [x] transfer_8b: all 2 manifest commit(s) descend from the pre-registration commit 4c6491b
- [x] transfer_8b_native: 240 rows, all on the test split (0 violations)
- [x] transfer_8b_native: expected 240 rows, got 240; statuses {'ok': 240}
- [x] transfer_8b_native: all 3 manifest commit(s) descend from the pre-registration commit 4c6491b
- [x] transfer_8b_t: 240 rows, all on the test split (0 violations)
- [x] transfer_8b_t: expected 240 rows, got 240; statuses {'ok': 240}
- [x] transfer_8b_t: all 2 manifest commit(s) descend from the pre-registration commit 4c6491b
- [x] facts: success re-derived from the logged answer for 50 sampled episodes: 50/50 agree
  - answer re-extracted from the logged reply: 50/50 identical
- [x] history: success re-derived from the logged answer for 50 sampled episodes: 50/50 agree
  - answer re-extracted from the logged reply: 50/50 identical
- [x] tool: success re-derived from the logged answer for 50 sampled episodes: 50/50 agree
  - answer re-extracted from the logged reply: 50/50 identical
- [x] tokenizer (qwen3:4b-instruct): Ollama prompt count minus HF count equals 8 (chat-template overhead) in 8580/8580 episodes; range [8, 8]
- [x] tokenizer (qwen3:8b): Ollama prompt count minus HF count equals 16 (chat-template overhead) in 720/720 episodes; range [16, 16]
- [x] independent recomputation: RESULT: MATCH

RESULT: PASS
