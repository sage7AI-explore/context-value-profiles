# Paper 03 — one-command reproduction. `make all` = env -> data -> experiments -> results -> verify -> figures
# -> numbers -> refs -> paper -> check. Targets marked (Phase n) are implemented by the build in that phase.
PY = cd code && uv run python
.PHONY: all smoke env test data experiments results verify figures numbers refs paper check clean-paper

all: env test data experiments results verify figures numbers refs paper check

env:            ## Phase 0
	$(PY) scripts/record_env.py

test:           ## Phase 2 (>= 85% coverage on core modules)
	$(PY) -m pytest -q --cov=mcv --cov-report=term-missing --cov-report=json:../results/processed/coverage.json --junitxml=../results/processed/tests.xml

data:           ## Phase 3: seeded generators/adapters -> data/processed (+ TEST.lock)
	$(PY) -m mcv.data.build

experiments:    ## Phase 4
	./experiments/run_all.sh
	./experiments/run_addendum.sh

results:        ## Phase 5: process raw logs; independent recomputation must match exactly
	$(PY) scripts/process_results.py
	$(PY) scripts/analyze_extra.py
	$(PY) scripts/analyze_profiles.py
	$(PY) scripts/sensitivity_checker.py
	$(PY) scripts/analyze_addendum.py
	$(PY) scripts/recompute_metrics.py

verify:         ## Phase 5 gate
	$(PY) scripts/verify_results.py

figures:        ## Phase 6
	$(PY) scripts/make_figures.py
	$(PY) scripts/make_excerpts.py
	$(PY) scripts/make_tables.py

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

arxiv:          ## self-contained arXiv source package in dist/ (run after `make paper`)
	$(PY) scripts/make_arxiv.py
