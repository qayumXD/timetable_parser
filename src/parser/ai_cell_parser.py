"""
LLM-based fallback cell parser using llama-cpp-python + Qwen2.5-1.5B-Instruct GGUF.
Only called when the regex parser returns an uncertain result.
"""

import json
import re
from pathlib import Path
from typing import Optional

# Lazy import — only load when needed
_llm = None

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"

SYSTEM_PROMPT = """You are a data extraction assistant for a university timetable system.
You will be given raw text from a single timetable cell. Extract exactly three fields:
- subject: the course/subject name only (no instructor, no room)
- room_code: the room or lab code (e.g. "CS-3", "SE LAB-1", "DLD Lab", "MS-8"). null if absent.
- instructor: the full instructor name including title if present (e.g. "Dr. Salman Iqbal", "Hamna Ashraf"). null if absent.

Respond ONLY with a valid JSON object. No explanation. No markdown. Just JSON.
Example output: {"subject": "Operating Systems", "room_code": "CS-2", "instructor": "Syed Ammar Yasir"}"""

USER_TEMPLATE = """Extract from this timetable cell text:

{cell_text}

JSON:"""

FACULTY_SYSTEM_PROMPT = """You are a data extraction assistant for faculty timetable cells.
Extract exactly these fields from ONE faculty timetable cell:
- course_name: full course title only
- course_credits: text inside credits parentheses such as "2Cr" or "2 Hrs."; null if absent
- batch_code: one batch code like "BCS-FA23-6B"; null if absent
- room_code: one room code like "CS-2", "SE-4", "MS-8", "DLD Lab", "CS-13 (Old CS)"; null if absent

Respond ONLY with valid JSON object. No markdown. No explanation.
Example:
{"course_name": "Machine Learning Fundamentals", "course_credits": "2Cr", "batch_code": "BCS-FA23-6B", "room_code": "CS-2"}
"""

FACULTY_USER_TEMPLATE = """Extract fields from this faculty timetable cell text:

{cell_text}

JSON:"""


def _get_llm():
    """Lazy-load the LLM on first use."""
    global _llm
    if _llm is None:
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python is not installed. Run: pip install llama-cpp-python"
            )
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run: huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF "
                "qwen2.5-1.5b-instruct-q4_k_m.gguf --local-dir models/"
            )
        print(f"[ai_cell_parser] Loading LLM from {MODEL_PATH} ...")
        _llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=512,
            n_threads=4,
            verbose=False,
        )
        print("[ai_cell_parser] LLM loaded.")
    return _llm


def ai_parse_cell(cell_text: str) -> Optional[dict]:
    """
    Uses LLM to extract subject, room_code, and instructor from ambiguous cell text.
    Returns a dict with keys: subject, room_code, instructor.
    Returns None if LLM fails or cell is empty.
    """
    if not cell_text or not cell_text.strip():
        return None

    llm = _get_llm()

    prompt = USER_TEMPLATE.format(cell_text=cell_text.strip())

    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=150,
        temperature=0.0,
        stop=["\n\n"],
    )

    raw_output = response["choices"][0]["message"]["content"].strip()

    # Strip any accidental markdown fences
    raw_output = re.sub(r"```json|```", "", raw_output).strip()

    try:
        result = json.loads(raw_output)
        return {
            "subject":    result.get("subject"),
            "room_code":  result.get("room_code"),
            "instructor": result.get("instructor"),
        }
    except json.JSONDecodeError:
        match = re.search(r'\{.*?\}', raw_output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        print(f"[ai_cell_parser] WARNING: Could not parse LLM output: {raw_output!r}")
        return None


def ai_parse_faculty_cell(cell_text: str) -> Optional[dict]:
    """
    Uses LLM to extract faculty cell fields.
    Returns dict with keys: course_name, course_credits, batch_code, room_code.
    Returns None if LLM fails or cell is empty.
    """
    if not cell_text or not cell_text.strip():
        return None

    llm = _get_llm()
    prompt = FACULTY_USER_TEMPLATE.format(cell_text=cell_text.strip())

    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": FACULTY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=180,
        temperature=0.0,
        stop=["\n\n"],
    )

    raw_output = response["choices"][0]["message"]["content"].strip()
    raw_output = re.sub(r"```json|```", "", raw_output).strip()

    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError:
        match = re.search(r'\{.*?\}', raw_output, re.DOTALL)
        if not match:
            print(f"[ai_cell_parser] WARNING: Could not parse LLM output: {raw_output!r}")
            return None
        try:
            result = json.loads(match.group(0))
        except json.JSONDecodeError:
            print(f"[ai_cell_parser] WARNING: Could not parse LLM output: {raw_output!r}")
            return None

    return {
        "course_name": result.get("course_name"),
        "course_credits": result.get("course_credits"),
        "batch_code": result.get("batch_code"),
        "room_code": result.get("room_code"),
    }
