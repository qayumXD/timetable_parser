import pdfplumber


def inspect(pdf_path: str):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        print("=== RAW TEXT ===")
        print(page.extract_text())

        print("\n=== WORDS WITH BBOXES ===")
        for word in page.extract_words():
            print(word)

        print("\n=== TABLE (default) ===")
        tables = page.extract_tables()
        for i, table in enumerate(tables):
            print(f"Table {i}:")
            for row in table:
                print(row)

        settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        }
        print("\n=== TABLE (lines strategy) ===")
        tables = page.extract_tables(table_settings=settings)
        for i, table in enumerate(tables):
            print(f"Table {i}:")
            for row in table:
                print(row)

        print("\n=== LINES ===")
        for line in page.lines:
            print(line)

        print("\n=== RECTS ===")
        for rect in page.rects:
            print(rect)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_pdf.py <path/to/timetable.pdf>")
        raise SystemExit(1)
    inspect(sys.argv[1])
