# GermanTutor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a terminal-based German language tutor TUI app using Textual + Ollama LLM, with adaptive curriculum, spaced repetition, and AI-powered quiz/feedback.

**Architecture:** Textual async TUI with aiosqlite persistence. Two-model Ollama setup (llama3.1:8b for curriculum reasoning, mistral:7b for fast quiz/tutor responses). All LLM I/O is strict JSON via a central prompt registry.

**Tech Stack:** Python 3.11+, Textual 0.60+, Ollama SDK, aiosqlite, Pydantic v2, PyYAML, TOML, uv

**Design Decisions:**
- Reorder questions: show shuffled words with numbers, learner types sequence (e.g. `3 1 4 2`)
- Single learner: auto-create on first launch, no login screen
- Lesson content: AI-generated via tutor prompts, manually reviewed before commit
- No tests to be written

---

## Phase 1 — Foundation

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `config/settings.toml`
- Create: `german_tutor/__init__.py`
- Create: `german_tutor/main.py`

**Step 1: Initialize project with uv**
```bash
cd /home/brian/projects/german-lang-tutor
uv init --name german-tutor --python 3.11
uv add textual ollama aiosqlite pydantic pyyaml rich
```

**Step 2: Write `pyproject.toml`**
```toml
[project]
name = "german-tutor"
version = "0.1.0"
description = "AI-powered German language TUI for English speakers"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.60.0",
    "ollama>=0.3.0",
    "aiosqlite>=0.20.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
]

[project.scripts]
german-tutor = "german_tutor.main:run"

[tool.uv]
dev-dependencies = [
    "textual-dev>=0.1.0",
]
```

**Step 3: Write `config/settings.toml`**
```toml
[app]
name = "GermanTutor"
version = "0.1.0"

[ollama]
host = "http://localhost:11434"
curriculum_model = "llama3.1:8b-instruct"
interaction_model = "mistral:7b-instruct"
num_ctx = 4096
num_gpu = 1

[db]
path = "data/db/learner.db"

[curriculum]
data_path = "data/curriculum"
default_level = "A1"
```

**Step 4: Write `german_tutor/main.py`** (minimal skeleton)
```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

class GermanTutorApp(App):
    """Main GermanTutor Textual application."""
    CSS_PATH = "styles/main.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

def run():
    app = GermanTutorApp()
    app.run()

if __name__ == "__main__":
    run()
```

**Step 5: Commit**
```bash
git init
git add .
git commit -m "feat: project scaffolding with uv and Textual skeleton"
```

---

### Task 2: Data Models (Pydantic)

**Files:**
- Create: `german_tutor/models/__init__.py`
- Create: `german_tutor/models/learner.py`
- Create: `german_tutor/models/lesson.py`
- Create: `german_tutor/models/session.py`

**Step 1: Write `german_tutor/models/learner.py`**
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Learner(BaseModel):
    id: Optional[int] = None
    name: str
    current_level: str = "A1"
    created_at: Optional[datetime] = None
    streak_days: int = 0
    last_session_date: Optional[datetime] = None
```

**Step 2: Write `german_tutor/models/lesson.py`**
```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"

