from src.parser.faculty_parser_v2 import is_uncertain_faculty, parse_faculty_cell_v2


def test_faculty_v2_certain_cell_no_ai():
    raw = "Machine Learning Fundamentals(2Cr)\nBCS-FA23-6B\nCS-2"
    parsed = parse_faculty_cell_v2(raw, use_ai=False)
    assert parsed is not None
    assert parsed.course_name == "Machine Learning Fundamentals"
    assert parsed.course_credits == "2Cr"
    assert parsed.batch_code == "BCS-FA23-6B"
    assert parsed.room_code == "CS-2"


def test_faculty_v2_marks_unknown_room_uncertain():
    raw = "Machine Learning Fundamentals-Lab\nBCS-FA23-6D"
    parsed = parse_faculty_cell_v2(raw, use_ai=False)
    assert parsed is not None
    assert parsed.room_code == "UNKNOWN"
    assert is_uncertain_faculty(parsed, raw)


def test_faculty_v2_empty_no_ai():
    assert parse_faculty_cell_v2("", use_ai=False) is None
