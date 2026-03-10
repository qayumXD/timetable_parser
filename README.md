# Timetable Parser

Parse COMSATS Vehari centralized timetable PDFs (student and faculty) into CSV and SQLite.

## Features

- Parses student and faculty timetable PDFs.
- Supports multi-page PDFs.
- Writes parsed records to:
	- SQLite database (`timetable.db`)
	- Timestamped CSV files in `output/`
- Optional AI fallback for uncertain cells.
- Minimal web UI for upload, parse, preview, and download.

## Setup

```bash
pip install -r requirements.txt
```

## CLI Usage

### Parse a PDF (all pages)

```bash
python scripts/run_parser.py data/raw/CTsp26.pdf
```

### Parse only first N pages

Useful for quick testing:

```bash
python scripts/run_parser.py data/raw/CTsp26.pdf 3
```

### Parse a faculty timetable PDF

```bash
python scripts/run_parser.py data/raw/FacultyCS.pdf
```

### Inspect PDF extraction (debug)

```bash
python scripts/inspect_pdf.py data/raw/CTsp26.pdf
```

### Run tests

```bash
python -m pytest tests/ -v
```

## Web UI Usage

### Start the UI

```bash
python scripts/run_web.py
```

Open in browser:

- `http://localhost:8000`

### In the UI

- Upload a `.pdf` file.
- Optionally set `max_pages`.
- Click **Run Parser**.
- View parser run logs.
- Preview generated CSV rows.
- Download CSV files from the output table.

## Outputs

- Database: `timetable.db`
- CSV files: `output/*.csv`
- Web uploads: `data/raw/web_uploads/`

## Key Scripts

- `scripts/run_parser.py` -> Main parser CLI
- `scripts/run_web.py` -> Start web interface
- `scripts/inspect_pdf.py` -> Debug PDF extraction
