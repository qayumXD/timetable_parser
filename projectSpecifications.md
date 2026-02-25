# 📅 University Timetable PDF Parser & Notification System
## Comprehensive Development Specification

> **Target:** COMSATS Vehari Centralized Timetable (Spring-2026)
> **Format:** Single-page grid PDF — consistent layout per batch (e.g. BCS-SP24-5C)
> **Stack:** Python · pdfplumber · SQLite · (future) notification backend

---

## 0. Project Overview

This system parses structured university timetable PDFs, stores the extracted schedule data in a normalized database, and will eventually notify students and instructors of their upcoming classes along with room/lab location context.

### Core Objectives

1. **Parse** — Reliably extract schedule data from the timetable PDF using `pdfplumber`
2. **Normalize** — Store structured records (subject, instructor, room, batch, timeslot, day)
3. **Resolve** — Map raw room codes (e.g. `CS LAB-3`) to human-readable physical locations
4. **Notify** — Alert students/instructors before a class begins (future phase)

---

## 1. Understanding the Source Document

Before writing a single line of code, the agent must understand the PDF structure intimately.

### 1.1 Grid Layout

```
Columns: Time Slots (1–6, plus a Break column)
  Slot 1: 8:30 – 10:00 AM
  Slot 2: 10:00 – 11:30 AM
  Slot 3: 11:30 AM – 1:00 PM
  Break:  1:00 – 1:30 PM  (no classes, skip)
  Slot 4: 1:30 – 3:00 PM
  Slot 5: 3:00 – 4:30 PM
  Slot 6: 4:30 – 6:00 PM

Rows: Days of the Week
  Monday, Tuesday, Wednesday, Thursday, Friday
```

### 1.2 Cell Content Structure

Each non-empty cell contains up to **3 lines** of text in this order:

```
Line 1: Subject Name          e.g. "Operating Systems-Lab"
Line 2: Room / Lab Code       e.g. "SE LAB-1"  or  "CS-3"  or  "MS LAB-5"
Line 3: Instructor Name       e.g. "Syed Ammar Yasir(CS)"
```

> ⚠️ **Important:** Room codes come in two flavors:
> - **Classroom codes**: `CS-2`, `CS-3`, `CS-4`, `MS-8` — these are regular lecture rooms
> - **Lab codes**: `SE LAB-1`, `CS LAB-3`, `MS LAB-5` — these are lab rooms

### 1.3 Multi-Slot (2-Hour) Classes

Some subjects span **two consecutive time slots**. They are marked with `(2Hrs)` in the subject name and their cell visually spans columns 3+Break or similar. The parser must detect and expand these into two records.

**Examples from the sample:**
- `Operating Systems(2Hrs)` — slots 3+Break (but treated as slot 3 through break)
- `Web Technologies(2Hrs)` — slots 3+Break
- `Mobile Application Development(2Hrs)` — slots 3+Break

### 1.4 Header Metadata

```
Title:     "COMSATS Vehari Centralized Timetable (V-2)-Spring-2026"
Batch:     "BCS-SP24-5C"  (top center, large font)
Semester:  "CS-5, CS-4, CS-3, CS-2"  (top right corner — indicates which semester rooms are used)
Date:      "COMSATS Centralized Timetable-16-Feb-2026"  (bottom left footer)
```

---

## 2. Project Structure

