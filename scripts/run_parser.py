#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.pdf_extractor import extract_raw_table, extract_metadata
from src.parser.grid_parser import parse_grid
from src.parser.normalizer import normalize
from src.db.database import init_db, insert_schedule_records


def main(pdf_path: str):
    print(f"[1/5] Opening PDF: {pdf_path}")
    raw_table = extract_raw_table(pdf_path)
    metadata = extract_metadata(pdf_path)

    print("[2/5] Parsing grid structure...")
    grid = parse_grid(raw_table)

    print("[3/5] Parsing cell contents...")

    print("[4/5] Normalizing records...")
    records = normalize(grid, metadata)
    print(f"      -> {len(records)} schedule records extracted")

    print("[5/5] Saving to database...")
    init_db()
    insert_schedule_records(records)
    print("Done. Database updated.")

    print("\n--- Summary ---")
    for r in records:
        print(f"  {r.day:12} Slot {r.slot} | {r.subject:35} | {r.room_code:12} | {r.instructor_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_parser.py <path/to/timetable.pdf>")
        sys.exit(1)
    main(sys.argv[1])
