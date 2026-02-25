from pathlib import Path
import pytest

from src.parser.pdf_extractor import extract_raw_table


def test_extract_raw_table_from_sample_pdf():
    pdf_path = Path("data/raw/BCS-SP24-5C.pdf")
    if not pdf_path.exists():
        pytest.skip("Sample PDF not available")

    table = extract_raw_table(str(pdf_path))
    assert table
    assert len(table) > 0