```
timetable-parser/
│
├── data/
│   ├── raw/                    # Input PDFs go here
│   │   └── BCS-SP24-5C.pdf
│   └── processed/              # Extracted JSON outputs
│       └── BCS-SP24-5C.json
│
├── src/
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py    # Phase 1: Raw text/table extraction via pdfplumber
│   │   ├── grid_parser.py      # Phase 2: Interpret grid structure, map rows/cols
│   │   ├── cell_parser.py      # Phase 3: Parse individual cell content
│   │   └── normalizer.py       # Phase 4: Clean, validate, expand 2hr classes
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.sql           # DDL for all tables
│   │   ├── database.py          # SQLite connection + CRUD helpers
│   │   └── seeder.py            # Seed location data for rooms
│   │
│   ├── location/
│   │   ├── __init__.py
│   │   └── resolver.py          # Map room codes → physical descriptions
│   │
│   └── notify/                  # Future phase — stub only for now
│       ├── __init__.py
│       └── scheduler.py
│
├── tests/
│   ├── test_pdf_extractor.py
│   ├── test_grid_parser.py
│   ├── test_cell_parser.py
│   └── test_normalizer.py
│
├── scripts/
│   ├── run_parser.py            # CLI entrypoint: parse PDF → DB
│   └── inspect_pdf.py           # Debug tool: dump raw pdfplumber output
│
├── requirements.txt
├── README.md
└── timetable.db                 # SQLite database (generated)
```

---

## 3. Development Phases

---

### Phase 1 — PDF Inspection & Raw Extraction

**File:** `src/parser/pdf_extractor.py`  
**Script:** `scripts/inspect_pdf.py`

#### Goal
Understand how `pdfplumber` sees the PDF before building logic around it. Run inspection first — do not assume structure.

#### Steps

**Step 1.1 — Install dependencies**
```bash
pip install pdfplumber
```

**Step 1.2 — Write `scripts/inspect_pdf.py`**

This script is a diagnostic tool only — NOT part of the final pipeline. It should:

```python
import pdfplumber
import json

def inspect(pdf_path: str):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        # 1. Print raw extracted text
        print("=== RAW TEXT ===")
        print(page.extract_text())

        # 2. Print all detected words with bounding boxes
        print("\n=== WORDS WITH BBOXES ===")
        for word in page.extract_words():
            print(word)  # {'text': ..., 'x0': ..., 'top': ..., 'x1': ..., 'bottom': ...}

        # 3. Try table extraction with default settings
        print("\n=== TABLE (default) ===")
        tables = page.extract_tables()
        for i, table in enumerate(tables):
            print(f"Table {i}:")
            for row in table:
                print(row)

        # 4. Try with explicit table settings
        settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        }
        print("\n=== TABLE (lines strategy) ===")
        tables = page.extract_tables(table_settings=settings)
        for i, table in enumerate(tables):
            print(f"Table {i}:")
            for row in table:
                print(row)

        # 5. Print detected lines/rects (for understanding grid structure)
        print("\n=== LINES ===")
        for line in page.lines:
            print(line)

        print("\n=== RECTS ===")
        for rect in page.rects:
            print(rect)
```

**Expected Outcome:**  
Determine which extraction strategy (`lines`, `text`, `explicit`) correctly identifies the grid. The timetable uses drawn lines for the grid, so `"vertical_strategy": "lines"` and `"horizontal_strategy": "lines"` is the most likely winner.

**Step 1.3 — Write `src/parser/pdf_extractor.py`**

```python
import pdfplumber
from typing import Optional

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "edge_min_length": 3,
    "min_words_vertical": 1,
    "min_words_horizontal": 1,
    "intersection_tolerance": 3,
}

def extract_raw_table(pdf_path: str, page_index: int = 0) -> list[list[Optional[str]]]:
    """
    Opens the PDF and extracts the raw 2D table from the specified page.
    Returns a list of rows, each row being a list of cell strings (or None).
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        tables = page.extract_tables(table_settings=TABLE_SETTINGS)
        if not tables:
            raise ValueError(f"No tables detected on page {page_index} of {pdf_path}")
        # The timetable is expected to be the largest table on the page
        return max(tables, key=lambda t: len(t) * len(t[0]))

def extract_metadata(pdf_path: str, page_index: int = 0) -> dict:
    """
    Extracts header metadata: batch name, timetable title, semester tags, date.
    Uses word-level bounding boxes since metadata is outside the grid.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        text = page.extract_text()
        # Metadata parsing is handled in normalizer.py
        return {"raw_header_text": text}
```

