# Code Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address the critical, major, and significant minor findings from the March 2026 code review, restoring data integrity, fixing the SM-2 algorithm, and establishing a baseline test suite.

**Architecture:** Changes are surgical — no structural rewrites. Each task is scoped to the minimum code change that fixes the named defect. Tasks are ordered dependency-first (DB schema before repo before screen).

**Tech Stack:** Python 3.11+, Textual, aiosqlite, pytest, pydantic, SM-2

---

## Task 1: Decouple ResultsScreen side effects from LLM analysis

The most critical bug. SM-2 progress, streaks, and vocab persistence are trapped inside the same `try/except` as the LLM call. If the model is unavailable, all persistent data is silently discarded.

**Files:**
- Modify: `src/german_tutor/screens/results.py:70–123`

**Step 1: Refactor `on_mount`**

Replace the single monolithic try/except with independent calls. The LLM analysis is the only thing that can be allowed to fail silently:

```python
async def on_mount(self) -> None:
    """Run persistent side effects unconditionally, then attempt AI analysis."""
    if self.progress_repo is not None:
        await self._update_progress()
        await self._check_daily_goal()
        await self._upsert_vocab_cards()

    if self.curriculum_agent is not None and self.progress_repo is not None:
        await self._run_ai_analysis()

async def _run_ai_analysis(self) -> None:
    """Fetch AI coaching report and update the display. Non-fatal if it fails."""
    try:
        breakdown = [
            {
                "question_id": r.question_id,
                "is_correct": r.is_correct,
                "user_answer": r.user_answer,
                "evaluation": r.llm_evaluation or {},
            }
            for r in self.session.responses
        ]
        session_results = {
            "lesson_title": self.lesson.title,
            "correct": self.session.correct_answers,
            "total": self.session.total_questions,
            "score_percent": round(
                (self.session.correct_answers / (self.session.total_questions or 1)) * 100,
                1,
            ),
        }
        history = await self.progress_repo.get_recent_sessions(self.learner.id, limit=5)
        self._analysis = await self.curriculum_agent.generate_performance_analysis(
            learner=self.learner,
            session_results=session_results,
            question_breakdown=breakdown,
            history=history,
        )
        coach_msg = self._analysis.get("coach_message", "")
        self.query_one("#analysis-display", Static).update(coach_msg)
    except Exception as exc:
        self.query_one("#analysis-display", Static).update(
            f"Analysis unavailable: {exc}"
        )
```

Remove the old `on_mount` body entirely. The helper methods `_update_progress`, `_check_daily_goal`, `_upsert_vocab_cards`, `_update_streak` stay unchanged.

**Step 2: Verify manually**

Run the app, complete a quiz, then kill the Ollama process before results appear. Confirm the streak and lesson progress are still updated in the DB (`sqlite3 data/german_tutor.db "SELECT * FROM lesson_progress ORDER BY completed_at DESC LIMIT 1"`).

**Step 3: Commit**

```bash
git add src/german_tutor/screens/results.py
git commit -m "fix: decouple SM-2/streak/vocab persistence from LLM analysis in ResultsScreen"
```

---

## Task 2: Fix SM-2 — store and restore ease_factor

`ease_factor` is never persisted. Every quiz resets it to 2.5, so the adaptive scheduling never activates.

**Files:**
- Modify: `src/german_tutor/db/migrations.py`
- Modify: `src/german_tutor/db/repositories/progress_repo.py:18–41`
- Modify: `src/german_tutor/models/lesson.py` (add `ease_factor` field to `LessonProgress`)
- Modify: `src/german_tutor/screens/results.py:125–163` (`_update_progress`)

**Step 1: Add migration v6**

In `migrations.py`, add to `MIGRATIONS`:

```python
6: """
-- Migration v6: Store ease_factor for SM-2 on lesson_progress
ALTER TABLE lesson_progress ADD COLUMN ease_factor REAL DEFAULT 2.5;
"""
```

**Step 2: Add `ease_factor` to `LessonProgress` model**

In `models/lesson.py`, find `LessonProgress` and add:

```python
ease_factor: float = 2.5
```

**Step 3: Persist `ease_factor` in `upsert_lesson_progress`**

