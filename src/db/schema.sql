CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    semester TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS instructors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT,
    UNIQUE(name, department)
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    building TEXT,
    floor INTEGER,
    description TEXT,
    landmark TEXT
);

CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    instructor_id INTEGER REFERENCES instructors(id),
    room_id INTEGER REFERENCES rooms(id),
    day TEXT NOT NULL CHECK(day IN ('Monday','Tuesday','Wednesday','Thursday','Friday')),
    slot INTEGER NOT NULL CHECK(slot BETWEEN 1 AND 6),
    time_start TEXT NOT NULL,
    time_end TEXT NOT NULL,
    subject TEXT NOT NULL,
    subject_is_lab INTEGER DEFAULT 0,
    is_two_hour INTEGER DEFAULT 0,
    UNIQUE(batch_id, day, slot)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_type TEXT NOT NULL CHECK(user_type IN ('student','instructor')),
    identifier TEXT NOT NULL,
    contact TEXT NOT NULL,
    notify_minutes_before INTEGER DEFAULT 15
);