#### ✅ Phase 1 Done When:
- `inspect_pdf.py` successfully prints a non-empty 2D table that looks like the timetable grid
- `extract_raw_table()` returns a clean matrix without errors
- You can visually confirm rows = days, columns = time slots by printing the matrix

---

### Phase 2 — Grid Parser

**File:** `src/parser/grid_parser.py`

#### Goal
Map the raw 2D matrix from Phase 1 into a structured dictionary keyed by `(day, slot)`.

#### Context
The raw table from `pdfplumber` will look roughly like this (some cells may be `None` for empty):

```
Row 0: [None, "1\n8:30-10:00AM", "2\n10:00-11:30AM", "3\n11:30AM-1:00PM", "Break...", "4\n1:30-3:00PM", ...]
Row 1: ["Monday", "Operating Systems-Lab\nSE LAB-1\nSyed Ammar Yasir(CS)", "Computer Org...", None, None, "Design...", ...]
Row 2: ["Tuesday", ...]
...
```

#### Implementation

```python
# src/parser/grid_parser.py

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIME_SLOTS = {
    1: {"label": "Slot 1", "start": "08:30", "end": "10:00"},
    2: {"label": "Slot 2", "start": "10:00", "end": "11:30"},
    3: {"label": "Slot 3", "start": "11:30", "end": "13:00"},
    # Slot index 4 in raw matrix is the "Break" column — SKIP
    4: {"label": "Slot 4", "start": "13:30", "end": "15:00"},
    5: {"label": "Slot 5", "start": "15:00", "end": "16:30"},
    6: {"label": "Slot 6", "start": "16:30", "end": "18:00"},
}

def parse_grid(raw_table: list) -> dict:
    """
    Converts raw pdfplumber table matrix into a structured dict:
    {
        "Monday": {
            1: "cell text or None",
            2: "...",
            ...
        },
        ...
    }
    """
    # Step 1: Identify header row (row 0) and find column indices for each slot
    # Step 2: Identify day rows and their indices
    # Step 3: Build (day, slot) -> cell_text mapping
    # Step 4: Skip the Break column (identify it by checking for "Break" or "1:00" in header)
    ...
```

#### Key Challenges & Solutions

| Challenge | Solution |
|---|---|
| Break column mixed in with slot columns | Detect by scanning header row for "Break" or "1:00" text, then skip that column index |
| Empty cells returned as `None` | Normalize `None` → `""` (empty string) |
| Multi-line cell text joined with `\n` | Preserve `\n` — cell parser in Phase 3 will split on it |
| Row 0 is header, not a day | Skip rows where first cell doesn't match a known day name |
| Day names may have extra whitespace | Strip and `.title()` normalize before matching |

#### ✅ Phase 2 Done When:
- `parse_grid()` returns a clean dict with all 5 days as keys
- Each day has exactly 6 slot keys (1–6)
- Break column is excluded
- Printing the dict shows recognizable subject names per cell

---

### Phase 3 — Cell Parser

**File:** `src/parser/cell_parser.py`

#### Goal
Parse a single cell's raw text string into structured fields: subject, room, instructor.

#### Cell Text Format (from pdfplumber)
Cells contain newline-separated text:
```
"Operating Systems-Lab\nSE LAB-1\nSyed Ammar Yasir(CS)"
```

Some cells may only have 2 lines if room info is embedded in the subject, or text wrapping causes 4+ lines.

#### Implementation

