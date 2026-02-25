import re
from dataclasses import dataclass
from typing import Optional

ROOM_PATTERN = re.compile(
    r"^(?P<dept>CS|SE|MS|EE|BBA|MBA)\s*-?\s*(?:(?:LAB)\s*-?\s*(?P<labnum>\d+)|(?P<classnum>\d+))$",
    re.IGNORECASE,
)

INSTRUCTOR_PATTERN = re.compile(r".+\([A-Za-z]+\)$")
TWO_HOUR_PATTERN = re.compile(r"\(2\s?[Hh]rs?\)", re.IGNORECASE)


@dataclass
class ParsedCell:
    subject: str
    room_code: Optional[str]
    room_type: Optional[str]
    instructor: Optional[str]
    instructor_dept: Optional[str]
    is_two_hour: bool
    subject_is_lab: bool
    raw_text: str


def _normalize_room_code(raw: str) -> Optional[tuple[str, str]]:
    match = ROOM_PATTERN.match(raw.replace("-", "-").strip())
    if not match:
        return None
    dept = match.group("dept").upper()
    labnum = match.group("labnum")
    classnum = match.group("classnum")
    if labnum:
        return (f"{dept} LAB-{labnum}", "lab")
    if classnum:
        return (f"{dept}-{classnum}", "classroom")
    return None


def parse_cell(cell_text: str) -> Optional[ParsedCell]:
    """
    Parses a single cell's raw text into a ParsedCell.
    Returns None if cell is empty.
    """
    if not cell_text or not str(cell_text).strip():
        return None

    lines = [line.strip() for line in str(cell_text).split("\n") if line.strip()]

    subject_parts: list[str] = []
    room_code = None
    room_type = None
    instructor = None
    instructor_dept = None

    i = 0
    while i < len(lines):
        line = lines[i]

        if INSTRUCTOR_PATTERN.match(line) and instructor is None:
            match = re.match(r"^(.+?)\(([^)]+)\)$", line)
            if match:
                instructor = match.group(1).strip()
                instructor_dept = match.group(2).strip()
                i += 1
                continue

        # Handle instructor split across two lines, e.g. "Syed Ammar" + "Yasir(CS)"
        if (
            instructor is None
            and i + 1 < len(lines)
            and INSTRUCTOR_PATTERN.match(lines[i + 1])
            and re.search(r"\d|/|\\", line) is None
            and "-" not in line
            and len(line.split()) <= 3
        ):
            match = re.match(r"^(.+?)\(([^)]+)\)$", lines[i + 1])
            if match:
                instructor = f"{line.strip()} {match.group(1).strip()}".strip()
                instructor_dept = match.group(2).strip()
                i += 2
                continue

        room_info = _normalize_room_code(line)
        if room_info and room_code is None:
            room_code, room_type = room_info
            i += 1
            continue

        subject_parts.append(line)
        i += 1

    subject_raw = ""
    for part in subject_parts:
        if not subject_raw:
            subject_raw = part
            continue
        if len(part) <= 2 and part.islower() and subject_raw[-1].isalpha():
            subject_raw += part
        else:
            subject_raw += f" {part}"
    subject_raw = subject_raw.strip()

    subject_norm = re.sub(r"\(\s*2\s*H\s*rs?\s*\)", "(2Hrs)", subject_raw, flags=re.IGNORECASE)
    is_two_hour = bool(TWO_HOUR_PATTERN.search(subject_norm))
    subject = TWO_HOUR_PATTERN.sub("", subject_norm).strip()
    subject_is_lab = subject.lower().endswith("-lab")

    return ParsedCell(
        subject=subject,
        room_code=room_code,
        room_type=room_type,
        instructor=instructor,
        instructor_dept=instructor_dept,
        is_two_hour=is_two_hour,
        subject_is_lab=subject_is_lab,
        raw_text=str(cell_text),
    )
