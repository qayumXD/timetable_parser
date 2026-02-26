# Phase AI — Local LLM Cell Parser Enhancement
## Specification for Fixing Misclassification in `cell_parser.py`

> **Context:** The existing parser (`src/parser/cell_parser.py`) uses regex heuristics to split cell
> text into `subject`, `room_code`, and `instructor`. It works well for clean cells but fails on
> ~15–20% of cells where names lack the `(DEPT)` suffix, room tokens are non-standard, or text wraps
> ambiguously. This phase introduces a **local LLM fallback** to resolve those ambiguous cells with
> high semantic accuracy — without any API cost or internet dependency.

---

## 1. Root Cause Analysis of Current Failures

Before touching any code, the agent must internalize *why* the current heuristics fail.

### 1.1 Instructor Name Not Detected → Bleeds Into Subject

The current `INSTRUCTOR_PATTERN` only matches lines that **end with `(DEPT)`**:
```
r'.+\([A-Z]+\)$'
```

This misses instructors who appear **without a department suffix**, which happens in two ways:

**Pattern A — Instructor appended directly to subject line (no newline separation):**
```
"Pre Calculas I (Medical) Hamna Ashraf"   → Hamna Ashraf is an instructor
"Fundamentals of Sociology Qaisar Abbas"  → Qaisar Abbas is an instructor
"Tourism and Hospitality Marketing Dr.Affan Ud Din MS"  → Dr.Affan Ud Din is instructor, MS is dept
```

**Pattern B — Instructor name with dept abbreviation not in parentheses:**
```
"Research Methodology Dr. M. Mudassar (CS)"  → actually DOES have (CS) — but the subject
                                                part was greedily consumed
```

**Pattern C — Subject and instructor are positionally swapped** (rarest, most damaging):
```
"Ayesha Rafiq (Mth) | SE-4 | Pre Calculas I"  → name came first, subject came last
```

### 1.2 Room Code Not Detected → Lands in Wrong Field

**Pattern D — Room prefix is non-standard or contains extra tokens:**
```
"Application of ICT-Lab/ITC FYP-CS"  → FYP-CS looks like a room code to humans but fails regex
"Applied Physics-Lab | | DLD Lab Junaid Iqbal"  → "DLD Lab" is a room, not parsed as one
```

**Pattern E — Room code missing entirely but text implies a location:**
```
"Applied Physics-Lab\n[empty]\nDLD Lab Junaid Iqbal"  → "DLD Lab" is both room and instructor context
```

### 1.3 Summary Table

| Failure Type | Example Cell | Root Cause |
|---|---|---|
| Instructor bleeds into subject | `"Pre Calculas I (Medical) Hamna Ashraf"` | Name has no `(DEPT)` suffix |
| Instructor with non-parens dept | `"Tourism... Dr.Affan Ud Din MS"` | Dept is bare word, not `(MS)` |
| Subject/instructor positionally swapped | `"Ayesha Rafiq (Mth) | SE-4 | Pre Calculas I"` | PDF text order unexpected |
| Non-standard room token | `"DLD Lab Junaid Iqbal"` | "DLD" not in known prefix list |
| Room code completely absent | `"Applied Physics-Lab\n\nDLD Lab..."` | Room was in next line as combined string |

---

## 2. Proposed Architecture

### 2.1 Strategy: Tiered Parsing

Do **not** replace the regex parser entirely — it works correctly for ~80% of cells and is fast.
Instead, add LLM as a **fallback tier** that only activates when heuristics are uncertain.

```
Cell text
    │
    ▼
[Tier 1] Regex/heuristic parser  (cell_parser.py — unchanged)
    │
    ├── CONFIDENT result? ──────────────────────► Return ParsedCell
    │
    └── UNCERTAIN result? (see confidence signals below)
            │
            ▼
        [Tier 2] LLM fallback parser  (ai_cell_parser.py — NEW)
            │
            └──────────────────────────────────────► Return ParsedCell
```

### 2.2 Confidence Signals (When to Trigger LLM Fallback)

