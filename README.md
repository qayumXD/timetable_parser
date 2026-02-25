# Timetable Parser

Parse COMSATS Vehari centralized timetable PDFs into a normalized SQLite database.

## What it does

- Extracts the timetable grid from a single-page PDF using `pdfplumber`.
- Normalizes cell contents into structured records (subject, instructor, room, slot).
- Handles two-hour classes that span the break.
- Persists data into SQLite with a normalized schema.

## Project layout

- `scripts/run_parser.py`: CLI entrypoint to parse a PDF and load the DB.
- `scripts/inspect_pdf.py`: Debug tool to inspect raw PDF extraction.
- `src/parser/`: PDF extraction, grid parsing, cell parsing, normalization.
- `src/db/`: SQLite schema and persistence helpers.
- `src/location/`: Room location resolver (seeded from `data/room_locations.json`).
- `tests/`: Unit tests for each parser stage.

## Quick start

```bash
pip install -r requirements.txt
python scripts/run_parser.py data/raw/BCS-SP24-5C.pdf
```

## Inspect a PDF (debug)

```bash
python scripts/inspect_pdf.py data/raw/BCS-SP24-5C.pdf
```

## Run tests

```bash
python -m pytest tests/ -v
```

## Output

- Database file: `timetable.db`
- Room locations seed data: `data/room_locations.json`
