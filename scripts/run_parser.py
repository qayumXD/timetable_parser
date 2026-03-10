#!/usr/bin/env python3
import sys
import csv
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.pdf_extractor import extract_raw_table, extract_metadata, get_page_count
from src.parser.grid_parser import parse_grid
from src.parser.timetable_detector import detect_timetable_type
from src.parser.normalizer import normalize, ScheduleRecord
from src.parser.faculty_normalizer import normalize_faculty, FacultyScheduleRecord
from src.db.database import init_db, insert_schedule_records


CSV_OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Student CSV headers
STUDENT_CSV_HEADERS = [
    "batch", "semester", "day", "slot", "time_start", "time_end",
    "subject", "subject_is_lab", "room_code", "room_type",
    "instructor_name", "instructor_dept", "is_two_hour"
]

# Faculty CSV headers
FACULTY_CSV_HEADERS = [
    "teacher_name", "semester", "day", "slot", "time_start", "time_end",
    "course_name", "course_credits", "batch_code", "room_code"
]


def create_csv_file(pdf_path: str, timetable_type: str) -> Path:
    """Creates a new CSV file with appropriate headers"""
    CSV_OUTPUT_DIR.mkdir(exist_ok=True)
    
    pdf_name = Path(pdf_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{pdf_name}_{timestamp}.csv"
    csv_path = CSV_OUTPUT_DIR / csv_filename
    
    headers = FACULTY_CSV_HEADERS if timetable_type == "faculty" else STUDENT_CSV_HEADERS
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
    
    return csv_path


def append_student_records_to_csv(csv_path: Path, records: list[ScheduleRecord]):
    """Appends student records to CSV"""
    if not records:
        return
    
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=STUDENT_CSV_HEADERS)
        for record in records:
            writer.writerow({
                "batch": record.batch,
                "semester": record.semester,
                "day": record.day,
                "slot": record.slot,
                "time_start": record.time_start,
                "time_end": record.time_end,
                "subject": record.subject,
                "subject_is_lab": record.subject_is_lab,
                "room_code": record.room_code,
                "room_type": record.room_type,
                "instructor_name": record.instructor_name,
                "instructor_dept": record.instructor_dept,
                "is_two_hour": record.is_two_hour
            })


def append_faculty_records_to_csv(csv_path: Path, records: list[FacultyScheduleRecord]):
    """Appends faculty records to CSV"""
    if not records:
        return
    
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FACULTY_CSV_HEADERS)
        for record in records:
            writer.writerow({
                "teacher_name": record.teacher_name,
                "semester": record.semester,
                "day": record.day,
                "slot": record.slot,
                "time_start": record.time_start,
                "time_end": record.time_end,
                "course_name": record.course_name,
                "course_credits": record.course_credits or "",
                "batch_code": record.batch_code,
                "room_code": record.room_code
            })


def process_student_timetable(pdf_path: str, max_pages: int = None):
    """Process student timetable"""
    print(f"[1/6] Opening PDF (Student): {pdf_path}")
    page_count = get_page_count(pdf_path)
    
    if max_pages is not None and max_pages > 0:
        page_count = min(page_count, max_pages)
        print(f"      -> Found {get_page_count(pdf_path)} page(s) total, processing {page_count} page(s)")
    else:
        print(f"      -> Found {page_count} page(s)")
    
    csv_path = create_csv_file(pdf_path, "student")
    print(f"[2/6] Created CSV file: {csv_path.name}")
    
    all_records = []
    
    for page_num in range(page_count):
        print(f"\n--- Processing Page {page_num + 1}/{page_count} ---")
        
        try:
            raw_table = extract_raw_table(pdf_path, page_index=page_num)
            metadata = extract_metadata(pdf_path, page_index=page_num)

            print(f"[3/6] Parsing grid structure (page {page_num + 1})...")
            grid = parse_grid(raw_table)

            print(f"[4/6] Parsing cell contents (page {page_num + 1})...")

            print(f"[5/6] Normalizing records (page {page_num + 1})...")
            records = normalize(grid, metadata)
            print(f"      -> {len(records)} schedule records extracted from page {page_num + 1}")
            
            append_student_records_to_csv(csv_path, records)
            print(f"      -> Records appended to CSV")
            
            all_records.extend(records)
        except Exception as e:
            print(f"      -> Error processing page {page_num + 1}: {e}")
            continue

    print(f"\n[6/6] Saving to database...")
    print(f"      -> Total records across all pages: {len(all_records)}")
    print(f"      -> CSV file saved at: {csv_path}")
    init_db()
    insert_schedule_records(all_records)
    print("Done. Database updated.")

    print("\n--- Summary ---")
    print(f"Total records: {len(all_records)}")
    print(f"CSV output: {csv_path}")
    if all_records:
        print(f"\nFirst 5 records:")
        for i, r in enumerate(all_records[:5], 1):
            print(f"  {i}. {r.batch:15} | {r.day:12} Slot {r.slot} | {r.subject:30} | {r.room_code}")


def process_faculty_timetable(pdf_path: str, max_pages: int = None):
    """Process faculty timetable"""
    print(f"[1/5] Opening PDF (Faculty): {pdf_path}")
    page_count = get_page_count(pdf_path)
    
    if max_pages is not None and max_pages > 0:
        page_count = min(page_count, max_pages)
        print(f"      -> Found {get_page_count(pdf_path)} page(s) total, processing {page_count} page(s)")
    else:
        print(f"      -> Found {page_count} page(s)")
    
    csv_path = create_csv_file(pdf_path, "faculty")
    print(f"[2/5] Created CSV file: {csv_path.name}")
    
    all_records = []
    
    for page_num in range(page_count):
        print(f"\n--- Processing Page {page_num + 1}/{page_count} ---")
        
        try:
            raw_table = extract_raw_table(pdf_path, page_index=page_num)
            metadata = extract_metadata(pdf_path, page_index=page_num)

            print(f"[3/5] Parsing grid structure (page {page_num + 1})...")
            grid = parse_grid(raw_table)

            print(f"[4/5] Parsing faculty schedule (page {page_num + 1})...")
            records = normalize_faculty(grid, metadata)
            print(f"      -> {len(records)} schedule records extracted from page {page_num + 1}")
            
            append_faculty_records_to_csv(csv_path, records)
            print(f"      -> Records appended to CSV")
            
            all_records.extend(records)
        except Exception as e:
            print(f"      -> Error processing page {page_num + 1}: {e}")
            continue

    print(f"\n[5/5] Processing complete!")
    print(f"      -> Total records across all pages: {len(all_records)}")
    print(f"      -> CSV file saved at: {csv_path}")

    print("\n--- Summary ---")
    print(f"Total records: {len(all_records)}")
    print(f"CSV output: {csv_path}")
    if all_records:
        print(f"\nRecords:")
        for i, r in enumerate(all_records[:10], 1):
            print(f"  {i}. {r.teacher_name:25} | {r.day:12} Slot {r.slot} | {r.course_name:30} | {r.batch_code}")


def main(pdf_path: str, max_pages: int = None):
    """Main entry point - detects type and processes accordingly"""
    timetable_type = detect_timetable_type(pdf_path)
    print(f"\n['{'Faculty' if timetable_type == 'faculty' else 'Student'} Timetable Detected']")
    
    if timetable_type == "faculty":
        process_faculty_timetable(pdf_path, max_pages)
    else:
        process_student_timetable(pdf_path, max_pages)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_parser.py <path/to/timetable.pdf> [max_pages]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    main(pdf_path, max_pages)
