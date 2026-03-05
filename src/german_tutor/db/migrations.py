from __future__ import annotations

import aiosqlite

# Migration definitions
MIGRATIONS = {
    1: """
-- Migration v1: Create base tables (baseline for existing databases)
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
""",
    2: """
-- Migration v2: Add daily goal minutes to learner table
ALTER TABLE learner ADD COLUMN daily_goal_minutes INTEGER DEFAULT 20;
""",
    3: """
-- Migration v3: Add gender column to vocabulary_cards for gender drills
ALTER TABLE vocabulary_cards ADD COLUMN gender TEXT;
""",
    4: """
-- Migration v4: Add last_lesson_id to learner table for continue where left off
ALTER TABLE learner ADD COLUMN last_lesson_id TEXT;
""",
    5: """
-- Migration v5: Track vocabulary topic progress
CREATE TABLE IF NOT EXISTS vocabulary_topic_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER REFERENCES learner(id),
    topic_id TEXT NOT NULL,
    topic_level TEXT,
    total_words INTEGER NOT NULL,
    words_seen INTEGER DEFAULT 0,
    completed_percent REAL DEFAULT 0.0,
    last_interacted_at DATETIME,
    UNIQUE(learner_id, topic_id)
);
""",
    6: """
-- Migration v6: Store ease_factor for SM-2 on lesson_progress
ALTER TABLE lesson_progress ADD COLUMN ease_factor REAL DEFAULT 2.5;
"""
}


async def run_migrations(db: aiosqlite.Connection) -> None:
    """Run migrations in order, checking version before each step."""
    # Create schema_version table if it doesn't exist
    await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
    """)
    
    # Get current version
    cursor = await db.execute("SELECT MAX(version) FROM schema_version")
    row = await cursor.fetchone()
    current_version = row[0] if row and row[0] is not None else 0
    
    # Run migrations in order
    for version in sorted(MIGRATIONS.keys()):
        if version > current_version:
            # Check if this specific version has already been applied
            cursor = await db.execute("SELECT version FROM schema_version WHERE version = ?", (version,))
            existing = await cursor.fetchone()
            
            if not existing:
                # Apply migration
                migration_sql = MIGRATIONS[version]
                await db.executescript(migration_sql)
                
                # Record this version
                await db.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
                await db.commit()
                print(f"Applied migration v{version}")
            else:
                print(f"Migration v{version} already applied, skipping")
