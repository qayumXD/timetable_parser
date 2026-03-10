import re
from pathlib import Path


def detect_timetable_type(pdf_path: str) -> str:
    """
    Detects whether the PDF is a student or faculty timetable.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        "faculty" or "student"
    """
    import pdfplumber
    
    pdf_name = Path(pdf_path).name.lower()
    
    # Check filename for indicators
    if any(keyword in pdf_name for keyword in ['faculty', 'teacher', 'instructor']):
        return "faculty"
    
    if any(keyword in pdf_name for keyword in ['student', 'batch', 'class']):
        return "student"
    
    # Check content of first page
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                first_page_text = pdf.pages[0].extract_text() or ""
                
                # Faculty indicators
                if re.search(r'Teacher\s+Dr\.', first_page_text, re.IGNORECASE):
                    return "faculty"
                if re.search(r'Faculty.*?Name', first_page_text, re.IGNORECASE):
                    return "faculty"
                
                # Student indicators
                if re.search(r'BCS-[A-Z]{2}\d{2}-', first_page_text):
                    return "student"
                if re.search(r'Batch.*?\d{4}', first_page_text):
                    return "student"
    except Exception:
        pass
    
    # Default to student
    return "student"
