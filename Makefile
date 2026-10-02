# Paper 03 — one-command reproduction. `make all` = env -> data -> experiments -> results -> verify -> figures
# -> numbers -> refs -> paper -> check. Targets marked (Phase n) are implemented by the build in that phase.
PY = cd code && uv run python
.PHONY: all smoke env test data experiments results verify figures numbers refs paper check clean-paper

all: env test data experiments results verify figures numbers refs paper check

env:            ## Phase 0
	$(PY) scripts/record_env.py

test:           ## Phase 2 (>= 85% coverage on core modules)
	$(PY) -m pytest -q --cov=mcv --cov-report=term-missing

data:           ## Phase 3: seeded generators/adapters -> data/processed (+ TEST.lock)
	$(PY) -m mcv.data.build

experiments:    ## Phase 4
	./experiments/run_all.sh

results:        ## Phase 5: process raw logs; independent recomputation must match exactly
	$(PY) scripts/process_results.py
	$(PY) scripts/recompute_metrics.py

verify:         ## Phase 5 gate
	$(PY) scripts/verify_results.py

figures:        ## Phase 6
	$(PY) scripts/make_figures.py

numbers:
	$(PY) scripts/export_paper_numbers.py

refs:           ## registry-built bib + verification (must PASS)
	$(PY) scripts/fetch_refs.py
	$(PY) scripts/verify_refs.py

paper:
	cd paper && pdflatex -interaction=nonstopmode main.tex >/dev/null; bibtex main >/dev/null; \
	  pdflatex -interaction=nonstopmode main.tex >/dev/null; pdflatex -interaction=nonstopmode main.tex >/dev/null; true

check:          ## 11-12 pages, no hand-typed numbers, no undefined refs
	$(PY) scripts/check_paper.py --min 11 --max 12

smoke:          ## 5-minute miniature of the full pipeline (implement in Phase 4)
	$(PY) -m mcv.run --smoke

clean-paper:
	cd paper && rm -f *.aux *.bbl *.blg *.log *.out *.fls *.fdb_latexmk
