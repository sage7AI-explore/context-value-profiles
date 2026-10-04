# Paper 03 "Context That Pays": experiments and terms (plain-language summary)

## Key terms

### MCV: Marginal Context Value
How much a type of context actually helps the model succeed at a task. An agent's prompt contains several kinds of
context: tool descriptions, retrieved documents, worked examples, notes and conversation history. To measure the MCV of
one kind, for example worked examples:
1. Run the model on practice (development) tasks with everything included and record how often it succeeds.
2. Run the same tasks with all worked examples removed.
3. The drop in success rate is the MCV of worked examples.

Example (Qwen3-4B): removing all tool descriptions dropped success by **0.85**, from 85% to almost zero, so they are
essential. Removing worked examples changed success by **about 0**.

An **MCV profile** is the table of these values for one model and one task family, each with a confidence range. It
also records how much a shortened version of each type is worth, and whether two types overlap. History and a summary
note, for example, largely substitute for each other.

Main finding: MCV is **good for diagnosis** (which kinds of context are worth sending) but **not better at choosing
individual items** (which of 20 documents to include). Simple embedding relevance did that as well or better.

### AUBC: Area Under the Budget Curve
A single score for how well a context-selection method does across all token budgets. Each method was tested at four
prompt-size limits (1,000, 2,000, 4,000 and 8,000 tokens), giving a curve of success rate against budget. AUBC is the
area under that curve, scaled to 0–1. The budget axis is logarithmic, so each doubling counts equally. A method that
stays accurate at small budgets scores higher.

Example: on history recall, relevance ranking scored **0.990** and MCV **0.937**. Both were near-perfect at 2k tokens
and above; MCV lost at 1k, where it more often dropped the session that held the answer.

## Held fixed in every experiment
- The same model settings: temperature 0, fixed seed, thinking off.
- A fixed prompt layout: instructions → tool schemas → examples → documents → notes → history → goal.
- The instructions and the goal (the question) are in every prompt.

## Table 1: Experiments run
| # | Experiment | Model | Data | Episodes | What changes from prompt to prompt | Purpose / result |
|---|---|---|---|---|---|---|
| 1 | Profiling (MCV measurement) | Qwen3-4B | 40 dev instances per family | 1,440 | Full context, then one type removed, two types removed, one type shortened, or one single block removed | Builds the MCV profile. Tool schemas 0.85, documents 0.35, examples about 0. |
| 2 | Length control | Qwen3-4B | 20 dev per family | 140 | A removed type is replaced with filler text of about equal length | Checks that value comes from content, not prompt length. It does. |
| 3 | 8B profiling | Qwen3-8B | 20 dev per family | 360 | Same as #1, type removals only | Compared with the 4B profile: ρ = 0.88 |
| 4 | Dev pilots v1–v3 | Qwen3-4B | dev 41–60 | 3,386 | Three versions of the block-ranking model | Chose v2 (0.758) over v3 (0.736) before any test run |
| 5 | Main study (H1, H1b, H2) | Qwen3-4B | 100 test per family | 5,100 | Five methods (B0, B2, B4, OURS-A, OURS) at 1k/2k/4k/8k token budgets | **H1 failed:** no win over relevance. H1b held in 2/3 families; H2 showed no effect. |
| 6 | Weaker baselines | Qwen3-4B | 30 test per family | 1,080 | B1, B3, B5 at 4 budgets | All scored below relevance (B2) |
| 7 | Transfer (H3) | Qwen3-8B | 40 test per family | 720 | B2; MCV with the 4B profile; MCV with the 8B profile; at 2k and 8k | Identical outcomes in 100% of pairs |
| 8 | Follow-up calibration | Qwen3-4B | dev 41–60 | 660 | Five similarity thresholds for the stop rule | Picked one threshold per family |
| 9 | Follow-up test (H6–H8) | Qwen3-4B | 100 test per family | 2,400 | B2S and HYB at 4 budgets | The hybrid won in 0/3 families. Relevance plus a stop rule cut 83% of tokens on tool use. |

## Table 2: What each method puts in the prompt
| Method | Rule for choosing what goes in the prompt | Example: tool task, 8k budget |
|---|---|---|
| B0 Full context | Everything, ignoring the budget | All 30 tool schemas and examples (about 4,240 tokens) |
| B1 Truncate oldest | Keep the most recent blocks that fit; drop the oldest | Whatever fits from the end |
| B2 Relevance | Rank blocks by embedding similarity to the question and fill the budget | Same as B0 at 8k: it keeps filling until everything is in |
| B3 LLMLingua-2 | Compress all context by deleting tokens until it fits | Shorter text, with names corrupted (`calculate_future_value` → `calculate future value`) |
| B4 Coverage (PACMS-style) | Choose a diverse set of blocks that covers the question | Mix of related tools |
| B5 Type tiers | Fixed priority order: tools, then documents, then examples, then notes, then history | Tools first |
| OURS-A (MCV, additive) | Compiler picks blocks with the highest predicted value; stops when no block adds value | About 2,760 tokens: drops low-value tools and most examples |
| OURS (MCV + interactions) | OURS-A plus type-pair interaction terms | Nearly the same, with a different choice in 22–50% of plans |
| OURS-T / OURS-native (8B) | OURS using the 4B profile / using the 8B profile | Different selections in 65% of episodes, identical outcomes |
| B2S (relevance + stop rule) | B2, but skip blocks below a similarity threshold | About 705 tokens: only the most relevant tools |
| HYB (hybrid) | Only types the profile marks valuable; relevance ranks within them; threshold; compiler | About 609 tokens: tools only, no examples |

