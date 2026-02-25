import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "timetable.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)


def insert_schedule_records(records: list):
    """Upsert all ScheduleRecord objects into DB."""
    with get_connection() as conn:
        for r in records:
            conn.execute(
                "INSERT OR IGNORE INTO batches(code, semester) VALUES (?,?)",
                (r.batch, r.semester),
            )
            batch_id = conn.execute(
                "SELECT id FROM batches WHERE code=?",
                (r.batch,),
            ).fetchone()[0]

            instructor_id = None
            if r.instructor_name:
                conn.execute(
                    "INSERT OR IGNORE INTO instructors(name, department) VALUES(?,?)",
                    (r.instructor_name, r.instructor_dept),
                )
                instructor_id = conn.execute(
                    "SELECT id FROM instructors WHERE name=? AND department=?",
                    (r.instructor_name, r.instructor_dept),
                ).fetchone()[0]

            room_id = None
            if r.room_code:
                conn.execute(
                    "INSERT OR IGNORE INTO rooms(code, type) VALUES(?,?)",
                    (r.room_code, r.room_type),
                )
                room_id = conn.execute(
                    "SELECT id FROM rooms WHERE code=?",
                    (r.room_code,),
                ).fetchone()[0]

            conn.execute(
                """
                INSERT OR REPLACE INTO schedule
                (batch_id, instructor_id, room_id, day, slot, time_start, time_end,
                 subject, subject_is_lab, is_two_hour)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    batch_id,
                    instructor_id,
                    room_id,
                    r.day,
                    r.slot,
                    r.time_start,
                    r.time_end,
                    r.subject,
                    int(r.subject_is_lab),
                    int(r.is_two_hour),
                ),
            )
        conn.commit()