```python
# src/parser/cell_parser.py
import re
from dataclasses import dataclass
from typing import Optional

# Room code patterns
ROOM_PATTERN = re.compile(
    r'^(CS|SE|MS|EE|BBA|MBA)\s?(LAB[-\s]\d+|\d+)$', re.IGNORECASE
)

# Instructor pattern: ends with department abbreviation in parentheses
INSTRUCTOR_PATTERN = re.compile(r'.+\([A-Z]+\)$')

# 2-hour class marker
TWO_HOUR_PATTERN = re.compile(r'\(2\s?[Hh]rs?\)', re.IGNORECASE)

@dataclass
class ParsedCell:
    subject: str
    room_code: Optional[str]        # e.g. "CS LAB-3", "CS-3", "MS-8"
    room_type: str                  # "lab" or "classroom"
    instructor: Optional[str]       # e.g. "Syed Ammar Yasir"
    instructor_dept: Optional[str]  # e.g. "CS"
    is_two_hour: bool
    raw_text: str

def parse_cell(cell_text: str) -> Optional[ParsedCell]:
    """
    Parses a single cell's raw text into a ParsedCell.
    Returns None if cell is empty.
    """
    if not cell_text or not cell_text.strip():
        return None

    lines = [line.strip() for line in cell_text.split('\n') if line.strip()]

    subject = None
    room_code = None
    room_type = None
    instructor = None
    instructor_dept = None

    for line in lines:
        if INSTRUCTOR_PATTERN.match(line) and instructor is None:
            # Parse instructor: "Syed Ammar Yasir(CS)" → name + dept
            match = re.match(r'^(.+)\(([A-Z]+)\)$', line)
            if match:
                instructor = match.group(1).strip()
                instructor_dept = match.group(2)
        elif ROOM_PATTERN.match(line) and room_code is None:
            room_code = line.upper().replace(' ', ' ')  # normalize spacing
            room_type = "lab" if "LAB" in line.upper() else "classroom"
        elif subject is None:
            subject = line

    is_two_hour = bool(TWO_HOUR_PATTERN.search(subject or ""))
    if is_two_hour:
        subject = TWO_HOUR_PATTERN.sub('', subject).strip()

    return ParsedCell(
        subject=subject,
        room_code=room_code,
        room_type=room_type,
        instructor=instructor,
        instructor_dept=instructor_dept,
        is_two_hour=is_two_hour,
        raw_text=cell_text
    )
```

#### ⚠️ Edge Cases to Handle

| Case | Example | Handling |
|---|---|---|
| Lab class — subject ends with "-Lab" | `"Operating Systems-Lab"` | Keep suffix; set `room_type="lab"` |
| Subject spans 2 text lines due to wrapping | `"Computer Organization\nand Assembly Language"` | Concatenate non-room, non-instructor lines |
| `(2Hrs)` in subject name | `"Operating Systems(2Hrs)"` | Set `is_two_hour=True`, strip marker from subject |
| Dr. title in instructor name | `"Dr.Salman Iqbal(CS)"` | Preserve "Dr." prefix |
| Room is a pure number with prefix | `"MS-8"`, `"CS-2"` | Match as classroom, not lab |

#### ✅ Phase 3 Done When:
- Unit tests pass for all cell types in the sample PDF
- `ParsedCell` fields are correctly populated for every cell variant
- Two-hour flag is correctly detected

---

### Phase 4 — Normalizer & Record Builder

**File:** `src/parser/normalizer.py`

#### Goal
Combine Phase 2 (grid) + Phase 3 (cells) outputs, expand 2-hour classes, extract metadata, and produce a clean list of schedule records ready for DB insertion.

#### Output Schema (per record)

```python
@dataclass
class ScheduleRecord:
    batch: str              # "BCS-SP24-5C"
    semester: str           # "Spring-2026"
    day: str                # "Monday"
    slot: int               # 1–6
    time_start: str         # "08:30"
    time_end: str           # "10:00"
    subject: str            # "Operating Systems"
    subject_is_lab: bool    # True if subject name ends with "-Lab"
    room_code: str          # "SE LAB-1"
    room_type: str          # "lab" or "classroom"
    instructor_name: str    # "Syed Ammar Yasir"
    instructor_dept: str    # "CS"
    is_two_hour: bool       # True if spans 2 slots
```

#### 2-Hour Class Expansion Logic