**In short:** B0–B5 differ in *how they rank and fill*. MCV differs in *what it values and when it stops*. The
follow-up showed that the "when to stop" part (B2S), not MCV's measured values, accounts for the token savings.

Source of all numbers: `results/processed/` (generated from the logs in `results/raw/`); full details in the paper.

## Relevance and the stop rule (method B2S)

### Relevance
Rank every piece of context by how similar it is to the question, most similar first.
1. An embedding model (nomic-embed-text, run locally) turns the question and each piece of context into vectors that
   capture meaning.
2. Each piece gets a cosine-similarity score: roughly 0 for unrelated text, closer to 1 for closely related text.
3. Pieces are sorted by score and the prompt is filled in that order until the token budget runs out.

Example: for "Calculate the future value of my $1,000 investment at 5% over 2 years", `calculate_future_value` scores
high, `calculate_compound_interest` fairly high, and `identify_bird` low. This is baseline **B2**, the strongest method
in the study. Its weakness is that it never stops while there's room: at 8k it adds everything.

### Stop rule
Don't add a piece whose similarity is below a threshold, even if there's still room in the budget. With a threshold of
0.585, every piece scoring below 0.585 is left out however much space remains. The threshold is set per task family on
development data only (see below). Chosen: **facts 0.606, history 0.541, tool 0.585**.

### Relevance + stop rule (B2S) vs the others: tool task at 8k
| | Relevance only (B2) | Relevance + stop rule (B2S) | MCV |
|---|---|---|---|
| Tokens sent | about 4,240 (everything) | **about 705** | about 2,760 |
| Success | 90% | **92%** | 91% |

On tool use, B2S cut **83%** of tokens with no loss in success, against 35% for MCV. On facts and history the thresholds
chosen on development data were too aggressive and cost about 6 points of success. Main takeaway: MCV's token savings
come from knowing *when to stop*, not from MCV's measured values.

## How the thresholds were chosen
The procedure was fixed in the pre-registration addendum (`PLAN.md`, Addendum A) and committed before any of these
runs. It used development data only.

**Step 1: candidate thresholds.** For each family, compute the question-to-block similarity for every optional block in
the 40 development instances used for profiling. The candidates are "no stop" (−1, keep everything) plus the 30th, 50th,
70th and 85th percentiles of those similarities. A higher threshold drops more.

| Family | Candidate thresholds |
|---|---|
| Facts | no stop, 0.474, 0.546, 0.606, 0.656 |
| History | no stop, 0.520, 0.541, 0.562, 0.582 |
| Tool | no stop, 0.501, 0.526, 0.554, 0.585 |

**Step 2: try each candidate** at the 8k budget on 20 other development instances per family, never used for profiling
or testing. Record success and tokens sent.

**Step 3: apply the rule written down before the runs.** Choose the threshold that sends the fewest tokens while keeping
success within 5 points of full context; if two tie, take the smaller threshold.

| Family | Threshold | Success | Tokens | Within 5 pts of full context? |
|---|---|---|---|---|
| **Facts** (full context: 45%) | no stop | 45% | 3,059 | ✅ |
| | 0.474 | 40% | 1,925 | ✅ |
| | 0.546 | 35% | 1,213 | ❌ |
| | **0.606 ← chosen** | **40%** | **760** | ✅ |
| | 0.656 | 35% | 337 | ❌ |
| **History** (full: 100%) | no stop | 100% | 2,724 | ✅ |
| | 0.520 | 95% | 1,874 | ✅ |
| | **0.541 ← chosen** | **95%** | **1,346** | ✅ |
| | 0.562 | 85% | 830 | ❌ |
| | 0.582 | 75% | 489 | ❌ |
| **Tool** (full: 90%) | no stop | 90% | 4,271 | ✅ |
| | 0.501 | 95% | 2,929 | ✅ |
| | 0.526 | 95% | 2,013 | ✅ |
| | 0.554 | 90% | 1,191 | ✅ |
| | **0.585 ← chosen** | **90%** | **619** | ✅ |

(Source: `results/processed/calibration_table.csv`, `results/processed/tau_grid.json`.)

### What happened on the test set
- **Tool:** the choice held. On 100 test tasks it removed 83% of tokens and matched full-context success.
- **Facts and history:** the chosen thresholds were too aggressive, and success fell about 6 points.

Two weaknesses explain the misses:
1. **20 instances is a small sample.** One more or one fewer correct answer moves success by 5 points, exactly the size
   of the tolerance.
2. **The facts curve isn't monotonic.** 0.546 scored worse (35%) than the stricter 0.606 (40%), a sign of noise; the
   rule picked 0.606 partly by luck of the sample.

The paper reports both openly and lists "calibrate thresholds on a larger development set" as the top experiment still
worth running.
