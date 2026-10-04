# Commit map (history rewrite, 2026-10-04)

Before publishing, the history was rewritten to remove two private planning files (an AI build prompt and an idea
note) and two README lines referring to them. Nothing else changed: every commit keeps its content, message, author and
date, so the pre-registration timestamps stand. Commit hashes changed, while the experiment manifests in `results/raw/`
were left untouched and still record the original hashes. This table maps them; `code/scripts/verify_results.py`
uses it to check that every test run descends from the pre-registration commit.

## Files removed by the rewrite, and references to them
- `PROMPT.md`: the private project brief used to set up and run this study (task description, rules, required
  checks). `PLAN.md` (the pre-registration, deliberately left unedited) says that H1 is "as specified in PROMPT.md". The
  full hypothesis it refers to, H1, is stated in `PLAN.md` itself under "Hypotheses", so nothing needed to evaluate the
  pre-registration is missing.
- `IDEA.md`: the private idea note with an internal novelty assessment; the public novelty analysis is in
  `refs/NOVELTY.md` and `refs/NOVELTY_AUDIT.md` (which also mentions `IDEA.md` as one of its inputs).

| original | rewritten | committed | message |
|---|---|---|---|
| `4ebcad3bc493` | `e47447cc5582` | 2026-10-02T10:56:28-05:00 | Scaffold as provided (Paper 03: MCV profiles) |
| `64451b5a5b0d` | `64d35fa1c251` | 2026-10-02T11:41:17-05:00 | Phase 1: literature (194 candidates), NOVELTY.md, independent NOVELTY_AUDIT (proceed with  |
| `26ef1cbcec5c` | `ec7bd5193ddb` | 2026-10-02T12:37:23-05:00 | NOVELTY: add audit-flagged works (abstracts read), repositioning decision |
| `8c2972001108` | `540311fdf9f1` | 2026-10-02T15:54:35-05:00 | Phase 2: mcv system (IR, render, ablation profiler, estimator, features, transfer, CP-SAT  | **(in run manifests)**
| `b3b25d53e92a` | `66b5c3f60b70` | 2026-10-02T16:01:13-05:00 | Profiling script (dev, 4B) |
| `421380e6244b` | `1e0a3eb19c54` | 2026-10-02T16:04:16-05:00 | Refs: 42 entries, all with abstracts on file; eval --offset |
| `98969f3a4fbe` | `be7cfd04ec3d` | 2026-10-02T16:05:01-05:00 | Stage-2 script: dev pilot + type-level profiles for 8B/12B; profile --lobo |
| `055eba6ca124` | `7b718e3fbdbc` | 2026-10-02T16:06:38-05:00 | Paper: related, problem, design sections; shared value model for transfer; padding control |
| `42c967893b1e` | `06f32a345965` | 2026-10-02T16:10:13-05:00 | Paper: impl section; architecture figure | **(in run manifests)**
| `0b98ce0a6e07` | `61c55851221c` | 2026-10-02T19:39:58-05:00 | Dev iteration: embedding-similarity feature in block-value model; stage2b (refit, pilot2,  | **(in run manifests)**
| `9daf78b075dc` | `a17485019208` | 2026-10-02T20:06:46-05:00 | Log pilot crash (feature change mid-run); restart stage2b immediately | **(in run manifests)**
| `c0695011d41c` | `18f3d2ac5abd` | 2026-10-02T21:32:00-05:00 | Final dev iteration: apportion type MCV across blocks (softmax of standardized block-model | **(in run manifests)**
| `2bd6b3e396fb` | `7331ed25a86d` | 2026-10-02T23:54:07-05:00 | Freeze method: restore v2 block values (dev rule: higher mean dev AUBC, v2 0.758 vs v3 0.7 |
| `974e16baf38c` | `5faf7fb2da9f` | 2026-10-02T23:55:13-05:00 | PRE-REGISTRATION: PLAN.md (H1, H1b, H2, H3; power analysis; fast plan) + run_all.sh — comm | **(in run manifests)**
| `944b9210eb57` | `4c6491b42d00` | 2026-10-02T23:55:40-05:00 | PRE-REGISTRATION (actual content): PLAN.md — before any test-split run | **(in run manifests)**
| `5ac7e179aeb9` | `9e39402b3084` | 2026-10-03T10:37:45-05:00 | Analysis, figures, generated tables and full paper draft (transfer runs still in progress) | **(in run manifests)**
| `e45e989dec7b` | `7a079413aab2` | 2026-10-03T10:49:40-05:00 | Audit fixes: claims narrowed to logs; selection diagnostics; checker sensitivity; arXiv pa | **(in run manifests)**
| `baca0cfc5e4f` | `021ca94390b5` | 2026-10-03T13:13:25-05:00 | Transfer runs complete: H3 analysis, final numbers and figures |
| `72b816f3d498` | `249ca9415f5c` | 2026-10-03T14:58:15-05:00 | Reviewer fixes, HEADLINE/REVIEW, arXiv package and submission guide |
| `61aaacff6544` | `ba5eaf8ff971` | 2026-10-03T14:58:18-05:00 | Raw logs of all profiling, pilot, main and transfer runs |
| `6401964d6272` | `2691500a9f4d` | 2026-10-03T16:02:20-05:00 | PRE-REGISTRATION ADDENDUM A: relevance+stopping (B2S) and hybrid (HYB) policies, tau grid, | **(in run manifests)**
| `944baf9f7a06` | `bb67de07059b` | 2026-10-03T16:04:42-05:00 | Revision in progress: three-level framing, measured vs predicted value, narrowed novelty;  | **(in run manifests)**
| `bfe7f7e474cb` | `0fe31a46ca54` | 2026-10-03T17:37:55-05:00 | Option C: addendum runs (B2S, HYB), follow-up analysis, three-level reframing, rewritten a |
| `5fa4f6106092` | `57d8b8d11153` | 2026-10-03T21:39:30-05:00 | Reference verification: 42/42 PASS |
| `2e31df026ba2` | `a14d33e0fa0d` | 2026-10-03T21:44:09-05:00 | TMLR format: anonymous submission + preprint versions generated by tools/to_tmlr.py |
| `c38505895028` | `5fbaebb7a2b9` | 2026-10-03T22:06:59-05:00 | TMLR: appendix for secondary material (main text ~12.5 pp), broader impact statement; anon |
| `403a21fadbd8` | `77fcd56c57e8` | 2026-10-04T14:22:57-05:00 | Add co-author Sudhir Vissa (SAGE7 AI) to named versions; anonymous TMLR PDF unchanged |
| `f957214a7941` | `89010827576b` | 2026-10-04T17:55:59-05:00 | Plain-language experiments summary (terms, experiments, methods, threshold calibration) |
