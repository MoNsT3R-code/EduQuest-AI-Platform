"""SQLite storage: one connection per request, foreign keys on, versioned migrations."""
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g

# Each entry upgrades the schema by one version (tracked in PRAGMA user_version).
MIGRATIONS = [
    """
    CREATE TABLE students (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 30),
        name_key TEXT NOT NULL,
        grade INTEGER NOT NULL CHECK (grade BETWEEN 3 AND 7),
        secret_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        UNIQUE (name_key, grade)
    );

    CREATE TABLE quests (
        id INTEGER PRIMARY KEY,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        subject TEXT NOT NULL,
        mode TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        abandoned INTEGER NOT NULL DEFAULT 0,
        score REAL,
        hints_used INTEGER,
        duration_s REAL,
        xp INTEGER
    );
    CREATE INDEX quests_by_student ON quests (student_id, finished_at);

    CREATE TABLE quest_items (
        id INTEGER PRIMARY KEY,
        quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        skill TEXT NOT NULL,
        difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
        prompt TEXT NOT NULL,
        options_json TEXT NOT NULL,
        answer_index INTEGER NOT NULL,
        hint TEXT NOT NULL,
        explanation TEXT NOT NULL,
        served_at TEXT NOT NULL,
        answered_at TEXT,
        tries INTEGER NOT NULL DEFAULT 0,
        hints_used INTEGER NOT NULL DEFAULT 0,
        last_choice INTEGER,
        correct INTEGER,
        credit REAL,
        UNIQUE (quest_id, position)
    );

    CREATE TABLE predictions (
        quest_id INTEGER PRIMARY KEY REFERENCES quests(id) ON DELETE CASCADE,
        label TEXT NOT NULL,
        confidence REAL NOT NULL,
        formula_score REAL NOT NULL,
        model_version TEXT NOT NULL,
        features_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE skill_ratings (
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        subject TEXT NOT NULL,
        rating REAL NOT NULL,
        answers INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (student_id, subject)
    );

    CREATE TABLE badges (
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        code TEXT NOT NULL,
        quest_id INTEGER REFERENCES quests(id) ON DELETE SET NULL,
        earned_at TEXT NOT NULL,
        PRIMARY KEY (student_id, code)
    );
    """,
]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse(ts):
    return datetime.fromisoformat(ts)


def connect(path):
    conn = sqlite3.connect(path, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        with conn:
            conn.executescript(script)
            conn.execute(f"PRAGMA user_version = {number}")
    return len(MIGRATIONS)


def init_app(app):
    conn = connect(app.config["DATABASE"])
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        migrate(conn)
    finally:
        conn.close()
    app.teardown_appcontext(close_db)
