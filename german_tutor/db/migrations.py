from __future__ import annotations

import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS learner (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    current_level TEXT DEFAULT 'A1',
    streak_days INTEGER DEFAULT 0,
    last_session_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER REFERENCES learner(id),
    lesson_id TEXT NOT NULL,
    completed_at DATETIME,
    attempts INTEGER DEFAULT 0,
    last_score REAL,
    mastery_score REAL DEFAULT 0.0,
    next_review DATETIME,
    UNIQUE(learner_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER REFERENCES learner(id),
    lesson_id TEXT NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    total_questions INTEGER,
    correct_answers INTEGER,
    score REAL,
    llm_feedback TEXT
);

CREATE TABLE IF NOT EXISTS quiz_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES quiz_sessions(id),
    question_id TEXT,
    user_answer TEXT,
    is_correct BOOLEAN,
    time_taken_seconds INTEGER,
    llm_evaluation TEXT
);

CREATE TABLE IF NOT EXISTS vocabulary_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER REFERENCES learner(id),
    german_word TEXT NOT NULL,
    english_word TEXT NOT NULL,
    level TEXT,
    ease_factor REAL DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review DATETIME,
    UNIQUE(learner_id, german_word)
);
"""


async def run_migrations(db: aiosqlite.Connection) -> None:
    """Create all tables if they don't exist. Idempotent."""
    await db.executescript(SCHEMA_SQL)
    await db.commit()
