"""
Tiered cell parser:
  Tier 1 → regex heuristics (cell_parser.py)
  Tier 2 → LLM fallback    (ai_cell_parser.py)  — only on uncertain results
"""

import re
from typing import Optional

from .cell_parser import parse_cell, ParsedCell
from .ai_cell_parser import ai_parse_cell


# ── Confidence check ─────────────────────────────────────────────────────────

NAME_INDICATORS = re.compile(
    r'\b(Dr\.?|Mr\.?|Ms\.?|Prof\.?|Engr\.?)\b'
    r'|[A-Z][a-z]+ [A-Z][a-z]+',
    re.IGNORECASE,
)


def looks_like_name(text: str) -> bool:
    return bool(NAME_INDICATORS.search(text))


def is_uncertain(parsed: Optional[ParsedCell], raw_text: str) -> bool:
    """Returns True if the regex parse result is likely wrong or incomplete."""
    if parsed is None:
        return False

    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    return (
        parsed.instructor is None
        or parsed.room_code is None
        or len(lines) > 3
        or (parsed.subject and len(parsed.subject.split()) > 8)
        or (
            parsed.instructor is None
            and any(
                looks_like_name(l)
                for l in lines
                if l.strip() == (parsed.subject or "").strip()
            )
        )
    )


# ── Instructor dept extraction ────────────────────────────────────────────────

DEPT_SUFFIX = re.compile(r'^(.+?)\s*\(([A-Za-z][A-Za-z0-9 ]*)\)\s*$')


def _split_instructor_dept(name: str):
    if not name:
        return name, None
    m = DEPT_SUFFIX.match(name.strip())
    if m:
        return m.group(1).strip(), m.group(2)
    return name.strip(), None


def parse_cell_v2(cell_text: str, use_ai: bool = True) -> Optional[ParsedCell]:
    """
    Primary entry point for cell parsing.
    Falls back to LLM when regex result is uncertain.

    Args:
        cell_text: Raw cell string from pdfplumber.
        use_ai: Set False to disable LLM fallback (e.g. during testing).

    Returns:
        ParsedCell or None.
    """
    parsed = parse_cell(cell_text)

    if not use_ai or not is_uncertain(parsed, cell_text or ""):
        return parsed

    # ── Tier 2: LLM fallback ──────────────────────────────────────────────────
    preview = repr(cell_text)[:80]
    print(f"[cell_parser_v2] Uncertain result — calling LLM for: {preview}")
    try:
        ai_result = ai_parse_cell(cell_text)
    except (ImportError, FileNotFoundError) as exc:
        print(f"[cell_parser_v2] AI unavailable ({exc}); using regex result")
        return parsed
    except Exception as exc:  # noqa: BLE001 - log and continue with fallback
        print(f"[cell_parser_v2] AI error ({exc}); using regex result")
        return parsed

    if ai_result is None:
        print("[cell_parser_v2] LLM returned None — keeping regex result")
        return parsed

    subject = ai_result.get("subject") or (parsed.subject if parsed else "")
    room_raw = ai_result.get("room_code")
    instructor_raw = ai_result.get("instructor")

    room_type = None
    room_code = None
    if room_raw:
        room_code = room_raw
        room_type = "lab" if "LAB" in room_raw.upper() else "classroom"
    else:
        # keep regex-detected room if LLM didn't provide
        if parsed:
            room_code = parsed.room_code
            room_type = parsed.room_type

    instructor_name = None
    instructor_dept = None
    if instructor_raw:
        instructor_name, instructor_dept = _split_instructor_dept(instructor_raw)
    else:
        if parsed:
            instructor_name = parsed.instructor
            instructor_dept = parsed.instructor_dept

    TWO_HR = re.compile(r'\(2\s?[Hh]rs?\)', re.IGNORECASE)
    is_two_hour = bool(TWO_HR.search(subject))
    subject = TWO_HR.sub('', subject).strip()
    subject_is_lab = subject.lower().endswith('-lab')

    return ParsedCell(
        subject=subject,
        room_code=room_code,
        room_type=room_type,
        instructor=instructor_name,
        instructor_dept=instructor_dept,
        is_two_hour=is_two_hour,
        subject_is_lab=subject_is_lab,
        raw_text=str(cell_text),
    )
