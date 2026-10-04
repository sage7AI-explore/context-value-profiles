# Model builds used in the experiments

Recorded 2026-10-04 with `ollama show` (Ollama 0.35.0) on the machine that ran every experiment. Digests match those
written into each run manifest (`results/raw/*/manifest.jsonl`, field `model_digests`), so these are the exact builds
used.

| Ollama tag | Role | Architecture | Parameters | Quantization | Context length (model) | Digest (prefix) |
|---|---|---|---|---|---|---|
| `qwen3:4b-instruct` | main model, profiling source | qwen3 | 4.0B | Q4_K_M | 262,144 | 0edcdef34593 |
| `qwen3:8b` | transfer target | qwen3 | 8.2B | Q4_K_M | 40,960 | 500a1f067a9f |
| `nomic-embed-text` | embeddings (relevance, features) | nomic-bert | 137M | F16 | 2,048 | 0a109f422b47 |

The Qwen models are Ollama's default 4-bit (Q4_K_M) builds. All runs used a 16,384-token window (`num_ctx`), greedy
decoding (temperature 0), seed 0, at most 96 output tokens, and thinking disabled. The 262,144-token native context of
the `qwen3:4b-instruct` build is consistent with the Qwen3-4B-Instruct-2507 release.
