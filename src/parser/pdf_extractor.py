import pdfplumber
from typing import Optional

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "edge_min_length": 3,
    "min_words_vertical": 1,
    "min_words_horizontal": 1,
    "intersection_tolerance": 3,
}


def extract_raw_table(pdf_path: str, page_index: int = 0) -> list[list[Optional[str]]]:
    """
    Opens the PDF and extracts the raw 2D table from the specified page.
    Returns a list of rows, each row being a list of cell strings (or None).
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        tables = page.extract_tables(table_settings=TABLE_SETTINGS)
        if not tables:
            raise ValueError(f"No tables detected on page {page_index} of {pdf_path}")
        return max(tables, key=lambda t: len(t) * len(t[0]) if t and t[0] else 0)


def extract_metadata(pdf_path: str, page_index: int = 0) -> dict:
    """
    Extracts header metadata: batch name, timetable title, semester tags, date.
    Uses word-level bounding boxes since metadata is outside the grid.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        text = page.extract_text() or ""
        return {"raw_header_text": text}