When a cell has `is_two_hour=True` and is in **Slot 3** (11:30 AM–1:00 PM), it runs through the break and effectively finishes at Slot 4 start (1:30 PM). Create **one** record for Slot 3, set `time_end = "13:30"` to account for the break, and do NOT create a Slot 4 duplicate.

```python
def expand_two_hour(record: ScheduleRecord) -> ScheduleRecord:
    """Adjust time_end for 2-hour classes spanning into break."""
    if record.slot == 3 and record.is_two_hour:
        record.time_end = "13:30"  # extends through 1:00–1:30 break
    return record
```

#### Metadata Extraction

```python
import re

def extract_batch(header_text: str) -> str:
    """Extract batch code like BCS-SP24-5C from header text."""
    match = re.search(r'BCS-[A-Z]{2}\d{2}-\d+[A-Z]', header_text)
    return match.group(0) if match else "UNKNOWN"

def extract_semester(header_text: str) -> str:
    """Extract semester label like Spring-2026."""
    match = re.search(r'(Spring|Fall|Summer)-(\d{4})', header_text)
    return match.group(0) if match else "UNKNOWN"
```

#### ✅ Phase 4 Done When:
- `normalize()` returns a flat list of `ScheduleRecord` objects
- All 5 days × 6 slots are accounted for (empty cells produce no records)
- 2-hour classes appear once with correct extended time
- Batch and semester metadata are populated on every record

---

### Phase 5 — Database Schema & Persistence

**File:** `src/db/schema.sql`, `src/db/database.py`

#### Schema Design

```sql
-- schema.sql

CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,          -- "BCS-SP24-5C"
    semester TEXT NOT NULL,             -- "Spring-2026"
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS instructors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                 -- "Syed Ammar Yasir"
    department TEXT,                    -- "CS"
    UNIQUE(name, department)
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,          -- "SE LAB-1", "CS-3"
    type TEXT NOT NULL,                 -- "lab" or "classroom"
    -- Location fields — populated manually later
    building TEXT,
    floor INTEGER,
    description TEXT,                   -- "2nd floor, 3rd room from east wing"
    landmark TEXT                       -- "right next to the library"
);

CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    instructor_id INTEGER REFERENCES instructors(id),
    room_id INTEGER REFERENCES rooms(id),
    day TEXT NOT NULL CHECK(day IN ('Monday','Tuesday','Wednesday','Thursday','Friday')),
    slot INTEGER NOT NULL CHECK(slot BETWEEN 1 AND 6),
    time_start TEXT NOT NULL,           -- "08:30"
    time_end TEXT NOT NULL,             -- "10:00"
    subject TEXT NOT NULL,
    subject_is_lab INTEGER DEFAULT 0,   -- 0 or 1 (boolean)
    is_two_hour INTEGER DEFAULT 0,
    UNIQUE(batch_id, day, slot)
);

-- Notification subscriptions (future use)
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_type TEXT NOT NULL CHECK(user_type IN ('student','instructor')),
    identifier TEXT NOT NULL,           -- batch code for student, instructor name for instructor
    contact TEXT NOT NULL,              -- phone/email
    notify_minutes_before INTEGER DEFAULT 15
);
```

#### Database Helper