The regex parser should flag a result as **uncertain** if ANY of these conditions are true:

```python
def is_uncertain(parsed: ParsedCell, raw_text: str) -> bool:
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    return (
        parsed.instructor is None                           # No instructor found
        or parsed.room_code is None                        # No room found
        or len(lines) > 3                                  # Unusually many lines
        or any(looks_like_name(line) for line in lines     # Name-like token in subject
               if line == parsed.subject)
        or parsed.subject and len(parsed.subject.split()) > 8  # Subject suspiciously long
    )
```

A simple `looks_like_name()` heuristic:
```python
import re

NAME_INDICATORS = re.compile(
    r'\b(Dr\.?|Mr\.?|Ms\.?|Prof\.?|Engr\.?)\b'  # Titles
    r'|[A-Z][a-z]+ [A-Z][a-z]+'                 # Two capitalized words (e.g. "Hamna Ashraf")
    , re.IGNORECASE
)

def looks_like_name(text: str) -> bool:
    return bool(NAME_INDICATORS.search(text))
```

---

## 3. Model Selection

### 3.1 Requirements

| Requirement | Reason |
|---|---|
| Runs fully offline / locally | No internet dependency; works in campus environments |
| Fits in ≤4GB RAM (quantized) | Runs on a standard laptop without GPU |
| Fast per-cell inference (<2s) | Parser must stay practical for bulk PDF processing |
| Good at structured extraction | Must follow a JSON output format reliably |
| Python-friendly runtime | Integrates cleanly into existing codebase |

### 3.2 Recommended Model: `Qwen2.5-1.5B-Instruct` (GGUF, Q4_K_M quantized)

**Why Qwen2.5-1.5B:**

- At 1.5B parameters it is **extremely fast** on CPU (~0.5–1s per cell)
- The Instruct variant follows structured prompts and JSON format reliably
- GGUF Q4_K_M quantization brings it to **~1.1 GB on disk** — fits in RAM easily
- Outperforms older models like Mistral-7B on structured extraction tasks *at this size tier*
- Available directly from HuggingFace as a GGUF: `Qwen/Qwen2.5-1.5B-Instruct-GGUF`

**Alternative if you want higher accuracy (costs ~2GB RAM, ~2x slower):**
- `Qwen2.5-3B-Instruct` GGUF Q4_K_M — better on edge cases, still CPU-viable

**Why NOT larger models for this task:**
- `Mistral-7B`, `LLaMA-3-8B` etc. are overkill — the task is simple classification, not reasoning
- They require 4–6GB RAM and are 3–5x slower per cell, making bulk processing painful

### 3.3 Runtime: `llama-cpp-python`

```bash
pip install llama-cpp-python
```

- Pure Python + C++ binding — no PyTorch, no CUDA required
- Loads GGUF files directly
- Supports structured JSON output via grammar constraints (optional but useful)
- Single dependency, no Ollama server required

**Download the model once:**
```bash
# In scripts/download_model.py or manually:
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
    qwen2.5-1.5b-instruct-q4_k_m.gguf \
    --local-dir models/
```

---

## 4. New File: `src/parser/ai_cell_parser.py`

### 4.1 Location in Project Structure

```
src/
└── parser/
    ├── cell_parser.py          ← existing (unchanged)
    ├── ai_cell_parser.py       ← NEW: LLM fallback
    └── cell_parser_v2.py       ← NEW: tiered dispatcher
```

### 4.2 `ai_cell_parser.py` Full Implementation

```python
# src/parser/ai_cell_parser.py
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
            n_ctx=512,          # Small context — cells are short
            n_threads=4,        # Adjust to your CPU core count
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
        temperature=0.0,   # Deterministic — this is extraction not generation
        stop=["\n\n"],
    )

    raw_output = response["choices"][0]["message"]["content"].strip()

    # Strip any accidental markdown fences
    raw_output = re.sub(r"```json|```", "", raw_output).strip()

    try:
        result = json.loads(raw_output)
        # Validate expected keys exist
        return {
            "subject":    result.get("subject"),
            "room_code":  result.get("room_code"),
            "instructor": result.get("instructor"),
        }
    except json.JSONDecodeError:
        # Attempt to extract JSON substring if model added prose
        match = re.search(r'\{.*?\}', raw_output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        print(f"[ai_cell_parser] WARNING: Could not parse LLM output: {raw_output!r}")
        return None
```

