"""
Tiered cell parser tests.

Fast tests run with use_ai=False so they don't require the model.
Slow tests exercise the AI fallback and are skipped if the model file is absent.
"""

from pathlib import Path

import pytest

from src.parser.cell_parser import parse_cell
from src.parser.cell_parser_v2 import is_uncertain, parse_cell_v2
from src.parser.ai_cell_parser import MODEL_PATH


# ── Uncertainty detection ─────────────────────────────────────────────────────


def test_uncertain_no_instructor():
    raw = "Pre Calculas I (Medical) Hamna Ashraf\nCS-3"
    parsed = parse_cell(raw)
    assert is_uncertain(parsed, raw)


def test_certain_clean_cell():
    raw = "Operating Systems-Lab\nSE LAB-1\nSyed Ammar Yasir(CS)"
    parsed = parse_cell(raw)
    assert not is_uncertain(parsed, raw)


def test_uncertain_very_long_subject():
    raw = "Tourism and Hospitality Marketing Dr.Affan Ud Din MS\nMS-9"
    parsed = parse_cell(raw)
    assert is_uncertain(parsed, raw)


# ── Tiered parser without AI ─────────────────────────────────────────────────-


def test_v2_clean_cell_no_ai():
    result = parse_cell_v2("Operating Systems-Lab\nSE LAB-1\nSyed Ammar Yasir(CS)", use_ai=False)
    assert result.subject == "Operating Systems-Lab"
    assert result.room_code == "SE LAB-1"
    assert result.instructor == "Syed Ammar Yasir"


def test_v2_empty_no_ai():
    result = parse_cell_v2(None, use_ai=False)
    assert result is None


# ── AI-powered (slow) tests ─────────────────────────────────────────────────--


requires_model = pytest.mark.skipif(
    not Path(MODEL_PATH).exists(),
    reason="Qwen2.5-1.5B model not downloaded",
)


@pytest.mark.slow
@requires_model
def test_ai_fixes_instructor_bleed():
    result = parse_cell_v2("Pre Calculas I (Medical) Hamna Ashraf\nCS-3")
    assert result.instructor is not None
    assert "Hamna Ashraf" in result.instructor
    assert "Hamna Ashraf" not in (result.subject or "")


@pytest.mark.slow
@requires_model
def test_ai_fixes_dld_lab_room():
    result = parse_cell_v2("Applied Physics-Lab\nDLD Lab Junaid Iqbal")
    assert result.room_code is not None
    assert "DLD" in result.room_code
    assert result.instructor is not None


@pytest.mark.slow
@requires_model
def test_ai_fixes_swapped_order():
    result = parse_cell_v2("Ayesha Rafiq (Mth)\nSE-4\nPre Calculas I")
    assert result.subject is not None
    assert result.instructor is not None
    assert "Ayesha" in result.instructor