```python
# src/db/database.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "timetable.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    schema = (Path(__file__).parent / "schema.sql").read_text()
    with get_connection() as conn:
        conn.executescript(schema)

def insert_schedule_records(records: list):
    """Upsert all ScheduleRecord objects into DB."""
    with get_connection() as conn:
        for r in records:
            # Upsert batch
            conn.execute(
                "INSERT OR IGNORE INTO batches(code, semester) VALUES (?,?)",
                (r.batch, r.semester)
            )
            batch_id = conn.execute(
                "SELECT id FROM batches WHERE code=?", (r.batch,)
            ).fetchone()[0]

            # Upsert instructor
            instructor_id = None
            if r.instructor_name:
                conn.execute(
                    "INSERT OR IGNORE INTO instructors(name, department) VALUES(?,?)",
                    (r.instructor_name, r.instructor_dept)
                )
                instructor_id = conn.execute(
                    "SELECT id FROM instructors WHERE name=? AND department=?",
                    (r.instructor_name, r.instructor_dept)
                ).fetchone()[0]

            # Upsert room
            room_id = None
            if r.room_code:
                conn.execute(
                    "INSERT OR IGNORE INTO rooms(code, type) VALUES(?,?)",
                    (r.room_code, r.room_type)
                )
                room_id = conn.execute(
                    "SELECT id FROM rooms WHERE code=?", (r.room_code,)
                ).fetchone()[0]

            # Insert schedule (ignore conflict on re-import)
            conn.execute("""
                INSERT OR REPLACE INTO schedule
                (batch_id, instructor_id, room_id, day, slot, time_start, time_end,
                 subject, subject_is_lab, is_two_hour)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                batch_id, instructor_id, room_id,
                r.day, r.slot, r.time_start, r.time_end,
                r.subject, int(r.subject_is_lab), int(r.is_two_hour)
            ))
        conn.commit()
```

#### ✅ Phase 5 Done When:
- `init_db()` creates the database with no errors
- `insert_schedule_records()` populates all tables from normalized records
- Running `sqlite3 timetable.db "SELECT * FROM schedule LIMIT 5;"` returns valid rows
- Re-running the import does not create duplicate records

---

### Phase 6 — Location Resolver

**File:** `src/location/resolver.py`, `src/db/seeder.py`

#### Goal
Map raw room codes to human-readable physical location descriptions. This data is **manually provided** by the user/admin — the code only provides the structure to store and query it.

#### Location Data Format

The user will provide location info in a simple JSON/YAML format:

```json
// data/room_locations.json  (user fills this in)
{
  "CS LAB-3": {
    "building": "CS Block",
    "floor": 1,
    "description": "Ground floor, third room from the main entrance",
    "landmark": null
  },
  "SE LAB-1": {
    "building": "SE Block",
    "floor": 2,
    "description": "Second floor, first room after the stairs",
    "landmark": "directly above the admin office"
  },
  "MS LAB-5": {
    "building": "MS Block",
    "floor": 1,
    "description": "Ground floor lab, room 5",
    "landmark": null
  },
  "CS-3": {
    "building": "CS Block",
    "floor": 1,
    "description": "Ground floor, lecture hall 3",
    "landmark": null
  }
}
```

#### Seeder

```python
# src/db/seeder.py
import json
from pathlib import Path
from .database import get_connection

def seed_locations(json_path: str = "data/room_locations.json"):
    data = json.loads(Path(json_path).read_text())
    with get_connection() as conn:
        for code, info in data.items():
            conn.execute("""
                UPDATE rooms SET
                    building = ?,
                    floor = ?,
                    description = ?,
                    landmark = ?
                WHERE code = ?
            """, (
                info.get("building"),
                info.get("floor"),
                info.get("description"),
                info.get("landmark"),
                code
            ))
        conn.commit()
    print(f"Seeded location data for {len(data)} rooms.")
```

#### Resolver

```python
# src/location/resolver.py
from src.db.database import get_connection

def resolve_room(room_code: str) -> dict:
    """
    Returns human-readable location info for a room code.
    Returns a dict with all location fields, or minimal info if not seeded yet.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM rooms WHERE code = ?", (room_code,)
        ).fetchone()

    if not row:
        return {"code": room_code, "description": "Location not found"}

    location = dict(row)

    # Build a natural language description
    parts = []
    if location.get("building"):
        parts.append(location["building"])
    if location.get("floor") is not None:
        floor_label = {1: "Ground floor", 2: "2nd floor", 3: "3rd floor"}.get(
            location["floor"], f"Floor {location['floor']}"
        )
        parts.append(floor_label)
    if location.get("description"):
        parts.append(location["description"])
    if location.get("landmark"):
        parts.append(f"Landmark: {location['landmark']}")

    location["human_readable"] = " — ".join(parts) if parts else room_code
    return location
```

