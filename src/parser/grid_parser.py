import re
from typing import Any

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIME_SLOTS = {
    1: {"label": "Slot 1", "start": "08:30", "end": "10:00"},
    2: {"label": "Slot 2", "start": "10:00", "end": "11:30"},
    3: {"label": "Slot 3", "start": "11:30", "end": "13:00"},
    4: {"label": "Slot 4", "start": "13:30", "end": "15:00"},
    5: {"label": "Slot 5", "start": "15:00", "end": "16:30"},
    6: {"label": "Slot 6", "start": "16:30", "end": "18:00"},
}

SLOT_HEADER_PATTERN = re.compile(r"\b([1-6])\b")
BREAK_PATTERN = re.compile(r"break", re.IGNORECASE)


def _normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_day(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return ""
    title = cleaned.title()
    if title in DAYS:
        return title
    reversed_title = cleaned[::-1].title()
    if reversed_title in DAYS:
        return reversed_title
    return title


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
    if not raw_table or not raw_table[0]:
        raise ValueError("raw_table is empty")

    header_row = [ _normalize_cell(c) for c in raw_table[0] ]

    slot_columns: dict[int, int] = {}
    for idx, cell in enumerate(header_row):
        if not cell:
            continue
        if BREAK_PATTERN.search(cell):
            continue
        match = SLOT_HEADER_PATTERN.search(cell)
        if match:
            slot = int(match.group(1))
            if slot not in slot_columns:
                slot_columns[slot] = idx

    missing_slots = [s for s in range(1, 7) if s not in slot_columns]
    if missing_slots:
        raise ValueError(f"Missing slot columns in header: {missing_slots}")

    grid: dict[str, dict[int, str]] = {day: {s: "" for s in range(1, 7)} for day in DAYS}

    for row in raw_table[1:]:
        if not row:
            continue
        first_cell = _normalize_cell(row[0])
        if not first_cell:
            continue
        day = _normalize_day(first_cell)
        if day not in grid:
            continue

        for slot, col_idx in slot_columns.items():
            cell_text = ""
            if col_idx < len(row):
                cell_text = _normalize_cell(row[col_idx])
            grid[day][slot] = cell_text

    return grid
