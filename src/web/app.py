from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template_string, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = BASE_DIR / "data" / "raw" / "web_uploads"
RUN_PARSER = BASE_DIR / "scripts" / "run_parser.py"

ALLOWED_EXTENSIONS = {"pdf"}
MAX_PREVIEW_ROWS = 100


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Timetable Parser</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1e293b;
      --muted: #64748b;
      --accent: #0f766e;
      --border: #dbe2ea;
      --warn: #b91c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at top right, #e2f3f1, var(--bg) 40%);
      color: var(--text);
      font-family: "Segoe UI", Tahoma, sans-serif;
    }
    .wrap {
      max-width: 1080px;
      margin: 24px auto;
      padding: 0 16px 32px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 14px;
    }
    h1, h2 { margin: 0 0 12px; }
    h1 { font-size: 1.35rem; }
    h2 { font-size: 1rem; }
    .muted { color: var(--muted); }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 14px;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
    }
    label { display: block; margin: 8px 0 6px; font-weight: 600; }
    input, button {
      width: 100%;
      padding: 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 0.95rem;
    }
    button {
      margin-top: 10px;
      border: 0;
      background: var(--accent);
      color: #fff;
      cursor: pointer;
      font-weight: 700;
    }
    .flash {
      padding: 10px;
      border-radius: 8px;
      margin-bottom: 10px;
      border: 1px solid #f2d0d0;
      background: #fff1f1;
      color: var(--warn);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.86rem;
      overflow: auto;
    }
    th, td {
      border: 1px solid var(--border);
      padding: 6px;
      text-align: left;
      vertical-align: top;
    }
    th { background: #f0f5f9; }
    .mono {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.82rem;
      background: #0f172a;
      color: #e2e8f0;
      padding: 10px;
      border-radius: 8px;
      max-height: 320px;
      overflow: auto;
    }
    .link-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .radio-group {
      display: flex;
      gap: 14px;
      margin: 10px 0 6px;
      flex-wrap: wrap;
    }
    .radio-item {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.92rem;
      color: var(--text);
    }
    .radio-item input {
      width: auto;
      padding: 0;
      margin: 0;
    }
    input:disabled {
      background: #f1f5f9;
      color: #64748b;
      cursor: not-allowed;
    }
    a { color: #0f766e; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Timetable Parser Web UI</h1>
      <div class="muted">Upload a PDF, run parser, and inspect/download generated CSV.</div>
    </div>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for m in messages %}
          <div class="flash">{{ m }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="grid">
      <div class="card">
        <h2>Parse New PDF</h2>
        <form method="post" action="{{ url_for('parse_pdf') }}" enctype="multipart/form-data">
          <label>PDF File</label>
          <input type="file" name="pdf_file" accept="application/pdf" required>

          <label>Parse Scope</label>
          <div class="radio-group">
            <label class="radio-item">
              <input type="radio" name="page_mode" value="all" checked>
              All pages
            </label>
            <label class="radio-item">
              <input type="radio" name="page_mode" value="specific">
              Specific number of pages
            </label>
          </div>

          <label>Pages to Parse</label>
          <input type="number" id="max_pages" name="max_pages" min="1" placeholder="Enter page count" disabled>

          <button type="submit">Run Parser</button>
        </form>
      </div>

      <div class="card">
        <h2>Recent CSV Outputs</h2>
        {% if csv_files %}
          <table>
            <thead>
              <tr><th>File</th><th>Rows</th><th>Updated</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {% for item in csv_files %}
              <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.rows }}</td>
                <td>{{ item.updated }}</td>
                <td>
                  <div class="link-row">
                    <a href="{{ url_for('download_csv', filename=item.name) }}">Download</a>
                    <a href="{{ url_for('index', preview=item.name) }}">Preview</a>
                  </div>
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        {% else %}
          <div class="muted">No CSV files found in output/.</div>
        {% endif %}
      </div>
    </div>

    {% if selected_preview %}
      <div class="card">
        <h2>CSV Preview: {{ selected_preview }}</h2>
        {% if preview_header %}
          <div class="muted">Showing {{ preview_rows|length }} of {{ preview_total_rows }} rows. Use Download for full file.</div>
          <br />
          <table>
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
        {% else %}
          <div class="muted">Could not load preview.</div>
        {% endif %}
      </div>
    {% endif %}

    {% if run_log %}
      <div class="card">
        <h2>Last Parser Run Log</h2>
        <div class="mono">{{ run_log }}</div>
      </div>
    {% endif %}
  </div>
  <script>
    (function () {
      const modeInputs = document.querySelectorAll('input[name="page_mode"]');
      const maxPagesInput = document.getElementById('max_pages');

      function syncPageInput() {
        const selected = document.querySelector('input[name="page_mode"]:checked');
        const specific = selected && selected.value === 'specific';
        maxPagesInput.disabled = !specific;
        if (specific) {
          maxPagesInput.required = true;
        } else {
          maxPagesInput.required = false;
          maxPagesInput.value = '';
        }
      }

      modeInputs.forEach((input) => input.addEventListener('change', syncPageInput));
      syncPageInput();
    })();
  </script>
</body>
</html>
"""


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _list_csv_files() -> list[dict]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(OUTPUT_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    items: list[dict] = []
    for path in files[:20]:
        rows = 0
        try:
            with path.open("r", encoding="utf-8", newline="") as f:
                rows = max(sum(1 for _ in f) - 1, 0)
        except OSError:
            rows = 0
        items.append(
            {
                "name": path.name,
                "rows": rows,
                "updated": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return items


def _preview_csv(filename: str) -> tuple[list[str], list[list[str]], int]:
    path = OUTPUT_DIR / filename
    if not path.exists() or path.suffix.lower() != ".csv":
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


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "timetable-parser-dev"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        preview_name = request.args.get("preview", "")
        header: list[str] = []
        rows: list[list[str]] = []
        total_preview_rows = 0
        if preview_name:
            header, rows, total_preview_rows = _preview_csv(preview_name)

        return render_template_string(
            HTML_TEMPLATE,
            csv_files=_list_csv_files(),
            selected_preview=preview_name,
            preview_header=header,
            preview_rows=rows,
            preview_total_rows=total_preview_rows,
            preview_limit=MAX_PREVIEW_ROWS,
            run_log=request.args.get("log", ""),
        )

    @app.post("/parse")
    def parse_pdf():
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

        before = {p.name for p in OUTPUT_DIR.glob("*.csv")}
        result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
        after = sorted(OUTPUT_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)

        log = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        log = log.strip()[-8000:]

        if result.returncode != 0:
            flash(f"Parser failed (exit code {result.returncode}).")
            return redirect(url_for("index", log=log))

        newest_path = next((p for p in after if p.name not in before), after[0] if after else None)
        flash("Parsing completed successfully.")
        if newest_path is not None:
            return redirect(url_for("index", preview=newest_path.name, log=log))
        return redirect(url_for("index", log=log))

    @app.get("/download/<path:filename>")
    def download_csv(filename: str):
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

    return app
