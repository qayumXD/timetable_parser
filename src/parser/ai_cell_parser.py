"""
LLM-based fallback cell parser using a locally running Ollama model.
Only called when the regex parser returns an uncertain result.
"""

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

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
def _call_ollama(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    """Send a non-streaming chat request to a local Ollama server."""
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": max_tokens,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ConnectionError(
            f"Could not reach Ollama at {OLLAMA_HOST}. "
            f"Make sure Ollama is running and model {OLLAMA_MODEL!r} is installed."
        ) from exc

    message = body.get("message", {})
    content = message.get("content")
    if not content:
        raise ValueError(f"Ollama returned no message content: {body}")
    return content.strip()


def ai_parse_cell(cell_text: str) -> Optional[dict]:
    """
    Uses LLM to extract subject, room_code, and instructor from ambiguous cell text.
    Returns a dict with keys: subject, room_code, instructor.
    Returns None if LLM fails or cell is empty.
    """
    if not cell_text or not cell_text.strip():
        return None

    prompt = USER_TEMPLATE.format(cell_text=cell_text.strip())
    raw_output = _call_ollama(SYSTEM_PROMPT, prompt, max_tokens=150)

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

    prompt = FACULTY_USER_TEMPLATE.format(cell_text=cell_text.strip())
    raw_output = _call_ollama(FACULTY_SYSTEM_PROMPT, prompt, max_tokens=180)
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
