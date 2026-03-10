"""
Tiered faculty cell parser:
  Tier 1 -> regex heuristics (faculty_parser.py)
  Tier 2 -> LLM fallback     (ai_cell_parser.py) on uncertain results
"""

from typing import Optional

from .ai_cell_parser import ai_parse_faculty_cell
from .faculty_parser import FacultyCell, parse_faculty_cell


def is_uncertain_faculty(parsed: Optional[FacultyCell], raw_text: str) -> bool:
    """Returns True when regex parse looks incomplete or likely wrong."""
    if parsed is None:
        return False

    lines = [line.strip() for line in (raw_text or "").split("\n") if line.strip()]

    return (
        parsed.batch_code == "UNKNOWN"
        or parsed.room_code == "UNKNOWN"
        or len(lines) >= 4
    )


def parse_faculty_cell_v2(cell_text: str, use_ai: bool = True) -> Optional[FacultyCell]:
    """
    Parses a faculty timetable cell with AI fallback for uncertain cases.

    Args:
        cell_text: Raw timetable cell text.
        use_ai: Disable to skip LLM fallback (useful in tests).

    Returns:
        FacultyCell or None.
    """
    parsed = parse_faculty_cell(cell_text)

    if not use_ai or not is_uncertain_faculty(parsed, cell_text or ""):
        return parsed

    preview = repr(cell_text)[:80]
    print(f"[faculty_parser_v2] Uncertain result - calling LLM for: {preview}")

    try:
        ai_result = ai_parse_faculty_cell(cell_text)
    except (ImportError, FileNotFoundError) as exc:
        print(f"[faculty_parser_v2] AI unavailable ({exc}); using regex result")
        return parsed
    except Exception as exc:  # noqa: BLE001 - log and continue with fallback
        print(f"[faculty_parser_v2] AI error ({exc}); using regex result")
        return parsed

    if ai_result is None:
        print("[faculty_parser_v2] LLM returned None - keeping regex result")
        return parsed

    if parsed is None:
        return FacultyCell(
            course_name=ai_result.get("course_name") or "",
            course_credits=ai_result.get("course_credits") or None,
            batch_code=ai_result.get("batch_code") or "UNKNOWN",
            room_code=ai_result.get("room_code") or "UNKNOWN",
        )

    # Merge AI output only where regex was weak/unknown.
    course_name = ai_result.get("course_name") or parsed.course_name
    course_credits = ai_result.get("course_credits") or parsed.course_credits
    batch_code = parsed.batch_code
    room_code = parsed.room_code

    if batch_code == "UNKNOWN" and ai_result.get("batch_code"):
        batch_code = ai_result["batch_code"]

    if room_code == "UNKNOWN" and ai_result.get("room_code"):
        room_code = ai_result["room_code"]

    return FacultyCell(
        course_name=course_name,
        course_credits=course_credits,
        batch_code=batch_code,
        room_code=room_code,
    )
