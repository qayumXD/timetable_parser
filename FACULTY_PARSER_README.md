# Faculty Timetable Parser Implementation

## Overview
Added comprehensive support for parsing faculty/instructor timetables in addition to the existing student timetable functionality.

## Key Features

### 1. Automatic Timetable Type Detection
- Automatically detects whether a PDF contains a student or faculty timetable
- Uses filename patterns and content analysis to determine type
- Falls back intelligently if detection is unclear

### 2. Faculty-Specific Parsing
New modules created:
- `src/parser/faculty_parser.py` - Parses individual faculty timetable cells
- `src/parser/faculty_normalizer.py` - Normalizes faculty data into structured records
- `src/parser/timetable_detector.py` - Detects timetable type

### 3. Faculty Cell Format
Faculty timetable cells contain:
```
Course Name(Credits)
Batch Code
Room Code
```

Example:
```
Machine Learning Fundamentals(2Cr)
BCS-FA23-6B
CS-2
```

### 4. Faculty CSV Export
Faculty CSV files contain these columns:
- `teacher_name` - Name of the instructor
- `semester` - Semester (e.g., Spring-2026)
- `day` - Day of week (Monday-Friday)
- `slot` - Time slot (1-6)
- `time_start` - Start time (HH:MM format)
- `time_end` - End time (HH:MM format)
- `course_name` - Course name
- `course_credits` - Credit hours (if available)
- `batch_code` - Batch code for which course is taught
- `room_code` - Room/location code

### 5. Multi-Page Processing
Both student and faculty parsers support:
- Processing all pages in a PDF (e.g., 65 faculty timetables)
- Incremental CSV writing (data appended after each page)
- Automatic page limit specification for testing

## Usage

### Parse Faculty Timetable
```bash
# Process entire faculty timetable PDF
python scripts/run_parser.py data/raw/FacultyCS.pdf

# Process first 5 pages only (for quick testing)
python scripts/run_parser.py data/raw/FacultyCS.pdf 5
```

### Parse Student Timetable
```bash
# Parser automatically detects student timetables
python scripts/run_parser.py data/raw/CTsp26.pdf
```

## Example Output

### Console Output
```
['Faculty Timetable Detected']
[1/5] Opening PDF (Faculty): data/raw/FacultyCS.pdf
      -> Found 65 page(s)
[2/5] Created CSV file: FacultyCS_20260305_052552.csv

--- Processing Page 1/65 ---
[3/5] Parsing grid structure (page 1)...
[4/5] Parsing faculty schedule (page 1)...
      -> 2 schedule records extracted from page 1
      -> Records appended to CSV

--- Processing Page 2/65 ---
...

[5/5] Processing complete!
      -> Total records across all pages: 285
      -> CSV file saved at: output/FacultyCS_20260305_052552.csv
```

### CSV Output Sample
```csv
teacher_name,semester,day,slot,time_start,time_end,course_name,course_credits,batch_code,room_code
Dr.Rehan Ashraf,Spring-2026,Monday,3,11:30,13:00,Machine Learning,,BCS-FA23-6B,CS-2
Dr.Rehan Ashraf,Spring-2026,Friday,4,13:30,15:00,Research Methodology,,RCS-FA25-2,SE-1
Dr.Aqeel Ur Rehman,Spring-2026,Monday,5,15:00,16:30,Public Key Cryptography,,RCS-SP25-3,CS-2
Dr.Muhammad Zahid Abbas,Spring-2026,Tuesday,4,13:30,15:00,Computer Networks,,BSE-FA24-4B,CS-5
```

## Implementation Details

### Faculty Cell Parser
- Extracts course name with optional credits
- Identifies batch codes (BCS-*, RCS-*, BSE-*)
- Extracts room codes (CS-*, SE-*, MS-*, etc.)
- Handles various formatting variations

### Faculty Normalizer
- Extracts teacher name from header metadata
- Converts grid data to FacultyScheduleRecord objects
- Extracts semester information
- Maps time slots to start/end times

### Timetable Detector
- Checks filename for keywords (faculty, teacher, instructor, student, batch, class)
- Scans first page content for identifying patterns
- Uses machine learning-friendly patterns for batch codes
- Defaults to student timetable if uncertain

## Results

Successfully processed FacultyCS.pdf:
- ✅ 65 faculty pages parsed
- ✅ 285 schedule records extracted
- ✅ 26KB CSV file generated
- ✅ All faculty names, courses, batches, and rooms parsed

## Architecture

The system now supports a flexible two-path parsing system:

```
PDF Input
    ↓
Type Detection (Detector)
    ↓
    ├─→ Student Path:
    │   ├─ extract_raw_table()
    │   ├─ parse_grid()
    │   ├─ normalize() → ScheduleRecord
    │   └─ CSV export
    │
    └─→ Faculty Path:
        ├─ extract_raw_table()
        ├─ parse_grid()
        ├─ normalize_faculty() → FacultyScheduleRecord
        └─ CSV export
    ↓
CSV Output + Database
```

## Files Modified/Created

**Created:**
- `src/parser/faculty_parser.py` - Faculty cell parsing logic
- `src/parser/faculty_normalizer.py` - Faculty data normalization
- `src/parser/timetable_detector.py` - Timetable type detection

**Modified:**
- `scripts/run_parser.py` - Enhanced to support both types with auto-detection
- `src/parser/pdf_extractor.py` - Added get_page_count() function

## Future Enhancements

1. Add support for other timetable types (e.g., classroom, lab schedules)
2. Improve course_credits extraction for faculty timetables
3. Add database schema for faculty schedules
4. Implement conflict detection (teacher/room double-booking)
5. Add HTML/JSON export formats in addition to CSV