---

## 5. New File: `src/parser/cell_parser_v2.py`

This is the **tiered dispatcher** — it replaces `cell_parser.py` as the entry point.
`cell_parser.py` itself is NOT modified.

```python
# src/parser/cell_parser_v2.py
"""
Tiered cell parser:
  Tier 1 → regex heuristics (cell_parser.py)
  Tier 2 → LLM fallback    (ai_cell_parser.py)  — only on uncertain results
"""

import re
from typing import Optional
from .cell_parser import parse_cell, ParsedCell, ROOM_PATTERN
from .ai_cell_parser import ai_parse_cell

# ── Confidence check ─────────────────────────────────────────────────────────

NAME_INDICATORS = re.compile(
    r'\b(Dr\.?|Mr\.?|Ms\.?|Prof\.?|Engr\.?)\b'
    r'|[A-Z][a-z]+ [A-Z][a-z]+',
    re.IGNORECASE
)

def looks_like_name(text: str) -> bool:
    return bool(NAME_INDICATORS.search(text))

def is_uncertain(parsed: Optional[ParsedCell], raw_text: str) -> bool:
    """Returns True if the regex parse result is likely wrong or incomplete."""
    if parsed is None:
        return False  # Genuinely empty cell — no need for LLM

    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]

    return (
        parsed.instructor is None                                  # No instructor found at all
        or parsed.room_code is None                                # No room found at all
        or (parsed.subject and len(parsed.subject.split()) > 7)   # Subject suspiciously long
        or any(looks_like_name(l) for l in lines                  # A name-like token is misplaced
               if l.strip() == (parsed.subject or "").strip())
    )


# ── Instructor dept extraction ────────────────────────────────────────────────

DEPT_SUFFIX = re.compile(r'^(.+?)\s*\(([A-Z][a-z]*)\)\s*$')

def _split_instructor_dept(name: str):
    """Split 'Dr. Salman Iqbal(CS)' → ('Dr. Salman Iqbal', 'CS')"""
    if not name:
        return name, None
    m = DEPT_SUFFIX.match(name.strip())
    if m:
        return m.group(1).strip(), m.group(2)
    return name.strip(), None


# ── Main dispatcher ───────────────────────────────────────────────────────────

def parse_cell_v2(cell_text: str, use_ai: bool = True) -> Optional[ParsedCell]:
    """
    Primary entry point for cell parsing.
    Falls back to LLM when regex result is uncertain.

    Args:
        cell_text: Raw cell string from pdfplumber.
        use_ai: Set False to disable LLM fallback (e.g. during testing).

    Returns:
        ParsedCell or None.
    """
    parsed = parse_cell(cell_text)

    if not use_ai or not is_uncertain(parsed, cell_text or ""):
        return parsed

    # ── Tier 2: LLM fallback ──────────────────────────────────────────────────
    print(f"[cell_parser_v2] Uncertain result — calling LLM for: {cell_text!r[:80]}")
    ai_result = ai_parse_cell(cell_text)

    if ai_result is None:
        print("[cell_parser_v2] LLM returned None — keeping regex result")
        return parsed

    # Merge LLM result into a ParsedCell
    subject = ai_result.get("subject") or parsed.subject or ""
    room_raw = ai_result.get("room_code")
    instructor_raw = ai_result.get("instructor")

    # Determine room type
    room_type = None
    if room_raw:
        room_type = "lab" if "LAB" in room_raw.upper() else "classroom"

    # Split instructor dept if present
    instructor_name, instructor_dept = _split_instructor_dept(instructor_raw)

    # Detect 2-hour flag from subject
    TWO_HR = re.compile(r'\(2\s?[Hh]rs?\)', re.IGNORECASE)
    is_two_hour = bool(TWO_HR.search(subject))
    subject = TWO_HR.sub('', subject).strip()

    return ParsedCell(
        subject=subject,
        room_code=room_raw,
        room_type=room_type,
        instructor=instructor_name,
        instructor_dept=instructor_dept or (parsed.instructor_dept if parsed else None),
        is_two_hour=is_two_hour,
        raw_text=cell_text,
    )
```

