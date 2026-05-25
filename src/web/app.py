from __future__ import annotations

import csv
import logging
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template_string, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = BASE_DIR / "data" / "raw" / "web_uploads"
RUN_PARSER = BASE_DIR / "scripts" / "run_parser.py"

ALLOWED_EXTENSIONS = {"pdf"}
MAX_PREVIEW_ROWS = 100
DAY_ORDER = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7}
FACULTY_COLUMNS = {"teacher_name", "semester", "day", "slot", "time_start", "time_end", "course_name", "batch_code", "room_code"}
STUDENT_COLUMNS = {"batch", "semester", "day", "slot", "time_start", "time_end", "subject", "room_code", "instructor_name"}


RUN_STATE: dict[str, object] = {
  "running": False,
  "started_at": None,
  "finished_at": None,
  "uploaded_file": "",
  "cmd": [],
  "log": "",
  "error": "",
  "latest_csv": "",
}
RUN_STATE_LOCK = threading.Lock()


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Timetable Parser</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --panel: #ffffff;
      --panel-soft: #f8fafc;
      --text: #111827;
      --muted: #5f6b7a;
      --subtle: #8a94a3;
      --accent: #0f766e;
      --accent-ink: #0b4f49;
      --border: #d8dee8;
      --border-strong: #c2cad6;
      --danger: #b42318;
      --warning: #9a3412;
      --success: #117a47;
      --shadow: 0 1px 2px rgba(17, 24, 39, 0.05);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }
    a {
      color: var(--accent-ink);
      text-decoration: none;
      font-weight: 600;
    }
    a:hover { text-decoration: underline; }
    .shell {
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }
    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 18px;
    }
    h1, h2, h3, p { margin: 0; }
    h1 {
      font-size: 1.55rem;
      line-height: 1.2;
      letter-spacing: 0;
    }
    h2 {
      font-size: 1rem;
      line-height: 1.25;
      letter-spacing: 0;
    }
    h3 {
      font-size: 0.92rem;
      line-height: 1.25;
    }
    .eyebrow {
      color: var(--subtle);
      font-size: 0.74rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }
    .lede {
      color: var(--muted);
      margin-top: 6px;
      max-width: 620px;
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 32px;
      padding: 6px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--panel);
      color: var(--muted);
      font-size: 0.84rem;
      font-weight: 700;
      white-space: nowrap;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--subtle);
    }
    .status-pill.is-running .status-dot { background: var(--warning); }
    .status-pill.is-complete .status-dot { background: var(--success); }
    .status-pill.is-error .status-dot { background: var(--danger); }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .panel-pad { padding: 16px; }
    .dashboard-grid {
      display: grid;
      grid-template-columns: minmax(320px, 0.9fr) minmax(0, 1.1fr);
      gap: 16px;
      align-items: start;
      margin-bottom: 16px;
    }
    .section-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }
    .section-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .muted {
      color: var(--muted);
      font-size: 0.92rem;
    }
    .field {
      display: grid;
      gap: 7px;
      margin-top: 14px;
    }
    .field-label {
      display: block;
      font-size: 0.86rem;
      font-weight: 700;
    }
    .native-file {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      clip-path: inset(50%);
    }
    .file-drop {
      display: grid;
      gap: 3px;
      width: 100%;
      min-height: 72px;
      padding: 14px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel-soft);
      cursor: pointer;
    }
    .file-drop:hover { border-color: var(--border-strong); }
    .file-title {
      font-weight: 800;
      color: var(--accent-ink);
    }
    .file-name {
      color: var(--muted);
      font-size: 0.9rem;
      overflow-wrap: anywhere;
    }
    .scope-group {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .scope-option {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 42px;
      padding: 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      font-size: 0.9rem;
      font-weight: 700;
      cursor: pointer;
    }
    .scope-option:has(input:checked) {
      border-color: rgba(15, 118, 110, 0.5);
      background: #eef8f6;
      color: var(--accent-ink);
    }
    .scope-option input {
      width: auto;
      margin: 0;
      accent-color: var(--accent);
    }
    .number-input {
      width: 100%;
      min-height: 42px;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
    }
    .number-input:disabled {
      background: #eef2f6;
      color: var(--subtle);
      cursor: not-allowed;
    }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid transparent;
      font: inherit;
      font-size: 0.92rem;
      font-weight: 800;
      cursor: pointer;
      text-decoration: none;
    }
    .button:hover { text-decoration: none; }
    .button-primary {
      width: 100%;
      margin-top: 16px;
      border: 0;
      background: var(--accent);
      color: #fff;
    }
    .button-secondary {
      border-color: var(--border-strong);
      background: var(--panel);
      color: var(--text);
    }
    .button-link {
      min-height: 34px;
      padding: 6px 8px;
      color: var(--accent-ink);
      background: transparent;
      border-color: transparent;
      font-weight: 800;
    }
    .button:disabled {
      opacity: 0.6;
      cursor: wait;
    }
    .alert {
      padding: 11px 12px;
      border-radius: 8px;
      margin-bottom: 12px;
      border: 1px solid var(--border);
      background: var(--panel);
      color: var(--muted);
      font-size: 0.92rem;
    }
    .alert-error {
      border-color: #f2b8b5;
      background: #fff5f5;
      color: var(--danger);
    }
    .alert-success {
      border-color: #b8e2ca;
      background: #f0faf4;
      color: var(--success);
    }
    .alert-warning {
      border-color: #fed7aa;
      background: #fff7ed;
      color: var(--warning);
    }
    .table-scroll {
      width: 100%;
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 8px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }
    th, td {
      border-bottom: 1px solid var(--border);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background: #eef2f6;
      color: #233044;
      font-size: 0.78rem;
      font-weight: 800;
      white-space: nowrap;
    }
    tr:last-child td { border-bottom: 0; }
    .preview-table { min-width: 820px; }
    .raw-table { min-width: 980px; }
    .output-list {
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }
    .output-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 11px 12px;
      border-bottom: 1px solid var(--border);
    }
    .output-item:last-child { border-bottom: 0; }
    .output-item.is-selected { background: #f0faf8; }
    .output-main {
      min-width: 0;
    }
    .output-name {
      display: block;
      color: var(--text);
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .output-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 5px;
      color: var(--muted);
      font-size: 0.84rem;
    }
    .output-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    .nowrap { white-space: nowrap; }
    .type-chip,
    .tag,
    .slot-badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 7px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--panel-soft);
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 800;
      white-space: nowrap;
    }
    .tag {
      margin-left: 8px;
      color: var(--accent-ink);
      border-color: rgba(15, 118, 110, 0.25);
      background: #eef8f6;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 14px 0;
    }
    .metric {
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--panel-soft);
    }
    .metric span {
      display: block;
      color: var(--subtle);
      font-size: 0.74rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .metric strong {
      display: block;
      margin-top: 4px;
      color: var(--text);
      font-size: 0.94rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .course-name {
      font-weight: 800;
      color: var(--text);
    }
    .empty-state {
      padding: 22px 16px;
      text-align: center;
      color: var(--muted);
    }
    .preview-panel {
      margin-bottom: 16px;
    }
    .raw-preview,
    .log-panel {
      margin-top: 14px;
    }
    details summary {
      cursor: pointer;
      color: var(--accent-ink);
      font-weight: 800;
      margin-bottom: 10px;
    }
    .mono {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.82rem;
      line-height: 1.5;
      background: #111827;
      color: #e2e8f0;
      padding: 12px;
      border-radius: 8px;
      max-height: 320px;
      overflow: auto;
    }
    .mobile-only { display: none; }
    @media (max-width: 900px) {
      .shell { padding: 20px 16px 32px; }
      .page-header { display: grid; }
      .dashboard-grid { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 560px) {
      .shell { padding: 18px 14px 28px; }
      .scope-group { grid-template-columns: 1fr; }
      .section-head { display: grid; }
      .metrics { grid-template-columns: 1fr; }
      h1 { font-size: 1.35rem; }
      .panel-pad { padding: 14px; }
      .desktop-only { display: none; }
      .mobile-only { display: inline; }
      .output-item {
        align-items: start;
        display: grid;
      }
      .output-name {
        white-space: normal;
        overflow-wrap: anywhere;
      }
      .output-actions {
        justify-content: start;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    {% set status_class = 'is-running' if run_state.running else ('is-error' if run_state.error else ('is-complete' if run_state.finished_at else 'is-idle')) %}
    {% set status_text = 'Running' if run_state.running else ('Failed' if run_state.error else ('Completed' if run_state.finished_at else 'Idle')) %}

    <header class="page-header">
      <div>
        <div class="eyebrow">Timetable operations</div>
        <h1>Timetable Parser</h1>
        <p class="lede">COMSATS timetable PDF to structured CSV.</p>
      </div>
      <div class="status-pill {{ status_class }}">
        <span class="status-dot" aria-hidden="true"></span>
        {{ status_text }}
      </div>
    </header>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for m in messages %}
          <div class="alert alert-error">{{ m }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    {% if run_state.running %}
      <div class="alert alert-warning">Parser is running for {{ run_state.uploaded_file }}.</div>
    {% elif run_state.finished_at and not run_state.error %}
      <div class="alert alert-success">Last parser run completed at {{ run_state.finished_at }}.</div>
    {% elif run_state.error %}
      <div class="alert alert-error">Last parser run failed: {{ run_state.error }}</div>
    {% endif %}

    <div class="dashboard-grid">
      <section class="panel panel-pad">
        <div class="section-head">
          <div>
            <div class="eyebrow">Input</div>
            <h2>Parse New PDF</h2>
          </div>
        </div>
        <form method="post" action="{{ url_for('parse_pdf') }}" enctype="multipart/form-data">
          <div class="field">
            <label class="field-label" for="pdf_file">PDF File</label>
            <label class="file-drop" for="pdf_file">
              <span class="file-title">Choose PDF</span>
              <span class="file-name" id="file-name">No file selected</span>
            </label>
            <input class="native-file" id="pdf_file" type="file" name="pdf_file" accept="application/pdf" required>
          </div>

          <div class="field">
            <span class="field-label">Parse Scope</span>
            <div class="scope-group">
              <label class="scope-option">
              <input type="radio" name="page_mode" value="all" checked>
                <span>All pages</span>
              </label>
              <label class="scope-option">
              <input type="radio" name="page_mode" value="specific">
                <span>Specific pages</span>
              </label>
            </div>
          </div>

          <div class="field" id="page-count-field">
            <label class="field-label" for="max_pages">Pages to Parse</label>
            <input class="number-input" type="number" id="max_pages" name="max_pages" min="1" placeholder="Enter page count" disabled>
          </div>

          <button class="button button-primary" type="submit" {% if run_state.running %}disabled{% endif %}>
            {% if run_state.running %}Parser Running{% else %}Run Parser{% endif %}
          </button>
        </form>
      </section>

      <section class="panel panel-pad">
        <div class="section-head">
          <div>
            <div class="eyebrow">Output</div>
            <h2>Recent CSV Outputs</h2>
          </div>
        </div>
        {% if csv_files %}
          <div class="output-list">
            {% for item in csv_files %}
              <div class="output-item {% if item.name == selected_preview %}is-selected{% endif %}">
                <div class="output-main">
                  <span class="output-name" title="{{ item.name }}">{{ item.name }}</span>
                  <div class="output-meta">
                    <span class="type-chip">{{ item.kind }}</span>
                    <span>{{ item.rows }} rows</span>
                    <span>{{ item.updated }}</span>
                  </div>
                </div>
                <div class="output-actions">
                  <a class="button button-link" href="{{ url_for('index', preview=item.name) }}">Preview</a>
                  <a class="button button-link" href="{{ url_for('download_csv', filename=item.name) }}">Download</a>
                </div>
              </div>
            {% endfor %}
          </div>
        {% else %}
          <div class="empty-state">No CSV files found in output/.</div>
        {% endif %}
      </section>
    </div>

    {% if selected_preview %}
      <section class="panel panel-pad preview-panel">
        <div class="section-head">
          <div>
            <div class="eyebrow">Selected output</div>
            <h2>{{ selected_preview }}</h2>
            {% if preview_header %}
              <p class="muted">Showing {{ preview_rows|length }} of {{ preview_total_rows }} rows.</p>
            {% endif %}
          </div>
          <div class="section-actions">
            <a class="button button-secondary" href="{{ url_for('download_csv', filename=selected_preview) }}">Download CSV</a>
          </div>
        </div>
        {% if preview_header %}
          <div class="metrics">
            <div class="metric">
              <span>Type</span>
              <strong>{{ preview_model.kind }}</strong>
            </div>
            <div class="metric">
              <span>{{ preview_model.primary_label }}</span>
              <strong title="{{ preview_model.primary_value }}">{{ preview_model.primary_value }}</strong>
            </div>
            <div class="metric">
              <span>Semester</span>
              <strong>{{ preview_model.semester }}</strong>
            </div>
            <div class="metric">
              <span>Records</span>
              <strong>{{ preview_total_rows }}</strong>
            </div>
          </div>

          {% if preview_model.schedule_rows %}
            <div class="table-scroll">
              <table class="preview-table">
                <thead>
                  <tr>
                    <th>Day</th>
                    <th>Slot</th>
                    <th>Time</th>
                    <th>Course</th>
                    <th>{{ preview_model.secondary_label }}</th>
                    <th>Room</th>
                  </tr>
                </thead>
                <tbody>
                  {% for record in preview_model.schedule_rows %}
                    {% set course_name = record[preview_model.course_key] %}
                    <tr>
                      <td class="nowrap">{{ record.day }}</td>
                      <td><span class="slot-badge">Slot {{ record.slot }}</span></td>
                      <td class="nowrap">{{ record.time_start }}-{{ record.time_end }}</td>
                      <td>
                        <span class="course-name">{{ course_name }}</span>
                        {% if 'lab' in course_name|lower %}
                          <span class="tag">Lab</span>
                        {% endif %}
                      </td>
                      <td>{{ record[preview_model.secondary_key] }}</td>
                      <td class="nowrap">{{ record.room_code }}</td>
                    </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          {% else %}
            <div class="empty-state">This CSV does not match the known timetable columns.</div>
          {% endif %}

          <details class="raw-preview">
            <summary>Raw CSV rows</summary>
            <div class="table-scroll">
              <table class="raw-table">
                <thead>
                  <tr>
                    {% for h in preview_header %}
                      <th>{{ h }}</th>
                    {% endfor %}
                  </tr>
                </thead>
                <tbody>
                  {% for row in preview_rows %}
                    <tr>
                      {% for c in row %}
                        <td>{{ c }}</td>
                      {% endfor %}
                    </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </details>
        {% else %}
          <div class="empty-state">Could not load preview.</div>
        {% endif %}
      </section>
    {% else %}
      <section class="panel panel-pad preview-panel">
        <div class="empty-state">No output selected.</div>
      </section>
    {% endif %}

    {% if run_log %}
      <section class="panel panel-pad">
        <details class="log-panel" {% if run_state.error %}open{% endif %}>
          <summary>Last Parser Run Log</summary>
          <div class="mono" id="run-log">{{ run_log }}</div>
        </details>
      </section>
    {% endif %}
  </main>
  <script>
    (function () {
      const fileInput = document.getElementById('pdf_file');
      const fileName = document.getElementById('file-name');
      const modeInputs = document.querySelectorAll('input[name="page_mode"]');
      const maxPagesInput = document.getElementById('max_pages');

      if (fileInput && fileName) {
        fileInput.addEventListener('change', () => {
          fileName.textContent = fileInput.files && fileInput.files.length
            ? fileInput.files[0].name
            : 'No file selected';
        });
      }

      function syncPageInput() {
        const selected = document.querySelector('input[name="page_mode"]:checked');
        const specific = selected && selected.value === 'specific';
        maxPagesInput.disabled = !specific;
        maxPagesInput.required = specific;
        if (!specific) {
          maxPagesInput.value = '';
        }
      }

      modeInputs.forEach((input) => input.addEventListener('change', syncPageInput));
      syncPageInput();

      const pollEnabled = {{ 'true' if run_state.running else 'false' }};
      if (pollEnabled) {
        setInterval(async () => {
          try {
            const resp = await fetch('{{ url_for('parse_status') }}', { cache: 'no-store' });
            if (!resp.ok) return;
            const data = await resp.json();
            if (!data.running) {
              const url = new URL(window.location.href);
              if (data.latest_csv) {
                url.searchParams.set('preview', data.latest_csv);
              }
              window.location.href = url.toString();
            }
          } catch (e) {
            // Ignore transient polling errors and retry.
          }
        }, 3000);
      }
    })();
  </script>
</body>
</html>
"""


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _resolve_output_csv(filename: str) -> Path | None:
    try:
        output_root = OUTPUT_DIR.resolve()
        path = (OUTPUT_DIR / filename).resolve()
        path.relative_to(output_root)
    except (OSError, ValueError):
        return None

    if not path.exists() or path.suffix.lower() != ".csv":
        return None
    return path


def _detect_csv_kind(header: list[str]) -> str:
    columns = set(header)
    if FACULTY_COLUMNS.issubset(columns):
        return "Faculty"
    if STUDENT_COLUMNS.issubset(columns):
        return "Student"
    return "CSV"


def _read_csv_summary(path: Path) -> tuple[list[str], int]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            rows = sum(1 for _ in reader)
            return header, rows
    except OSError:
        return [], 0


def _list_csv_files() -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(OUTPUT_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    items: list[dict] = []
    for path in files[:20]:
        header, rows = _read_csv_summary(path)
        items.append(
            {
                "name": path.name,
                "kind": _detect_csv_kind(header),
                "rows": rows,
                "updated": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return items


def _preview_csv(filename: str) -> tuple[list[str], list[list[str]], int]:
    path = _resolve_output_csv(filename)
    if path is None:
        return [], [], 0

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            rows: list[list[str]] = []
            total_rows = 0
            for idx, row in enumerate(reader):
                total_rows += 1
                if idx < MAX_PREVIEW_ROWS:
                    rows.append(row)
            return header, rows, total_rows
    except OSError:
        return [], [], 0


def _row_dicts(header: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for row in rows:
        records.append({name: row[idx] if idx < len(row) else "" for idx, name in enumerate(header)})
    return records


def _first_value(records: list[dict[str, str]], key: str, fallback: str = "Unknown") -> str:
    for record in records:
        value = (record.get(key) or "").strip()
        if value:
            return value
    return fallback


def _slot_number(record: dict[str, str]) -> int:
    try:
        return int(record.get("slot", ""))
    except ValueError:
        return 99


def _schedule_sort_key(record: dict[str, str]) -> tuple[int, int, str]:
    return (
        DAY_ORDER.get(record.get("day", ""), 99),
        _slot_number(record),
        record.get("time_start", ""),
    )


def _preview_model(filename: str, header: list[str], rows: list[list[str]], total_rows: int) -> dict[str, object]:
    kind = _detect_csv_kind(header)
    records = _row_dicts(header, rows)

    model: dict[str, object] = {
        "kind": kind,
        "primary_label": "File",
        "primary_value": filename,
        "secondary_label": "Related",
        "secondary_key": "",
        "course_key": "",
        "semester": _first_value(records, "semester"),
        "row_count": total_rows,
        "schedule_rows": [],
    }

    if kind == "Faculty":
        model.update(
            {
                "primary_label": "Teacher",
                "primary_value": _first_value(records, "teacher_name"),
                "secondary_label": "Batch",
                "secondary_key": "batch_code",
                "course_key": "course_name",
                "schedule_rows": sorted(records, key=_schedule_sort_key),
            }
        )
    elif kind == "Student":
        model.update(
            {
                "primary_label": "Batch",
                "primary_value": _first_value(records, "batch"),
                "secondary_label": "Instructor",
                "secondary_key": "instructor_name",
                "course_key": "subject",
                "schedule_rows": sorted(records, key=_schedule_sort_key),
            }
        )

    return model


def _snapshot_state() -> dict[str, object]:
    with RUN_STATE_LOCK:
        return dict(RUN_STATE)
 
 
def _run_parser_in_background(app: Flask, cmd: list[str], uploaded_file: str) -> None:
    with app.app_context():
        app.logger.info("Starting parser run for %s", uploaded_file)
        before = {p.name for p in OUTPUT_DIR.glob("*.csv")}
 
        try:
            result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
            after = sorted(OUTPUT_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
 
            log = ((result.stdout or "") + ("\n" + result.stderr if result.stderr else "")).strip()[-12000:]
            newest_path = next((p for p in after if p.name not in before), after[0] if after else None)
 
            with RUN_STATE_LOCK:
                RUN_STATE["running"] = False
                RUN_STATE["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                RUN_STATE["log"] = log
                RUN_STATE["latest_csv"] = newest_path.name if newest_path is not None else ""
                RUN_STATE["error"] = "" if result.returncode == 0 else f"Parser failed (exit code {result.returncode})"
 
            if result.returncode == 0:
                app.logger.info("Parser run completed for %s", uploaded_file)
            else:
                app.logger.error("Parser run failed for %s with exit code %s", uploaded_file, result.returncode)
        except Exception as exc:
            with RUN_STATE_LOCK:
                RUN_STATE["running"] = False
                RUN_STATE["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                RUN_STATE["error"] = f"Parser crashed: {exc}"
                RUN_STATE["log"] = str(exc)
            app.logger.exception("Unexpected error while running parser")
 
 
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "timetable-parser-dev"
 
    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
 
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
 
    @app.before_request
    def _log_request_start():
        request._start_time = time.perf_counter()  # type: ignore[attr-defined]
        app.logger.info("HTTP %s %s from %s", request.method, request.path, request.remote_addr)
 
    @app.after_request
    def _log_request_end(response):
        start = getattr(request, "_start_time", None)
        if start is not None:
            elapsed_ms = (time.perf_counter() - start) * 1000
            app.logger.info("HTTP %s %s -> %s in %.1fms", request.method, request.path, response.status_code, elapsed_ms)
        return response
 
    @app.get("/")
    def index():
        preview_name = request.args.get("preview", "")
        header: list[str] = []
        rows: list[list[str]] = []
        total_preview_rows = 0
        preview_data: dict[str, object] = _preview_model("", header, rows, total_preview_rows)
        if preview_name:
            header, rows, total_preview_rows = _preview_csv(preview_name)
            preview_data = _preview_model(preview_name, header, rows, total_preview_rows)
 
        return render_template_string(
            HTML_TEMPLATE,
            csv_files=_list_csv_files(),
            selected_preview=preview_name,
            preview_header=header,
            preview_rows=rows,
            preview_total_rows=total_preview_rows,
            preview_model=preview_data,
            preview_limit=MAX_PREVIEW_ROWS,
            run_log=_snapshot_state().get("log", ""),
            run_state=_snapshot_state(),
        )
 
    @app.post("/parse")
    def parse_pdf():
        with RUN_STATE_LOCK:
            if bool(RUN_STATE["running"]):
                flash("Parser is already running. Please wait for it to finish.")
                return redirect(url_for("index"))
 
        file = request.files.get("pdf_file")
        page_mode = (request.form.get("page_mode") or "all").strip().lower()
        max_pages_raw = (request.form.get("max_pages") or "").strip()
 
        if file is None or file.filename == "":
            flash("Please select a PDF file.")
            return redirect(url_for("index"))
 
        if not _allowed(file.filename):
            flash("Only .pdf files are allowed.")
            return redirect(url_for("index"))
 
        filename = secure_filename(file.filename)
        if not filename:
            flash("Invalid filename.")
            return redirect(url_for("index"))
 
        saved_path = UPLOAD_DIR / filename
        file.save(saved_path)
 
        cmd = [sys.executable, str(RUN_PARSER), str(saved_path)]
        if page_mode == "specific":
            if not max_pages_raw.isdigit() or int(max_pages_raw) < 1:
                flash("Max pages must be a positive integer.")
                return redirect(url_for("index"))
            cmd.append(max_pages_raw)
 
        with RUN_STATE_LOCK:
            RUN_STATE["running"] = True
            RUN_STATE["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            RUN_STATE["finished_at"] = None
            RUN_STATE["uploaded_file"] = filename
            RUN_STATE["cmd"] = cmd
            RUN_STATE["log"] = ""
            RUN_STATE["error"] = ""
            RUN_STATE["latest_csv"] = ""
 
        worker = threading.Thread(target=_run_parser_in_background, args=(app, cmd, filename), daemon=True)
        worker.start()
 
        flash("Parser started. You can stay on this page; it will refresh when complete.")
        return redirect(url_for("index"))
 
    @app.get("/parse-status")
    def parse_status():
        state = _snapshot_state()
        return jsonify(
            {
                "running": bool(state.get("running")),
                "started_at": state.get("started_at"),
                "finished_at": state.get("finished_at"),
                "error": state.get("error", ""),
                "latest_csv": state.get("latest_csv", ""),
            }
        )
 
    @app.get("/download/<path:filename>")
    def download_csv(filename: str):
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
 
    return app