In `progress_repo.py`, update the INSERT columns and the ON CONFLICT SET clause:

```python
async def upsert_lesson_progress(self, progress: LessonProgress) -> None:
    await self.db.execute(
        """
        INSERT INTO lesson_progress
            (learner_id, lesson_id, completed_at, attempts, last_score,
             mastery_score, next_review, ease_factor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(learner_id, lesson_id) DO UPDATE SET
            completed_at   = excluded.completed_at,
            attempts       = lesson_progress.attempts + 1,
            last_score     = excluded.last_score,
            mastery_score  = excluded.mastery_score,
            next_review    = excluded.next_review,
            ease_factor    = excluded.ease_factor
        """,
        (
            progress.learner_id,
            progress.lesson_id,
            progress.completed_at.isoformat() if progress.completed_at else None,
            progress.attempts,
            progress.last_score,
            progress.mastery_score,
            progress.next_review.isoformat() if progress.next_review else None,
            progress.ease_factor,
        ),
    )
    await self.db.commit()
```

**Step 4: Restore `ease_factor` when building `CardState` in `results.py`**

Replace the hardcoded `ease_factor=2.5`:

```python
# In _update_progress
if existing:
    card = CardState(
        item_id=self.lesson.id,
        ease_factor=existing.ease_factor,   # ← restored from DB
        interval=1,
        repetitions=existing.attempts,
    )
else:
    card = CardState(item_id=self.lesson.id)

updated_card = calculate_next_review(card, quality)

progress = LessonProgress(
    learner_id=self.learner.id,
    lesson_id=self.lesson.id,
    completed_at=datetime.now(),
    attempts=(existing.attempts + 1) if existing else 1,
    last_score=self.session.score,
    mastery_score=min(1.0, self.session.score),
    next_review=updated_card.next_review,
    ease_factor=updated_card.ease_factor,   # ← persisted
)
```

**Step 5: Run the app and verify**

Complete two quizzes on the same lesson. After the second, check:
```bash
sqlite3 data/german_tutor.db \
  "SELECT lesson_id, ease_factor, next_review FROM lesson_progress LIMIT 5"
```
`ease_factor` should differ from 2.5 if any question was answered incorrectly.

**Step 6: Commit**

```bash
git add src/german_tutor/db/migrations.py \
        src/german_tutor/db/repositories/progress_repo.py \
        src/german_tutor/models/lesson.py \
        src/german_tutor/screens/results.py
git commit -m "fix: persist and restore SM-2 ease_factor across quiz sessions"
```

---

## Task 3: Fix settings.py — config path and asyncio.create_task

Two independent defects in the same file.

**Files:**
- Modify: `src/german_tutor/screens/settings.py:97–137`

**Step 1: Fix the relative `Path("config/settings.toml")`**

Replace the hardcoded relative path with one resolved from the package location:

```python
# At top of settings.py, after existing imports
from german_tutor.config import get_config  # already imported

# In _save_config, replace:
#   config_path = Path("config/settings.toml")
# with:
_SETTINGS_PATH = Path(__file__).parent.parent.parent.parent / "config" / "settings.toml"
```

Add `_SETTINGS_PATH` as a module-level constant (above the class). In `_save_config`, replace the local `config_path` assignment with `_SETTINGS_PATH`.

**Step 2: Replace `asyncio.create_task` with `self.app.run_worker`**

In `_save_config`, the DB update block currently uses `asyncio.create_task`. Replace it:

```python
# Remove: import asyncio / asyncio.create_task(...)
# Replace with:
if hasattr(self.app, '_state') and self.app._state and self.app._state.current_learner:
    self.app.run_worker(
        self.app._state.learner_repo.update_goal(
            self.app._state.current_learner.id,
            daily_goal,
        )
    )
    self.app._state.current_learner.daily_goal_minutes = daily_goal
```

Remove the `try/except Exception: pass` block wrapping it — `run_worker` handles errors through Textual's worker error handling.

**Step 3: Verify**

Launch the app from `/tmp` (`cd /tmp && python -m german_tutor`). Change the daily goal and save. Confirm the settings file in the project's `config/` directory is updated, not a new file in `/tmp/config/`.

**Step 4: Commit**

