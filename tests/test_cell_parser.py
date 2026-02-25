from src.parser.cell_parser import parse_cell
from tests.fixtures import SAMPLE_CELLS


def test_parse_os_lab():
    result = parse_cell(SAMPLE_CELLS["os_lab"])
    assert result.subject == "Operating Systems-Lab"
    assert result.room_code == "SE LAB-1"
    assert result.room_type == "lab"
    assert result.instructor == "Syed Ammar Yasir"
    assert result.instructor_dept == "CS"
    assert result.is_two_hour is False
    assert result.subject_is_lab is True


def test_parse_two_hour():
    result = parse_cell(SAMPLE_CELLS["os_2hr"])
    assert result.is_two_hour is True
    assert result.subject == "Operating Systems"


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
