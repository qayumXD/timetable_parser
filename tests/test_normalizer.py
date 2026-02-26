from src.parser.normalizer import normalize
from src.parser.cell_parser_v2 import parse_cell_v2


def test_normalize_two_hour_extends_break():
    grid = {
        "Monday": {1: "", 2: "", 3: "Operating Systems(2Hrs)\nCS-2\nSyed Ammar Yasir(CS)", 4: "", 5: "", 6: ""},
        "Tuesday": {1: "", 2: "", 3: "", 4: "", 5: "", 6: ""},
        "Wednesday": {1: "", 2: "", 3: "", 4: "", 5: "", 6: ""},
        "Thursday": {1: "", 2: "", 3: "", 4: "", 5: "", 6: ""},
        "Friday": {1: "", 2: "", 3: "", 4: "", 5: "", 6: ""},
    }
    metadata = {"raw_header_text": "COMSATS Vehari Centralized Timetable (V-2)-Spring-2026 BCS-SP24-5C"}
    records = normalize(grid, metadata, cell_parser=lambda t: parse_cell_v2(t, use_ai=False))

    assert len(records) == 1
    record = records[0]
    assert record.time_end == "13:30"
    assert record.batch == "BCS-SP24-5C"
    assert record.semester == "Spring-2026"