class LessonCategory(str, Enum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    SENTENCE_STRUCTURE = "sentence_structure"

class QuizQuestion(BaseModel):
    type: str  # multiple_choice | fill_blank | translation | reorder
    question: str
    context: Optional[str] = None
    options: Optional[list[str]] = None
    correct_answer: str
    correct_answer_index: Optional[int] = None
    answer_explanation: str
    grammar_rule_tested: str
    english_comparison: str
    hint: str
    points: int = 10

class LessonQuiz(BaseModel):
    questions: list[QuizQuestion]

class Lesson(BaseModel):
    id: str  # e.g. "A1-GRM-002"
    level: CEFRLevel
    category: LessonCategory
    title: str
    prerequisites: list[str] = []
    estimated_minutes: int
    tags: list[str] = []
    explanation: dict
    example_sentences: list[dict] = []
    quiz: Optional[LessonQuiz] = None

class LessonRecommendation(BaseModel):
    recommended_lesson_id: str
    lesson_title: str
    reason: str
    difficulty_adjustment: str
    english_speaker_warning: Optional[str] = None
    estimated_minutes: int
    review_items: list[str] = []

class LessonProgress(BaseModel):
    id: Optional[int] = None
    learner_id: int
    lesson_id: str
    completed_at: Optional[datetime] = None
    attempts: int = 0
    last_score: float = 0.0
    mastery_score: float = 0.0
    next_review: Optional[datetime] = None
```

**Step 3: Write `german_tutor/models/session.py`**
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class QuizResponse(BaseModel):
    id: Optional[int] = None
    session_id: Optional[int] = None
    question_id: str
    user_answer: str
    is_correct: bool
    time_taken_seconds: int = 0
    llm_evaluation: Optional[dict] = None

class QuizSession(BaseModel):
    id: Optional[int] = None
    learner_id: int
    lesson_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_questions: int = 0
    correct_answers: int = 0
    score: float = 0.0
    llm_feedback: Optional[dict] = None
    responses: list[QuizResponse] = []
```

**Step 4: Commit**
```bash
git add german_tutor/models/
git commit -m "feat: add Pydantic data models for learner, lesson, and session"
```

---

### Task 3: Database Schema & Migrations

**Files:**
- Create: `data/db/.gitkeep`
- Create: `german_tutor/db/__init__.py`
- Create: `german_tutor/db/connection.py`
- Create: `german_tutor/db/migrations.py`

**Step 1: Write `german_tutor/db/connection.py`**
```python
import aiosqlite
import tomllib
from pathlib import Path

_db: aiosqlite.Connection | None = None

def _load_db_path() -> str:
    config_path = Path("config/settings.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    return config["db"]["path"]

async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = _load_db_path()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
    return _db

async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
```

**Step 2: Write `german_tutor/db/migrations.py`**

Full SQL schema — `learner`, `lesson_progress`, `quiz_sessions`, `quiz_responses`, `vocabulary_cards` tables, plus a `schema_version` table:

```python
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
    next_review DATETIME
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
    next_review DATETIME
);
"""

async def run_migrations(db: aiosqlite.Connection) -> None:
    await db.executescript(SCHEMA_SQL)
    await db.commit()
```

**Step 3: Commit**
```bash
git add german_tutor/db/ data/
git commit -m "feat: SQLite schema and async connection pool"
```

---

### Task 4: Database Repositories

**Files:**
- Create: `german_tutor/db/repositories/__init__.py`
- Create: `german_tutor/db/repositories/learner_repo.py`
- Create: `german_tutor/db/repositories/progress_repo.py`

**Step 1: Write `learner_repo.py`**
```python
import aiosqlite
from german_tutor.models.learner import Learner
from datetime import datetime

class LearnerRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create(self, name: str) -> Learner:
        async with self.db.execute(
            "INSERT INTO learner (name) VALUES (?) RETURNING *", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            await self.db.commit()
            return Learner(**dict(row))

    async def get_by_id(self, learner_id: int) -> Learner | None:
        async with self.db.execute(
            "SELECT * FROM learner WHERE id = ?", (learner_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return Learner(**dict(row)) if row else None

    async def get_first(self) -> Learner | None:
        async with self.db.execute("SELECT * FROM learner LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return Learner(**dict(row)) if row else None

    async def update_level(self, learner_id: int, level: str) -> None:
        await self.db.execute(
            "UPDATE learner SET current_level = ? WHERE id = ?", (level, learner_id)
        )
        await self.db.commit()

    async def update_streak(self, learner_id: int, streak: int, last_date: datetime) -> None:
        await self.db.execute(
            "UPDATE learner SET streak_days = ?, last_session_date = ? WHERE id = ?",
            (streak, last_date.isoformat(), learner_id)
        )
        await self.db.commit()
```

**Step 2: Write `progress_repo.py`**

Handles `lesson_progress`, `quiz_sessions`, `quiz_responses`, `vocabulary_cards` CRUD + aggregation queries (mastery score rolling average, spaced repetition due items, last 10 session performance history):

```python
import aiosqlite
import json
from datetime import datetime
from german_tutor.models.lesson import LessonProgress
from german_tutor.models.session import QuizSession, QuizResponse

class ProgressRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    # --- Lesson Progress ---

    async def upsert_lesson_progress(self, progress: LessonProgress) -> None:
        await self.db.execute("""
            INSERT INTO lesson_progress (learner_id, lesson_id, completed_at, attempts, last_score, mastery_score, next_review)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(learner_id, lesson_id) DO UPDATE SET
                completed_at = excluded.completed_at,
                attempts = lesson_progress.attempts + 1,
                last_score = excluded.last_score,
                mastery_score = excluded.mastery_score,
                next_review = excluded.next_review
        """, (
            progress.learner_id, progress.lesson_id,
            progress.completed_at.isoformat() if progress.completed_at else None,
            progress.attempts, progress.last_score, progress.mastery_score,
            progress.next_review.isoformat() if progress.next_review else None
        ))
        await self.db.commit()

    async def get_lesson_progress(self, learner_id: int, lesson_id: str) -> LessonProgress | None:
        async with self.db.execute(
            "SELECT * FROM lesson_progress WHERE learner_id = ? AND lesson_id = ?",
            (learner_id, lesson_id)
        ) as cursor:
            row = await cursor.fetchone()
            return LessonProgress(**dict(row)) if row else None

    async def get_all_progress(self, learner_id: int) -> list[LessonProgress]:
        async with self.db.execute(
            "SELECT * FROM lesson_progress WHERE learner_id = ?", (learner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [LessonProgress(**dict(r)) for r in rows]

    async def get_due_reviews(self, learner_id: int, today: datetime) -> list[LessonProgress]:
        async with self.db.execute(
            "SELECT * FROM lesson_progress WHERE learner_id = ? AND next_review <= ?",
            (learner_id, today.isoformat())
        ) as cursor:
            rows = await cursor.fetchall()
            return [LessonProgress(**dict(r)) for r in rows]

    # --- Quiz Sessions ---

    async def create_session(self, session: QuizSession) -> int:
        async with self.db.execute("""
            INSERT INTO quiz_sessions (learner_id, lesson_id, started_at, total_questions)
            VALUES (?, ?, ?, ?)
        """, (
            session.learner_id, session.lesson_id,
            (session.started_at or datetime.now()).isoformat(),
            session.total_questions
        )) as cursor:
            await self.db.commit()
            return cursor.lastrowid

    async def complete_session(self, session_id: int, correct: int, total: int, score: float, feedback: dict) -> None:
        await self.db.execute("""
            UPDATE quiz_sessions SET completed_at = ?, correct_answers = ?,
            total_questions = ?, score = ?, llm_feedback = ? WHERE id = ?
        """, (
            datetime.now().isoformat(), correct, total, score,
            json.dumps(feedback), session_id
        ))
        await self.db.commit()

    async def get_recent_sessions(self, learner_id: int, limit: int = 10) -> list[dict]:
        async with self.db.execute("""
            SELECT qs.*, lp.mastery_score
            FROM quiz_sessions qs
            LEFT JOIN lesson_progress lp ON lp.lesson_id = qs.lesson_id AND lp.learner_id = qs.learner_id
            WHERE qs.learner_id = ?
            ORDER BY qs.started_at DESC LIMIT ?
        """, (learner_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- Quiz Responses ---

    async def save_response(self, response: QuizResponse) -> None:
        await self.db.execute("""
            INSERT INTO quiz_responses (session_id, question_id, user_answer, is_correct, time_taken_seconds, llm_evaluation)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            response.session_id, response.question_id, response.user_answer,
            response.is_correct, response.time_taken_seconds,
            json.dumps(response.llm_evaluation) if response.llm_evaluation else None
        ))
        await self.db.commit()

    async def get_session_responses(self, session_id: int) -> list[QuizResponse]:
        async with self.db.execute(
            "SELECT * FROM quiz_responses WHERE session_id = ?", (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [QuizResponse(**dict(r)) for r in rows]

    # --- Vocabulary Cards ---

    async def upsert_vocab_card(self, learner_id: int, german: str, english: str, level: str) -> None:
        await self.db.execute("""
            INSERT INTO vocabulary_cards (learner_id, german_word, english_word, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
        """, (learner_id, german, english, level))
        await self.db.commit()

    async def update_vocab_card_sm2(self, card_id: int, ease: float, interval: int, reps: int, next_review: datetime) -> None:
        await self.db.execute("""
            UPDATE vocabulary_cards SET ease_factor = ?, interval_days = ?,
            repetitions = ?, next_review = ? WHERE id = ?
        """, (ease, interval, reps, next_review.isoformat(), card_id))
        await self.db.commit()

    async def get_due_vocab_cards(self, learner_id: int, today: datetime) -> list[dict]:
        async with self.db.execute("""
            SELECT * FROM vocabulary_cards WHERE learner_id = ? AND (next_review IS NULL OR next_review <= ?)
            ORDER BY next_review ASC LIMIT 20
        """, (learner_id, today.isoformat())) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
```

**Step 3: Commit**
```bash
git add german_tutor/db/repositories/
git commit -m "feat: database repositories for learner and progress tracking"
```

---

### Task 5: Ollama Client Wrapper

**Files:**
- Create: `german_tutor/llm/__init__.py`
- Create: `german_tutor/llm/client.py`

**Step 1: Write `german_tutor/llm/client.py`**
```python
import json
import tomllib
from pathlib import Path
from typing import AsyncGenerator
import ollama

def _load_config() -> dict:
    with open(Path("config/settings.toml"), "rb") as f:
        return tomllib.load(f)

class OllamaClient:
    def __init__(self, host: str | None = None):
        config = _load_config()
        self.host = host or config["ollama"]["host"]
        self.curriculum_model = config["ollama"]["curriculum_model"]
        self.interaction_model = config["ollama"]["interaction_model"]
        self.client = ollama.AsyncClient(host=self.host)

    async def chat(self, model: str, messages: list[dict], format: str = None) -> ollama.Message:
        response = await self.client.chat(
            model=model,
            messages=messages,
            format=format
        )
        return response.message

    async def chat_json(self, model: str, messages: list[dict]) -> dict:
        """Returns parsed JSON dict from LLM response."""
        msg = await self.chat(model=model, messages=messages, format="json")
        return json.loads(msg.content)

    async def stream_chat(self, model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
        async for chunk in await self.client.chat(
            model=model, messages=messages, stream=True
        ):
            if chunk.message.content:
                yield chunk.message.content

    async def list_models(self) -> list[str]:
        """Return list of locally available Ollama model names."""
        response = await self.client.list()
        return [m.model for m in response.models]
```

**Step 2: Commit**
```bash
git add german_tutor/llm/
git commit -m "feat: async Ollama client wrapper with streaming support"
```

---

## Phase 2 — Curriculum Engine

### Task 6: Prompt Registry

**Files:**
- Create: `german_tutor/llm/prompts.py`

Transcribe ALL 8 prompt templates from `german_tutor_prompts.md` into `prompts.py` exactly:
- `CURRICULUM_SYSTEM_PROMPT` + `CURRICULUM_USER_PROMPT`
- `TUTOR_SYSTEM_PROMPT` + `TUTOR_USER_PROMPT`
- `BREAKDOWN_SYSTEM_PROMPT` + `BREAKDOWN_USER_PROMPT`
- `QUIZ_GEN_SYSTEM_PROMPT` + `QUIZ_GEN_USER_PROMPT`
- `EVALUATION_SYSTEM_PROMPT` + `EVALUATION_USER_PROMPT`
- `ANALYSIS_SYSTEM_PROMPT` + `ANALYSIS_USER_PROMPT`
- `VOCABULARY_SYSTEM_PROMPT` + `VOCABULARY_USER_PROMPT`
- `HINT_SYSTEM_PROMPT` + `HINT_USER_PROMPT`

Implement `PromptTemplate` dataclass with `render_user(**kwargs)` method (from prompts.md section 10).

Build `PROMPTS` dict keyed by `"curriculum"`, `"tutor"`, `"breakdown"`, `"quiz_gen"`, `"evaluation"`, `"analysis"`, `"vocabulary"`, `"hint"`.

**Commit:**
```bash
git add german_tutor/llm/prompts.py
git commit -m "feat: central prompt registry with all 8 LLM prompt templates"
```

---

### Task 7: Spaced Repetition (SM-2)

**Files:**
- Create: `german_tutor/curriculum/__init__.py`
- Create: `german_tutor/curriculum/spaced_repetition.py`

Implement `CardState` dataclass and `calculate_next_review(card, quality)` function from architecture doc section 5.3.

Add `score_to_quality(score_0_100: int) -> int` helper mapping evaluation rubric scores (0/25/50/70/85/100) to SM-2 quality ratings (0-5).

**Commit:**
```bash
git add german_tutor/curriculum/
git commit -m "feat: SM-2 spaced repetition algorithm"
```

---

### Task 8: CEFR Progression Logic

**Files:**
- Create: `german_tutor/curriculum/cefr.py`

```python
LEVEL_ORDER = ["A1", "A2", "B1"]
MASTERY_THRESHOLD = 0.75

class CEFRProgressionEngine:
    def can_advance(self, current_level: str, mastery_scores: list[float]) -> bool: ...
    def next_level(self, current_level: str) -> str | None: ...
    def progress_percent(self, mastery_scores: list[float]) -> float: ...
```

**Commit:**
```bash
git add german_tutor/curriculum/cefr.py
git commit -m "feat: CEFR progression logic with mastery thresholds"
```

---

### Task 9: YAML Curriculum Loader + A1 Content (5 lessons)

**Files:**
- Create: `german_tutor/curriculum/loader.py`
- Create: `data/curriculum/A1/01_greetings.yaml`
- Create: `data/curriculum/A1/02_articles_nominative.yaml`
- Create: `data/curriculum/A1/03_verbs_sein_haben.yaml`
- Create: `data/curriculum/A1/04_nominative_case.yaml`
- Create: `data/curriculum/A1/05_personal_pronouns.yaml`

Loader:
```python
class CurriculumLoader:
    def load_lesson(self, file_path: Path) -> Lesson: ...
    def load_level(self, level: str) -> list[Lesson]: ...
    def load_all(self) -> dict[str, list[Lesson]]: ...
```

Each YAML file follows this schema from architecture doc section 6:
- `id`, `level`, `category`, `title`, `prerequisites`, `estimated_minutes`, `tags`
- `explanation`: `concept`, `english_comparison`, optional `table` (headers + rows)
- `example_sentences`: list of `{german, english, breakdown_focus}`
- `quiz`: optional static questions

IDs: `A1-GRM-001` through `A1-GRM-005`

**Commit:**
```bash
git add german_tutor/curriculum/ data/curriculum/A1/
git commit -m "feat: YAML curriculum loader and 5 A1 starter lessons"
```

---

### Task 10: AI Agents

**Files:**
- Create: `german_tutor/llm/curriculum_agent.py`
- Create: `german_tutor/llm/tutor_agent.py`
- Create: `german_tutor/llm/quiz_agent.py`

**curriculum_agent.py:** `CurriculumAgent` class using `curriculum_model`:
- `recommend_next_lesson(performance_history, available_lessons, current_level, due_reviews, learner) -> LessonRecommendation`
- `generate_performance_analysis(session, question_breakdown, history, learner) -> dict`

Uses `PROMPTS["curriculum"]` and `PROMPTS["analysis"]`.

**tutor_agent.py:** `TutorAgent` class using `interaction_model`:
- `explain_lesson(lesson, learner) -> dict`
- `breakdown_sentence(sentence, cefr_level) -> dict`
- `get_vocabulary_entry(german_word, cefr_level) -> dict`

Uses `PROMPTS["tutor"]`, `PROMPTS["breakdown"]`, `PROMPTS["vocabulary"]`.

**quiz_agent.py:** `QuizAgent` class using `interaction_model`:
- `generate_quiz(lesson, learner) -> dict` (10 questions)
- `evaluate_answer(question, user_answer, correct_answer, grammar_rule, cefr_level) -> dict`
- `get_hint(question, correct_answer, grammar_rule, hint_level, attempted_answer) -> dict`

Uses `PROMPTS["quiz_gen"]`, `PROMPTS["evaluation"]`, `PROMPTS["hint"]`.

**Commit:**
```bash
git add german_tutor/llm/
git commit -m "feat: curriculum, tutor, and quiz AI agents using prompt registry"
```

---

## Phase 3 — Textual Screens & Widgets

### Task 11: Textual Styles

**Files:**
- Create: `german_tutor/styles/main.tcss`
- Create: `german_tutor/styles/theme.tcss`

`main.tcss`: layout rules for nav sidebar + main content split matching wireframe from architecture doc section 7.1.

`theme.tcss`: color variable definitions — dark terminal theme. Color-code grammatical cases:
- nominative: red/error
- accusative: yellow/warning
- dative: accent/blue
- genitive: green/success

**Commit:**
```bash
git add german_tutor/styles/
git commit -m "feat: Textual CSS styles with grammatical case color coding"
```

---

### Task 12: Core Widgets

**Files:**
- Create: `german_tutor/widgets/__init__.py`
- Create: `german_tutor/widgets/grammar_panel.py`
- Create: `german_tutor/widgets/sentence_tree.py`
- Create: `german_tutor/widgets/progress_bar.py`
- Create: `german_tutor/widgets/streak_indicator.py`
- Create: `german_tutor/widgets/quiz_card.py`

**grammar_panel.py:** `GrammarPanelWidget` — side-by-side EN↔DE display. Renders lesson `explanation` dict: `concept`, `english_comparison`, optional `table`.

**sentence_tree.py:** `SentenceBreakdownWidget` from architecture doc section 7.3. `DataTable` columns: Word, English, Part of Speech, Case/Role, Note. Color words by `colour_tag` field.

**progress_bar.py:** `CEFRProgressBar` — shows current level, next level, fill percent.

**streak_indicator.py:** `StreakIndicator` — displays streak day count as a Static widget.

**quiz_card.py:** `QuizCard` — renders a single quiz question with all 4 types:
- `multiple_choice`: radio-style option list
- `fill_blank`: text input with blank highlighted in prompt
- `translation`: text input with English sentence as prompt
- `reorder`: shows shuffled numbered words, learner types sequence like `3 1 4 2`

Includes hint toggle button.

**Commit:**
```bash
git add german_tutor/widgets/
git commit -m "feat: Textual widgets for grammar panel, sentence breakdown, progress, quiz"
```

---

### Task 13: Home Screen

**Files:**
- Create: `german_tutor/screens/__init__.py`
- Create: `german_tutor/screens/home.py`

`HomeScreen(Screen)` — dashboard matching wireframe from architecture doc section 7.1:
- Left nav sidebar: `📚 Lessons`, `🧠 Quiz`, `📊 Progress`, `🔁 Review`, `⚙ Settings`
- Right: lesson recommendation card, CEFR progress bar, streak indicator
- Buttons: `Start Quiz`, `Next Lesson`
- On mount: load learner from DB (or prompt for name if first launch), call `CurriculumAgent.recommend_next_lesson()`

Single-learner: auto-create with default name on first launch if no learner exists.

**Commit:**
```bash
git add german_tutor/screens/home.py
git commit -m "feat: home screen dashboard with curriculum recommendation"
```

---

### Task 14: Lesson Screen

**Files:**
- Create: `german_tutor/screens/lesson.py`

`LessonScreen(Screen)`:
- Loads lesson by ID from `CurriculumLoader`
- Calls `TutorAgent.explain_lesson()` on mount (show loading spinner)
- Renders `GrammarPanelWidget` with AI-generated explanation
- For each example sentence (2-3): renders `SentenceBreakdownWidget` (calls `TutorAgent.breakdown_sentence()`)
- Buttons: `Start Quiz`, `Back`

**Commit:**
```bash
git add german_tutor/screens/lesson.py
git commit -m "feat: lesson screen with AI grammar explanation and sentence breakdown"
```

---

### Task 15: Quiz Screen

**Files:**
- Create: `german_tutor/screens/quiz.py`

`QuizScreen(ModalScreen)` — full quiz flow:
- On mount: call `QuizAgent.generate_quiz(lesson, learner)` → 10 questions
- Render current `QuizCard`, progress bar (Q3/10), score display
- On submit:
  - `multiple_choice`/`reorder`: evaluate locally against `correct_answer`
  - `fill_blank`/`translation`: call `QuizAgent.evaluate_answer()`
- Track `QuizResponse` objects, save each to DB via `ProgressRepository`
- Hint button: call `QuizAgent.get_hint()` (levels 1→3, each press advances level)
- After final question: save `QuizSession` to DB, navigate to `ResultsScreen`

**Commit:**
```bash
git add german_tutor/screens/quiz.py
git commit -m "feat: quiz screen with AI generation, LLM evaluation, and hint system"
```

---

### Task 16: Results & Breakdown Screens

**Files:**
- Create: `german_tutor/screens/results.py`
- Create: `german_tutor/screens/breakdown.py`

**results.py:** `ResultsScreen(Screen)` — post-quiz analysis view matching wireframe from architecture doc section 10:
- Score: `7/10  ██████████░░░░  70%`
- Strong areas list (from AI analysis)
- Weak areas list
- AI Analysis block (calls `CurriculumAgent.generate_performance_analysis()`)
- Recommended next lessons (3 items)
- Buttons: `Review Mistakes`, `Next Lesson`, `Home`
- On mount: update `lesson_progress.mastery_score` using SM-2, update streak via `calculate_streak()`

**breakdown.py:** `BreakdownScreen(Screen)`:
- Accepts a German sentence string
- Calls `TutorAgent.breakdown_sentence()`
- Renders full `SentenceBreakdownWidget`
- Renders `structure_comparison` section: German vs English word order pattern side-by-side

**Commit:**
```bash
git add german_tutor/screens/results.py german_tutor/screens/breakdown.py
git commit -m "feat: results screen with AI coaching and sentence breakdown screen"
```

---

### Task 17: Settings Screen

**Files:**
- Create: `german_tutor/screens/settings.py`

`SettingsScreen(Screen)`:
- Model selection: fetch available models via `OllamaClient.list_models()`, show dropdown/select
- Curriculum model selector
- Interaction model selector
- Ollama host URL input
- Save button: writes updated values back to `config/settings.toml`
- Reload `OllamaClient` in app state after save

**Commit:**
```bash
git add german_tutor/screens/settings.py
git commit -m "feat: settings screen with Ollama model selection"
```

---

### Task 18: App State & Wire Everything Together

**Files:**
- Create: `german_tutor/app_state.py`
- Modify: `german_tutor/main.py`

**app_state.py:** Singleton `AppState` holding shared resources:
```python
class AppState:
    ollama_client: OllamaClient
    learner_repo: LearnerRepository
    progress_repo: ProgressRepository
    curriculum_loader: CurriculumLoader
    curriculum_agent: CurriculumAgent
    tutor_agent: TutorAgent
    quiz_agent: QuizAgent
    cefr_engine: CEFRProgressionEngine
    current_learner: Learner | None
```

**main.py (rewrite):**
- Import all screens
- On startup: `run_migrations()`, initialize `AppState`, load or create learner
- Mount `HomeScreen` as default
- Pass `AppState` into screens on `push_screen`
- Keyboard shortcuts: `q` quit, `h` home, `?` help
- Clean `close_db()` on exit via `on_unmount`

**Commit:**
```bash
git add german_tutor/app_state.py german_tutor/main.py
git commit -m "feat: app state singleton and wire all screens into Textual app"
```

---

## Phase 4 — Content & Polish

### Task 19: Complete A1 Curriculum (20 lessons total)

**Files:**
- Create: `data/curriculum/A1/06_accusative_case.yaml` through `data/curriculum/A1/20_*.yaml`

Remaining 15 A1 topics:
- `06_accusative_case` — definite/indefinite articles in accusative
- `07_indefinite_articles` — ein/eine/ein + kein
- `08_negation_nicht_kein` — nicht vs kein
- `09_basic_verbs_regular` — regular -en verb conjugation
- `10_separable_verbs_intro` — prefix detachment basics
- `11_modal_verbs_intro` — können, müssen, wollen
- `12_question_words` — wer, was, wo, wann, warum, wie
- `13_numbers_time` — 1-100, Uhr, days of week
- `14_dative_intro` — dative case and indirect objects
- `15_prepositions_accusative` — durch, für, gegen, ohne, um
- `16_prepositions_dative` — aus, bei, mit, nach, seit, von, zu
- `17_adjectives_basic` — predicate adjectives (no endings)
- `18_word_order_v2` — V2 rule, time-manner-place
- `19_common_phrases` — greetings, polite phrases, basic conversation
- `20_subordinate_clauses_intro` — weil, dass, wenn

**Commit:**
```bash
git add data/curriculum/A1/
git commit -m "feat: complete A1 curriculum (20 lessons)"
```

---

### Task 20: A2 Curriculum (15 lessons)

**Files:**
- Create: `data/curriculum/A2/01_perfect_tense.yaml` through `data/curriculum/A2/15_*.yaml`

Topics: Perfekt tense, Präteritum for sein/haben, dative case deep-dive, adjective declension (nominative + accusative), modal verbs full conjugation, subordinate clauses, relative pronouns, comparative/superlative, reflexive verbs, two-way prepositions (an/auf/in + case), Konjunktiv II intro (würde), imperative, passive voice intro.

**Commit:**
```bash
git add data/curriculum/A2/
git commit -m "feat: A2 curriculum (15 lessons)"
```

---

### Task 21: Vocabulary Cards + SM-2 Integration

**Files:**
- Modify: `german_tutor/screens/results.py`
- Modify: `german_tutor/screens/home.py`

After quiz completion in `ResultsScreen`:
- Extract vocabulary from lesson's `example_sentences`
- Upsert `vocabulary_cards` via `ProgressRepository.upsert_vocab_card()`
- Update SM-2 fields using `calculate_next_review()` for any card reviewed

In `HomeScreen`, wire `🔁 Review` nav item:
- Load due vocab cards via `ProgressRepository.get_due_vocab_cards()`
- Run flashcard-style loop: `QuizCard` in `translation` mode (DE → EN)
- After each answer: update SM-2 score, save to DB

**Commit:**
```bash
git commit -am "feat: vocabulary cards integrated with SM-2 spaced repetition review"
```

---

### Task 22: Streak Tracking

**Files:**
- Create: `german_tutor/curriculum/streak.py`
- Modify: `german_tutor/screens/results.py`

`streak.py`:
```python
def calculate_streak(last_session_date: datetime | None, current_streak: int) -> int:
    today = date.today()
    if last_session_date is None:
        return 1
    last_date = last_session_date.date()
    delta = (today - last_date).days
    if delta == 0:
        return current_streak      # already studied today
    elif delta == 1:
        return current_streak + 1  # consecutive day
    else:
        return 1                   # streak broken, restart
```

Call `calculate_streak()` in `ResultsScreen` after session save. Update `learner.streak_days` via `LearnerRepository.update_streak()`.

**Commit:**
```bash
git commit -am "feat: streak tracking with consecutive day detection"
```

---

### Task 23: B1 Starter Curriculum (10 lessons)

**Files:**
- Create: `data/curriculum/B1/01_genitive_case.yaml` through `data/curriculum/B1/10_*.yaml`

Topics: genitive case (des/der), passive voice (werden + past participle), Konjunktiv II full (könnte, müsste, hätte, wäre), indirect speech, complex subordinate clauses (obwohl, während, nachdem), relative clauses in all cases, participial phrases, extended adjective phrases, mixed tenses in narrative, discourse connectors.

**Commit:**
```bash
git add data/curriculum/B1/
git commit -m "feat: B1 starter curriculum (10 lessons)"
```

---

### Task 24: Keyboard Shortcuts, Help Overlay & Polish

**Files:**
- Modify: `german_tutor/main.py`
- Modify: `german_tutor/styles/main.tcss`
- Modify: `german_tutor/styles/theme.tcss`
- Create: `README.md`

Keyboard shortcuts (add to `BINDINGS` in main app):
- `q` — quit
- `h` — go to home screen
- `?` — toggle help overlay
- `Ctrl+R` — go to review queue

Help overlay: `ModalScreen` listing all keybindings in a table.

Polish: ensure responsive layout, correct padding, readable font sizing, proper color contrast for all case color tags.

`README.md`:
- Quick start (uv install, ollama model pull, run)
- GPU setup notes (ROCm / RX 7800 XT)
- Settings guide
- CEFR level overview

**Commit:**
```bash
git commit -am "feat: keyboard shortcuts, help overlay, polish, and README"
```

---

## Prompt Chaining Reference

```
App Start → CurriculumAgent.recommend_next_lesson()
         → TutorAgent.explain_lesson()
         → TutorAgent.breakdown_sentence() (×2-3 per lesson)
         → QuizAgent.generate_quiz()
         → Per answer: QuizAgent.evaluate_answer() OR QuizAgent.get_hint()
         → CurriculumAgent.generate_performance_analysis()
         → Loop back to CurriculumAgent.recommend_next_lesson()
```

---

## Task Summary

| Phase | Tasks | Deliverables |
|---|---|---|
| 1 — Foundation | 1-5 | Scaffolding, models, DB schema, repositories, Ollama client |
| 2 — Curriculum Engine | 6-10 | Prompt registry, SM-2, CEFR, YAML loader, AI agents |
| 3 — TUI Screens | 11-18 | 6 screens, 5 widgets, app state wiring |
| 4 — Content & Polish | 19-24 | 45 lessons (A1/A2/B1), vocab cards, streaks, polish |
