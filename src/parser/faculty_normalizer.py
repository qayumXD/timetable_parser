import re
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .faculty_parser import extract_faculty_name, FacultyCell
from .faculty_parser_v2 import parse_faculty_cell_v2
from .grid_parser import TIME_SLOTS


@dataclass
class FacultyScheduleRecord:
    """Represents a single faculty schedule entry"""
    teacher_name: str
    semester: str
    day: str
    slot: int
    time_start: str
    time_end: str
    course_name: str
    course_credits: Optional[str]
    batch_code: str
    room_code: str


def extract_semester_from_header(header_text: str) -> str:
    """
    Extracts semester from header text.
    
    Examples:
    "Spring-2026" -> "Spring-2026"
    "Fall-2025" -> "Fall-2025"
    """
    match = re.search(r"(Spring|Fall|Summer)-(\d{4})", header_text)
    return match.group(0) if match else "UNKNOWN"


def _iter_faculty_grid(grid: dict) -> Iterable[tuple[str, int, str]]:
    """Iterates through grid yielding day, slot, cell_text"""
    for day, slots in grid.items():
        for slot, cell_text in slots.items():
            yield day, int(slot), cell_text


def normalize_faculty(
    grid: dict,
    metadata: dict,
    cell_parser: Callable[[str], Optional[FacultyCell]] = parse_faculty_cell_v2,
) -> list[FacultyScheduleRecord]:
    """
    Normalizes faculty grid into schedule records.
    
    Args:
        grid: Grid of faculty timetable cells
        metadata: Metadata including header text
        cell_parser: Function to parse cell contents
    
    Returns:
        List of FacultyScheduleRecord objects
    """
    header_text = metadata.get("raw_header_text", "") if metadata else ""
    teacher_name = extract_faculty_name(header_text)
    semester = extract_semester_from_header(header_text)
    
    records: list[FacultyScheduleRecord] = []
    
    for day, slot, cell_text in _iter_faculty_grid(grid):
        parsed = cell_parser(cell_text)
        if not parsed:
            continue
        
        slot_info = TIME_SLOTS.get(slot)
        if not slot_info:
            continue
        
        record = FacultyScheduleRecord(
            teacher_name=teacher_name,
            semester=semester,
            day=day,
            slot=slot,
            time_start=slot_info["start"],
            time_end=slot_info["end"],
            course_name=parsed.course_name,
            course_credits=parsed.course_credits,
            batch_code=parsed.batch_code,
            room_code=parsed.room_code,
        )
        
        records.append(record)
    
    return records