#### ✅ Phase 6 Done When:
- `seed_locations()` updates the `rooms` table with location data
- `resolve_room("CS LAB-3")` returns a dict with `human_readable` field
- Rooms without location data gracefully return a fallback string

---

### Phase 7 — CLI Entrypoint

**File:** `scripts/run_parser.py`

#### Goal
Single command to parse a PDF and load it into the database.

```python
#!/usr/bin/env python3
# scripts/run_parser.py

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.pdf_extractor import extract_raw_table, extract_metadata
from src.parser.grid_parser import parse_grid
from src.parser.cell_parser import parse_cell
from src.parser.normalizer import normalize
from src.db.database import init_db, insert_schedule_records

def main(pdf_path: str):
    print(f"[1/5] Opening PDF: {pdf_path}")
    raw_table = extract_raw_table(pdf_path)
    metadata = extract_metadata(pdf_path)

    print("[2/5] Parsing grid structure...")
    grid = parse_grid(raw_table)

    print("[3/5] Parsing cell contents...")
    # (cell parsing happens inside normalize)

    print("[4/5] Normalizing records...")
    records = normalize(grid, metadata)
    print(f"      → {len(records)} schedule records extracted")

    print("[5/5] Saving to database...")
    init_db()
    insert_schedule_records(records)
    print("✅ Done. Database updated.")

    # Print summary
    print("\n--- Summary ---")
    for r in records:
        print(f"  {r.day:12} Slot {r.slot} | {r.subject:35} | {r.room_code:12} | {r.instructor_name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_parser.py <path/to/timetable.pdf>")
        sys.exit(1)
    main(sys.argv[1])
```

**Usage:**
```bash
python scripts/run_parser.py data/raw/BCS-SP24-5C.pdf
```

---

### Phase 8 — Testing

**Directory:** `tests/`

Write unit tests for each parser component. Use the actual extracted data from the sample PDF as fixtures.

#### Test Fixtures (based on sample PDF)

```python
# tests/fixtures.py

SAMPLE_CELLS = {
    "os_lab": "Operating Systems-Lab\nSE LAB-1\nSyed Ammar Yasir(CS)",
    "comp_org": "Computer Organization\nand Assembly Language\nCS-3\nSania Qayume(CS)",
    "daa": "Design and Analysis of\nAlgorithms\nCS-3\nDr.Salman Iqbal(CS)",
    "os_2hr": "Operating\nSystems(2Hrs)\nCS-2\nSyed Ammar\nYasir(CS)",
    "stats": "Statistics and\nProbability/ M-Statistic\nCS-3\nMuhammad Sajjad(Math)",
    "web_lab": "Web Techonologies-Lab\nCS LAB-3\nRizwan Ali (CS)",
    "mob_lab": "Mobile Application\nDevelopment-Lab\nMS LAB-5\nAbrar Siddique(CS)",
    "empty": None,
}
```

#### Test Cases

```python
# tests/test_cell_parser.py
from src.parser.cell_parser import parse_cell
from tests.fixtures import SAMPLE_CELLS

def test_parse_os_lab():
    result = parse_cell(SAMPLE_CELLS["os_lab"])
    assert result.subject == "Operating Systems-Lab"
    assert result.room_code == "SE LAB-1"
    assert result.room_type == "lab"
    assert result.instructor == "Syed Ammar Yasir"
    assert result.instructor_dept == "CS"
    assert result.is_two_hour == False
    assert result.subject_is_lab == True

def test_parse_two_hour():
    result = parse_cell(SAMPLE_CELLS["os_2hr"])
    assert result.is_two_hour == True
    assert result.subject == "Operating Systems"  # (2Hrs) stripped

def test_parse_dr_prefix():
    result = parse_cell(SAMPLE_CELLS["daa"])
    assert result.instructor == "Dr.Salman Iqbal"
    assert result.instructor_dept == "CS"

def test_parse_empty():
    result = parse_cell(SAMPLE_CELLS["empty"])
    assert result is None

def test_parse_math_dept():
    result = parse_cell(SAMPLE_CELLS["stats"])
    assert result.instructor_dept == "Math"
```