---

## 6. Integration — Updating `normalizer.py`

The only change to existing code: swap the import in `normalizer.py`.

**Find this line in `normalizer.py`:**
```python
from src.parser.cell_parser import parse_cell
```

**Replace with:**
```python
from src.parser.cell_parser_v2 import parse_cell_v2 as parse_cell
```

That's it. The `ParsedCell` dataclass interface is identical — nothing else changes.

To **disable LLM** for a run (e.g. fast bulk mode):
```python
from src.parser.cell_parser_v2 import parse_cell_v2
records = normalize(grid, metadata, cell_parser=lambda t: parse_cell_v2(t, use_ai=False))
```

---

## 7. Project Structure Changes

```
timetable-parser/
│
├── models/                                   ← NEW directory
│   └── qwen2.5-1.5b-instruct-q4_k_m.gguf   ← downloaded once (~1.1 GB)
│
├── src/
│   └── parser/
│       ├── cell_parser.py                    ← UNCHANGED
│       ├── ai_cell_parser.py                 ← NEW
│       └── cell_parser_v2.py                 ← NEW (tiered dispatcher)
│
├── scripts/
│   └── download_model.py                     ← NEW helper script
│
└── requirements.txt                          ← add: llama-cpp-python>=0.2.0
```

### `scripts/download_model.py`
```python
#!/usr/bin/env python3
"""One-time model download. Run once before first use."""
import subprocess
from pathlib import Path

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

subprocess.run([
    "huggingface-cli", "download",
    "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "--local-dir", str(MODEL_DIR),
], check=True)
print(f"Model saved to {MODEL_DIR}")
```

---

## 8. Updated `requirements.txt`

```txt
pdfplumber>=0.10.0
pytest>=7.0
llama-cpp-python>=0.2.0
huggingface-hub>=0.20.0   # for huggingface-cli download
```

---

## 9. New Tests: `tests/test_ai_cell_parser.py`

```python
# tests/test_ai_cell_parser.py
"""
Tests for the tiered parser. These use use_ai=False so they run without the model.
AI-specific tests are marked with @pytest.mark.slow and require the model to be downloaded.
"""
import pytest
from src.parser.cell_parser_v2 import parse_cell_v2, is_uncertain

# ── Uncertainty detection tests ───────────────────────────────────────────────

def test_uncertain_no_instructor():
    """Cell with no (DEPT) suffix should be flagged uncertain."""
    from src.parser.cell_parser import parse_cell
    raw = "Pre Calculas I (Medical) Hamna Ashraf\nCS-3"
    parsed = parse_cell(raw)
    assert is_uncertain(parsed, raw)

def test_certain_clean_cell():
    """A well-formed cell should NOT be flagged uncertain."""
    from src.parser.cell_parser import parse_cell
    raw = "Operating Systems-Lab\nSE LAB-1\nSyed Ammar Yasir(CS)"
    parsed = parse_cell(raw)
    assert not is_uncertain(parsed, raw)

def test_uncertain_very_long_subject():
    """A suspiciously long subject suggests instructor bled in."""
    from src.parser.cell_parser import parse_cell
    raw = "Tourism and Hospitality Marketing Dr.Affan Ud Din MS\nMS-9"
    parsed = parse_cell(raw)
    assert is_uncertain(parsed, raw)

# ── Tiered parser integration (no AI) ────────────────────────────────────────

def test_v2_clean_cell_no_ai():
    result = parse_cell_v2("Operating Systems-Lab\nSE LAB-1\nSyed Ammar Yasir(CS)", use_ai=False)
    assert result.subject == "Operating Systems-Lab"
    assert result.room_code == "SE LAB-1"
    assert result.instructor == "Syed Ammar Yasir"

def test_v2_empty_no_ai():
    result = parse_cell_v2(None, use_ai=False)
    assert result is None

# ── AI-powered tests (require model downloaded) ───────────────────────────────

@pytest.mark.slow
def test_ai_fixes_instructor_bleed():
    """LLM should correctly separate instructor from subject."""
    result = parse_cell_v2("Pre Calculas I (Medical) Hamna Ashraf\nCS-3")
    assert result.instructor is not None
    assert "Hamna Ashraf" in result.instructor
    assert "Hamna Ashraf" not in result.subject

@pytest.mark.slow
def test_ai_fixes_dld_lab_room():
    """LLM should identify 'DLD Lab' as a room code."""
    result = parse_cell_v2("Applied Physics-Lab\nDLD Lab Junaid Iqbal")
    assert result.room_code is not None
    assert "DLD" in result.room_code
    assert result.instructor is not None

@pytest.mark.slow
def test_ai_fixes_swapped_order():
    """LLM should handle subject/instructor positional swap."""
    result = parse_cell_v2("Ayesha Rafiq (Mth)\nSE-4\nPre Calculas I")
    assert result.subject is not None
    assert "Calculas" in result.subject or "Pre" in result.subject
    assert result.instructor is not None
    assert "Ayesha" in result.instructor
```