```bash
git add src/german_tutor/screens/settings.py
git commit -m "fix: resolve settings.toml path relative to package, use run_worker for async DB update"
```

---

## Task 4: Batch vocab card upserts

Each sentence triggers a separate `INSERT` + `COMMIT`. Replace with a single `executemany`.

**Files:**
- Modify: `src/german_tutor/db/repositories/progress_repo.py`
- Modify: `src/german_tutor/screens/results.py:194–206`

**Step 1: Add `upsert_vocab_cards_bulk` to `ProgressRepository`**

```python
async def upsert_vocab_cards_bulk(
    self,
    learner_id: int,
    entries: list[tuple[str, str, str]],  # (german, english, level)
) -> None:
    """Batch upsert vocabulary cards; skips duplicates."""
    if not entries:
        return
    await self.db.executemany(
        """
        INSERT INTO vocabulary_cards (learner_id, german_word, english_word, level)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(learner_id, german_word) DO NOTHING
        """,
        [(learner_id, g, e, lvl) for g, e, lvl in entries],
    )
    await self.db.commit()
```

**Step 2: Update `_upsert_vocab_cards` in `results.py`**

```python
async def _upsert_vocab_cards(self) -> None:
    """Extract vocabulary from lesson example sentences and upsert to DB."""
    level = self.lesson.level.value
    entries = [
        (entry.get("german", "").strip(), entry.get("english", "").strip(), level)
        for entry in self.lesson.example_sentences
        if entry.get("german", "").strip() and entry.get("english", "").strip()
    ]
    try:
        await self.progress_repo.upsert_vocab_cards_bulk(self.learner.id, entries)
    except Exception as e:
        self.app.log.error(f"Failed to upsert vocab cards: {e}")
```

Keep the old `upsert_vocab_card` (singular) in the repo — it's still used by other callers.

**Step 3: Commit**

```bash
git add src/german_tutor/db/repositories/progress_repo.py \
        src/german_tutor/screens/results.py
git commit -m "perf: batch vocab card upserts to single executemany+commit"
```

---

## Task 5: Add tests for pure functions

These are zero-dependency functions that are entirely untested. They are also where the SM-2 logic bug would have been caught.

**Files:**
- Create: `tests/test_spaced_repetition.py`
- Create: `tests/test_streak.py`
- Create: `tests/test_cefr.py`

**Step 1: Write `tests/test_spaced_repetition.py`**

```python
import pytest
from german_tutor.curriculum.spaced_repetition import (
    CardState,
    calculate_next_review,
    score_to_quality,
)


class TestScoreToQuality:
    @pytest.mark.parametrize(
        "score, expected_quality",
        [
            (100, 5),
            (90, 4),
            (85, 4),
            (75, 3),
            (70, 3),
            (60, 2),
            (50, 2),
            (30, 1),
            (25, 1),
            (10, 0),
            (0, 0),
        ],
    )
    def test_score_maps_to_quality(self, score, expected_quality):
        assert score_to_quality(score) == expected_quality


class TestCalculateNextReview:
    def test_perfect_recall_increases_ease_factor(self):
        card = CardState(item_id="lesson-1", ease_factor=2.5, interval=6, repetitions=2)
        updated = calculate_next_review(card, quality=5)
        assert updated.ease_factor > 2.5

    def test_poor_recall_decreases_ease_factor(self):
        card = CardState(item_id="lesson-1", ease_factor=2.5, interval=6, repetitions=2)
        updated = calculate_next_review(card, quality=2)
        assert updated.ease_factor < 2.5

    def test_ease_factor_never_drops_below_1_3(self):
        card = CardState(item_id="lesson-1", ease_factor=1.3, interval=1, repetitions=0)
        updated = calculate_next_review(card, quality=0)
        assert updated.ease_factor >= 1.3

    def test_wrong_answer_resets_repetitions(self):
        card = CardState(item_id="lesson-1", ease_factor=2.5, interval=10, repetitions=5)
        updated = calculate_next_review(card, quality=2)
        assert updated.repetitions == 0
        assert updated.interval == 1

    def test_first_correct_answer_sets_interval_1(self):
        card = CardState(item_id="lesson-1")
        updated = calculate_next_review(card, quality=4)
        assert updated.interval == 1
        assert updated.repetitions == 1

    def test_second_correct_answer_sets_interval_6(self):
        card = CardState(item_id="lesson-1", repetitions=1, interval=1)
        updated = calculate_next_review(card, quality=4)
        assert updated.interval == 6

    def test_next_review_is_in_future(self):
        from datetime import datetime
        card = CardState(item_id="lesson-1")
        updated = calculate_next_review(card, quality=5)
        assert updated.next_review > datetime.now()
```

