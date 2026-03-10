import re
from dataclasses import dataclass
from typing import Optional


BATCH_PATTERN = re.compile(r'^[A-Z]{2,4}-[A-Z]{2}\d{2}-\d+[A-Z]?$', re.IGNORECASE)
ROOM_PATTERN = re.compile(
    r'^(?:'
    r'[A-Z]{1,4}(?:\s+LAB)?-\d+(?:\s*\(.*\))?'
    r'|[A-Z]{2,4}\s+LAB-\d+'
    r'|[A-Z]{2,4}\s*Lab'
    r'|DLD\s+Lab'
    r')$',
    re.IGNORECASE,
)


@dataclass
class FacultyCell:
    """Represents a parsed faculty timetable cell"""
    course_name: str
    course_credits: Optional[str]
    batch_code: str
    room_code: str


def parse_faculty_cell(cell_text: str) -> Optional[FacultyCell]:
    """
    Parses a faculty timetable cell.
    
    Format is typically:
    Course Name(Credits)
    Batch Code
    Room Code
    
    Example:
    Machine Learning Fundamentals(2Cr)
    BCS-FA23-6B
    CS-2
    """
    if not cell_text or not cell_text.strip():
        return None
    
    lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
    
    if len(lines) < 2:
        return None
    
    # Extract course name and credits
    course_line = lines[0]
    match = re.match(r'(.+?)\s*\(([^)]*)\)\s*$', course_line)
    if match:
        course_name = match.group(1).strip()
        course_credits = match.group(2).strip()
    else:
        course_name = course_line
        course_credits = None
    
    # Extract batch and room code lines.
    batch_code = "UNKNOWN"
    room_code = "UNKNOWN"
    
    for line in lines[1:]:
        if BATCH_PATTERN.match(line):
            batch_code = line
            continue
        if ROOM_PATTERN.match(line):
            room_code = line
    
    return FacultyCell(
        course_name=course_name,
        course_credits=course_credits,
        batch_code=batch_code,
        room_code=room_code
    )


def extract_faculty_name(header_text: str) -> str:
    """
    Extracts the faculty/teacher name from the header text.
    
    Examples:
    "Teacher Dr.Rehan Ashraf(CS)"
    "Faculty Dr. John Smith(CS)"
    """
    # Look for "Teacher" or "Faculty" keyword followed by a name
    match = re.search(r'(?:Teacher|Faculty)\s+(.+?)(?:\(|$)', header_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Try to find a pattern like "Dr. Something Name(Department)"
    match = re.search(r'(Dr\.?\s+[A-Za-z\s]+)\s*\(', header_text)
    if match:
        return match.group(1).strip()
    
    return "UNKNOWN"
