# arXiv submission: step by step (free; you submit; nothing is sent by the build)

## Files (in `dist/`)
- `context-that-pays-arxiv.tar.gz`: the source package to upload (compiles on its own; includes figures, .bbl, class files).
- `context-that-pays.pdf`: the reference PDF, for checking that arXiv's build looks the same.
- `abstract.txt`: plain-text abstract (macros expanded, under 1,920 characters) to paste into the form.

## Before you start
1. Create or log in to an arXiv account at https://arxiv.org/user/ (free). Use your real name, and add your
   affiliation as "Independent Researcher".
2. **Endorsement:** if this is your first submission to the cs archive, arXiv may ask for an endorsement. The form
   tells you; follow its instructions to request one from an established cs author (for example someone you have
   worked with). Never pay anyone for an endorsement.
3. **Recommended: make the artifact public first.** The paper says code, data adapters and logs "will be released
   with the preprint". Create a free public GitHub repository from this folder, then add its URL to the conclusion's
   "Artifact availability" line and rebuild (`make paper && make arxiv`). Exclude `results/cache/` (large) and check
   that `data/raw` contains only redistributable files (HotpotQA is CC BY-SA 4.0 and BFCL is Apache-2.0, both
   redistributable with attribution).

## Submission form
| Field | Value |
|---|---|
| Upload | `dist/context-that-pays-arxiv.tar.gz` (choose "TeX source") |
| Title | Context That Pays? Why Measured Context Value Failed to Beat Cosine Similarity in a Pre-Registered Test |
| Authors | Venkata Sangaraju |
| Abstract | contents of `dist/abstract.txt` |
| Comments | 12 pages, 7 figures, 6 tables. Pre-registered; primary hypothesis not supported; pre-specified post-hoc follow-up included. Code and logs: <your repo URL> |
| Primary category | cs.CL (Computation and Language) |
| Cross-lists | cs.AI, cs.LG |
| License | CC BY 4.0 (most open; maximizes reuse and citation) |
| MSC/ACM classes | leave empty |

Check the arXiv-generated PDF preview against `dist/context-that-pays.pdf`, then submit. Announcements go out
Sunday to Thursday evenings (US Eastern). A submission made on the weekend appears with the Monday-evening announcement.

## After posting
- Add the arXiv ID to the README and to the GitHub repository description.
- Google Scholar indexes arXiv automatically, usually within days to a few weeks.