**Step 2: Run to verify they pass**

```bash
pytest tests/test_spaced_repetition.py -v
```

Expected: all pass.

**Step 3: Write `tests/test_streak.py`**

```python
from datetime import datetime, timedelta
import pytest
from german_tutor.curriculum.streak import calculate_streak


class TestCalculateStreak:
    def test_studied_today_keeps_streak(self):
        today = datetime.now()
        assert calculate_streak(today, 5) == 5

    def test_studied_yesterday_increments_streak(self):
        yesterday = datetime.now() - timedelta(days=1)
        assert calculate_streak(yesterday, 5) == 6

    def test_missed_day_resets_streak(self):
        two_days_ago = datetime.now() - timedelta(days=2)
        assert calculate_streak(two_days_ago, 10) == 1

    def test_none_last_session_returns_1(self):
        assert calculate_streak(None, 0) == 1
```

Run: `pytest tests/test_streak.py -v`

**Step 4: Write `tests/test_cefr.py`**

```python
import pytest
from german_tutor.curriculum.cefr import CEFRProgressionEngine
from german_tutor.models.lesson import CEFRLevel


class TestCEFRProgressionEngine:
    def setup_method(self):
        self.engine = CEFRProgressionEngine()

    def test_can_advance_when_avg_mastery_above_threshold(self):
        scores = {"l1": 0.8, "l2": 0.9, "l3": 0.76}
        assert self.engine.can_advance(scores) is True

    def test_cannot_advance_when_avg_mastery_below_threshold(self):
        scores = {"l1": 0.5, "l2": 0.6, "l3": 0.7}
        assert self.engine.can_advance(scores) is False

    def test_cannot_advance_with_empty_scores(self):
        assert self.engine.can_advance({}) is False

    def test_next_level_from_a1_is_a2(self):
        assert self.engine.next_level(CEFRLevel.A1) == CEFRLevel.A2

    def test_next_level_from_a2_is_b1(self):
        assert self.engine.next_level(CEFRLevel.A2) == CEFRLevel.B1

    def test_progress_percent_scales_correctly(self):
        scores = {"l1": 0.5, "l2": 1.0}  # avg 0.75 → 100% of threshold
        pct = self.engine.progress_percent(scores)
        assert 0.0 <= pct <= 100.0
```

Run: `pytest tests/test_cefr.py -v`

**Step 5: Commit**

```bash
git add tests/test_spaced_repetition.py tests/test_streak.py tests/test_cefr.py
git commit -m "test: add parametrized tests for SM-2, streak, and CEFR progression"
```

---