Run tests:
```bash
python -m pytest tests/ -v
```

---

## 4. Data Flow Diagram

```
PDF File
   │
   ▼
[pdf_extractor.py]
   │  pdfplumber → raw 2D matrix (list of lists)
   │
   ▼
[grid_parser.py]
   │  matrix → {day: {slot: cell_text}} dict
   │  (skips break column, normalizes day names)
   │
   ▼
[cell_parser.py]  ◄── called for each cell
   │  cell_text → ParsedCell(subject, room, instructor, flags)
   │
   ▼
[normalizer.py]
   │  grid + metadata → list[ScheduleRecord]
   │  (expands 2hr classes, attaches batch/semester)
   │
   ▼
[database.py]
   │  upserts into: batches, instructors, rooms, schedule tables
   │
   ▼
[resolver.py]  ◄── called at notification time
      room_code → human_readable location string
```

---

## 5. Requirements File

```txt
# requirements.txt
pdfplumber>=0.10.0
pytest>=7.0
```

---

## 6. Known Challenges & Mitigation

| Challenge | Risk | Mitigation |
|---|---|---|
| pdfplumber misses merged cells | High | Inspect with `inspect_pdf.py` first; try multiple `table_settings` combos |
| Text wrapping splits subject names across lines | Medium | Collect consecutive non-room, non-instructor lines as subject |
| Typos in PDF (e.g. "Techonologies") | Low | Store raw text as-is; do not auto-correct |
| Room code format variations | Medium | Regex pattern with flexible spacing: `CS LAB-3` vs `CS-LAB-3` vs `CSLAB3` |
| Multiple timetable pages (future) | Medium | `page_index` param in extractor; loop over pages |
| `(2Hrs)` class slot boundary unclear | Medium | For now: assume slot 3 always → extends through break. Log a warning for other slots |

---

## 7. Future Phases (Stub — Do Not Implement Yet)

### Phase 9 — Notification Scheduler (`src/notify/scheduler.py`)

- Query schedule for classes starting within N minutes
- Look up subscriptions table for matching batch codes or instructor names
- Resolve room location via `resolver.py`
- Format message: `"[10 min] Operating Systems — SE LAB-1 (2nd floor, first room after stairs)"`
- Send via SMS/WhatsApp/Email (provider TBD)

### Phase 10 — Multi-PDF Batch Processing

- Accept a directory of PDFs (one per batch)
- Process all, merge into single DB
- Detect and warn on scheduling conflicts (same room, same slot, different batch)

### Phase 11 — Web/Admin Interface

- Simple Flask/FastAPI app to:
  - Upload new PDFs
  - Fill in room location descriptions
  - Manage notification subscriptions
  - View parsed timetable in browser

---

## 8. Quick Start Checklist for the Agent

```
[ ] 1. Create project structure as defined in Section 2
[ ] 2. Install: pip install pdfplumber pytest
[ ] 3. Copy PDF to data/raw/
[ ] 4. Run inspect_pdf.py — confirm table extraction works
[ ] 5. Implement pdf_extractor.py — test with assert on table shape
[ ] 6. Implement grid_parser.py — print grid dict to verify
[ ] 7. Implement cell_parser.py — run unit tests
[ ] 8. Implement normalizer.py — print all ScheduleRecord objects
[ ] 9. Implement schema.sql + database.py
[ ] 10. Run scripts/run_parser.py — verify DB is populated
[ ] 11. Create data/room_locations.json (user fills in)
[ ] 12. Run seeder.py — verify rooms tab