# Environment

## Machine

- macOS: 26.6.2 (25G83)
- CPU: Apple M4, arch arm64
- RAM: 24 GiB
- Free disk (home): 210Gi

## Tools

- Python: 3.12.14 (uv 0.12.3 (Homebrew 2026-08-07 aarch64-apple-darwin))
- Ollama: ollama version is 0.35.0
- LaTeX: pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026)
- Docker: Docker version 29.5.3, build d1c06ef

## Python packages

- absl-py==2.5.0
- accelerate==1.15.0
- aiohappyeyeballs==2.7.1
- aiohttp==3.14.3
- aiosignal==1.4.0
- annotated-doc==0.0.5
- annotated-types==0.8.0
- anyio==4.15.1
- attrs==26.1.0
- certifi==2026.7.22
- charset-normalizer==3.5.2
- click==8.5.0
- cloudpickle==3.1.2
- contourpy==1.4.0
- coverage==7.16.2
- cycler==0.12.1
- datasets==5.0.1
- defusedxml==0.7.1
- dill==0.4.1
- filelock==4.0.9
- fonttools==4.66.1
- frozenlist==1.8.0
- fsspec==2026.6.0
- h11==0.16.0
- hf-xet==1.6.0
- httpcore==1.0.9
- httpx==0.28.1
- huggingface_hub==1.33.0
- idna==3.20
- immutabledict==4.3.1
- iniconfig==2.3.0
- Jinja2==3.1.6
- joblib==1.6.0
- jsonschema==4.26.0
- jsonschema-specifications==2025.9.1
- kiwisolver==1.5.1
- llmlingua==0.2.2
- markdown-it-py==4.2.0
- MarkupSafe==3.0.3
- matplotlib==3.11.2
- mcv==0.0.1
- mdurl==0.1.2
- mpmath==1.3.0
- multidict==6.9.1
- multiprocess==0.70.19
- narwhals==2.26.0
- networkx==3.7
- nltk==3.10.3
- numpy==2.5.3
- ortools==9.15.6755
- packaging==26.3
- pandas==3.0.6
- pillow==12.3.0
- pluggy==1.6.0
- propcache==0.5.4
- protobuf==6.33.6
- psutil==7.2.2
- pyarrow==25.0.1
- pydantic==2.13.5
- pydantic_core==2.46.5
- Pygments==2.21.0
- pyparsing==3.3.3
- pypdf==6.19.0
- pytest==9.1.1
- pytest-cov==7.1.0
- python-dateutil==2.9.0.post0
- PyYAML==6.0.3
- referencing==0.37.0
- regex==2026.9.29
- requests==2.34.2
- rich==15.0.0
- rpds-py==2026.6.3
- ruff==0.16.10
- safetensors==0.8.0
- scikit-learn==1.9.1
- scipy==1.18.1
- setuptools==84.0.0
- shellingham==1.5.4
- six==1.17.0
- sympy==1.14.0
- threadpoolctl==3.7.0
- tiktoken==0.14.0
- tokenizers==0.23.2
- torch==2.14.1
- tqdm==4.70.1
- transformers==5.18.0
- typer==0.27.2
- typing-inspection==0.4.4
- typing_extensions==4.16.0
- urllib3==2.8.0
- xxhash==4.0.1
- yarl==1.25.1

## Models (Ollama)

| tag | family | params | quant | digest |
|---|---|---|---|---|
| FILL-IN after Phase 0 tool-calling probe (>=3 models, >=2 families, fit in 24 GB at 4-bit) | NOT INSTALLED | | | |

Decoding: temperature 0 and a fixed `seed` per run. Ollama/llama.cpp on Metal is not guaranteed to be
bit-deterministic even with a fixed seed; variance across seeds is reported, never hidden.