## Task 6: Add DB migration and repository tests

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_migrations.py`
- Create: `tests/test_progress_repo.py`

**Step 1: Create `tests/conftest.py`**

```python
import asyncio
import pytest
import aiosqlite
from german_tutor.db.migrations import run_migrations


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db():
    """In-memory SQLite database with all migrations applied."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await run_migrations(conn)
        yield conn
```

Note: requires `pytest-asyncio`. Add to `pyproject.toml` dev deps:
```toml
"pytest-asyncio>=0.24",
```
And add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Step 2: Write `tests/test_migrations.py`**

```python
import pytest
import aiosqlite
from german_tutor.db.migrations import run_migrations, MIGRATIONS


async def test_migrations_create_all_tables():
    async with aiosqlite.connect(":memory:") as db:
        db.row_factory = aiosqlite.Row
        await run_migrations(db)
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in await cursor.fetchall()}
    expected = {
        "learner", "lesson_progress", "quiz_sessions",
        "quiz_responses", "vocabulary_cards", "vocabulary_topic_progress",
        "schema_version",
    }
    assert expected.issubset(tables)


async def test_migrations_are_idempotent():
    """Running migrations twice must not raise."""
    async with aiosqlite.connect(":memory:") as db:
        await run_migrations(db)
        await run_migrations(db)  # second run must be a no-op


async def test_schema_version_tracks_all_migrations():
    async with aiosqlite.connect(":memory:") as db:
        await run_migrations(db)
        cursor = await db.execute("SELECT COUNT(*) FROM schema_version")
        count = (await cursor.fetchone())[0]
    assert count == len(MIGRATIONS)
```

Run: `pytest tests/test_migrations.py -v`

**Step 3: Write `tests/test_progress_repo.py`**

```python
import pytest
from datetime import datetime
from german_tutor.db.repositories.progress_repo import ProgressRepository
from german_tutor.models.lesson import LessonProgress
from german_tutor.models.session import QuizSession, QuizResponse


async def _seed_learner(db) -> int:
    cursor = await db.execute(
        "INSERT INTO learner (name, current_level) VALUES (?, ?) RETURNING id",
        ("Test User", "A1"),
    )
    row = await cursor.fetchone()
    await db.commit()
    return row[0]


async def test_upsert_lesson_progress_creates_row(db):
    learner_id = await _seed_learner(db)
    repo = ProgressRepository(db)
    progress = LessonProgress(
        learner_id=learner_id,
        lesson_id="a1-01",
        completed_at=datetime.now(),
        attempts=1,
        last_score=0.8,
        mastery_score=0.8,
    )
    await repo.upsert_lesson_progress(progress)
    result = await repo.get_lesson_progress(learner_id, "a1-01")
    assert result is not None
    assert result.mastery_score == pytest.approx(0.8)


async def test_upsert_lesson_progress_increments_attempts(db):
    learner_id = await _seed_learner(db)
    repo = ProgressRepository(db)
    progress = LessonProgress(
        learner_id=learner_id, lesson_id="a1-02",
        completed_at=datetime.now(), attempts=1,
        last_score=0.5, mastery_score=0.5,
    )
    await repo.upsert_lesson_progress(progress)
    await repo.upsert_lesson_progress(progress)
    result = await repo.get_lesson_progress(learner_id, "a1-02")
    assert result.attempts == 2  # DB increments via attempts + 1


async def test_create_and_complete_session(db):
    learner_id = await _seed_learner(db)
    repo = ProgressRepository(db)
    session = QuizSession(
        learner_id=learner_id,
        lesson_id="a1-01",
        started_at=datetime.now(),
        total_questions=5,
    )
    session_id = await repo.create_session(session)
    assert isinstance(session_id, int)
    await repo.complete_session(session_id, correct=4, total=5, score=0.8, feedback={})
    recent = await repo.get_recent_sessions(learner_id, limit=1)
    assert recent[0]["score"] == pytest.approx(0.8)


async def test_upsert_vocab_cards_bulk_skips_duplicates(db):
    learner_id = await _seed_learner(db)
    repo = ProgressRepository(db)
    entries = [("Hund", "dog", "A1"), ("Katze", "cat", "A1")]
    await repo.upsert_vocab_cards_bulk(learner_id, entries)
    await repo.upsert_vocab_cards_bulk(learner_id, entries)  # must not raise
    cursor = await db.execute(
        "SELECT COUNT(*) FROM vocabulary_cards WHERE learner_id = ?", (learner_id,)
    )
    count = (await cursor.fetchone())[0]
    assert count == 2
```

Run: `pytest tests/test_progress_repo.py -v`

**Step 4: Commit**

```bash
git add tests/conftest.py tests/test_migrations.py tests/test_progress_repo.py pyproject.toml
git commit -m "test: add DB migration and repository integration tests with in-memory SQLite"
```

---

## Task 7: Fix type annotations and deprecated imports

Minor cleanup but makes type checking usable.

**Files:**
- Modify: `src/german_tutor/screens/vocab_topics.py:3–4`
- Modify: `src/german_tutor/screens/results.py:24–25`
- Modify: `src/german_tutor/screens/quiz.py:24–25`
- Modify: `src/german_tutor/main.py:185,217`
- Modify: `src/german_tutor/quiz.py:64–65` (remove duplicate imports)

**Step 1: Fix deprecated `typing` imports in `vocab_topics.py`**

```python
# Remove:
from typing import Dict, List, Set

# Replace all uses in the file:
#   List[VocabTopic]  →  list[VocabTopic]
#   Dict[str, dict]   →  dict[str, dict]
#   Set[int]          →  set[int]
```

**Step 2: Add types to screen constructors**

In `results.py`:
```python
from german_tutor.db.repositories.progress_repo import ProgressRepository
from german_tutor.llm.curriculum_agent import CurriculumAgent

# Constructor:
curriculum_agent: CurriculumAgent | None = None,
progress_repo: ProgressRepository | None = None,
```

In `quiz.py`:
```python
from german_tutor.db.repositories.progress_repo import ProgressRepository
from german_tutor.llm.quiz_agent import QuizAgent

# Constructor:
quiz_agent: QuizAgent | None = None,
progress_repo: ProgressRepository | None = None,
```

**Step 3: Add return type and parameter types to untyped methods in `main.py`**

```python
async def _show_results(self, session: QuizSession, lesson: Lesson) -> None:

def _get_current_lesson(self) -> Lesson | None:
```

**Step 4: Remove duplicate imports in `quiz.py:64–65`**

Delete these two lines from inside `on_mount`:
```python
from german_tutor.models.session import QuizSession as QS
from datetime import datetime
```
Change `QS(` to `QuizSession(` on the line below (it's already imported at the top as `QuizSession`).

**Step 5: Remove stale comment in `main.py:90`**

```python
# Remove the "# Remove await" comment
current_lesson = self._get_current_lesson()
```

**Step 6: Commit**

```bash
git add src/german_tutor/screens/vocab_topics.py \
        src/german_tutor/screens/results.py \
        src/german_tutor/screens/quiz.py \
        src/german_tutor/main.py
git commit -m "chore: fix deprecated typing imports, add missing type annotations, remove stale comment"
```

---

## Task 8: Replace magic numbers and hard-coded level list

**Files:**
- Modify: `src/german_tutor/screens/results.py`
- Modify: `src/german_tutor/screens/quiz.py`
- Modify: `src/german_tutor/main.py:122`

**Step 1: Add constants to `results.py`**

At module level, below imports:
```python
_GRADE_EXCELLENT_THRESHOLD = 85
_GRADE_GOOD_THRESHOLD = 60
_HISTORY_LIMIT = 5
```

Replace the grade comparison in `compose`:
```python
grade_class = (
    "score-excellent"
    if pct >= _GRADE_EXCELLENT_THRESHOLD
    else "score-good"
    if pct >= _GRADE_GOOD_THRESHOLD
    else "score-needs-review"
)
```

Replace `limit=5` in `_run_ai_analysis`:
```python
history = await self.progress_repo.get_recent_sessions(
    self.learner.id, limit=_HISTORY_LIMIT
)
```

**Step 2: Add constants to `quiz.py`**

```python
_MAX_FALLBACK_QUESTIONS = 5
_ANSWER_ADVANCE_DELAY_SECS = 1.5
```

Replace `[:5]` on line 97 and `1.5` on line 228.

**Step 3: Fix hard-coded level list in `main.py`**

```python
# Remove:
for level in ["A1", "A2", "B1"]:

# Replace with:
from german_tutor.models.lesson import CEFRLevel
for level in [l.value for l in CEFRLevel]:
```

**Step 4: Commit**

```bash
git add src/german_tutor/screens/results.py \
        src/german_tutor/screens/quiz.py \
        src/german_tutor/main.py
git commit -m "chore: replace magic numbers with named constants, use CEFRLevel enum for level iteration"
```

---

## Execution Order Summary

| # | Task | Severity | Effort |
|---|------|----------|--------|
| 1 | Decouple results side effects from LLM | critical | small |
| 2 | Fix SM-2 ease_factor persistence | critical | medium |
| 3 | Fix settings path + asyncio.create_task | major | small |
| 4 | Batch vocab card upserts | major | small |
| 5 | Tests: pure functions | major | small |
| 6 | Tests: DB migrations + repositories | major | medium |
| 7 | Type annotations + deprecated imports | minor | small |
| 8 | Magic numbers + hard-coded level list | minor | small |

Do tasks 1 and 2 first — they are the only ones with data integrity consequences.
