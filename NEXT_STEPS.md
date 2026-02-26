Next steps to use the AI cell parser pipeline
- Install deps: `pip install -r requirements.txt`
- Download model (one-time): `python scripts/download_model.py`
- Run fast tests (no model needed): `python -m pytest -m "not slow" -v`
- Run full suite after model download: `python -m pytest -v`
- Parse a PDF (example): `python scripts/run_parser.py data/raw/CTfa24.pdf`
