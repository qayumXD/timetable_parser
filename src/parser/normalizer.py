import re
from dataclasses import dataclass
from typing import Iterable

from .cell_parser import parse_cell
from .grid_parser import TIME_SLOTS


@dataclass
class ScheduleRecord:
    batch: str
    semester: str
    day: str
    slot: int
    time_start: str
    time_end: str
    subject: str
    subject_is_lab: bool
    room_code: str
    room_type: str
    instructor_name: str
    instructor_dept: str
    is_two_hour: bool


def extract_batch(header_text: str) -> str:
    match = re.search(r"BCS-[A-Z]{2}\d{2}-\d+[A-Z]", header_text)
    return match.group(0) if match else "UNKNOWN"


def extract_semester(header_text: str) -> str:
    match = re.search(r"(Spring|Fall|Summer)-(\d{4})", header_text)
    return match.group(0) if match else "UNKNOWN"


def expand_two_hour(record: ScheduleRecord) -> ScheduleRecord:
    if record.slot == 3 and record.is_two_hour:
        record.time_end = "13:30"
    return record


def _iter_grid(grid: dict) -> Iterable[tuple[str, int, str]]:
    for day, slots in grid.items():
        for slot, cell_text in slots.items():
            yield day, int(slot), cell_text


def normalize(grid: dict, metadata: dict) -> list[ScheduleRecord]:
    header_text = metadata.get("raw_header_text", "") if metadata else ""
    batch = extract_batch(header_text)
    semester = extract_semester(header_text)

    records: list[ScheduleRecord] = []

    for day, slot, cell_text in _iter_grid(grid):
        parsed = parse_cell(cell_text)
        if not parsed:
            continue

        slot_info = TIME_SLOTS.get(slot)
        if not slot_info:
            continue

        record = ScheduleRecord(
            batch=batch,
            semester=semester,
            day=day,
            slot=slot,
            time_start=slot_info["start"],
            time_end=slot_info["end"],
            subject=parsed.subject,
            subject_is_lab=parsed.subject_is_lab,
            room_code=parsed.room_code or "",
            room_type=parsed.room_type or "",
            instructor_name=parsed.instructor or "",
            instructor_dept=parsed.instructor_dept or "",
            is_two_hour=parsed.is_two_hour,
        )

        record = expand_two_hour(record)
        records.append(record)

    return records