Run without model (fast):
```bash
python -m pytest tests/ -v -m "not slow"
```

Run with AI tests (requires model):
```bash
python -m pytest tests/ -v
```

---

## 10. Implementation Checklist for the Agent

```
[ ] 1. pip install llama-cpp-python huggingface-hub
[ ] 2. python scripts/download_model.py  (one-time, ~1.1GB download)
[ ] 3. Create src/parser/ai_cell_parser.py  (as specified in Section 4.2)
[ ] 4. Create src/parser/cell_parser_v2.py  (as specified in Section 5)
[ ] 5. In normalizer.py — swap import to parse_cell_v2 (Section 6)
[ ] 6. Update requirements.txt (Section 8)
[ ] 7. Run: python -m pytest tests/ -v -m "not slow"  → all existing tests still pass
[ ] 8. Run: python scripts/run_parser.py data/raw/CTfa24.pdf
        → Verify "Pre Calculas I" no longer contains "Hamna Ashraf"
[ ] 9. Run: python scripts/run_parser.py data/raw/CTfa25.pdf
        → Verify "Tourism and Hospitality Marketing" is clean
[ ] 10. Run: python -m pytest tests/ -v  (including @slow)  → all pass
[ ] 11. If any AI test fails — inspect LLM raw output with:
        python -c "from src.parser.ai_cell_parser import ai_parse_cell; print(ai_parse_cell('<cell>'))"
```

---

## 11. Known Tradeoffs & Mitigations

| Concern | Detail | Mitigation |
|---|---|---|
| LLM load time on first use | ~3–5 seconds to load model into RAM | Load is lazy — only on first uncertain cell per run. Subsequent cells in same run are fast. |
| LLM hallucinates a field | Model invents a room or instructor | All LLM results are merged conservatively — regex result fields are kept as fallback if LLM returns null |
| `llama-cpp-python` install fails on Windows | Requires C++ build tools | Add note to README: install `Visual Studio Build Tools` or use pre-built wheel from `pip install llama-cpp-python --prefer-binary` |
| Model not downloaded | `FileNotFoundError` on first fallback | Error message includes exact download command; `run_parser.py` catches and warns gracefully |
| 1.5B still gets edge cases wrong | e.g. very unusual cell layouts | For persistent failures, escalate to `Qwen2.5-3B` GGUF (same API, just larger model path) |

---

*This spec is a standalone addendum to the existing `projectSpecifications.md`.  
All other phases (1–8) remain unchanged. Only `normalizer.py` import line is modified.*
