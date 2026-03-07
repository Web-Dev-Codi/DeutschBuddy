from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite

from deutschbuddy.models.lesson import LessonProgress
from deutschbuddy.models.session import QuizResponse, QuizSession


class ProgressRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    # ── Lesson Progress ────────────────────────────────────────────────────────

    async def upsert_lesson_progress(self, progress: LessonProgress) -> None:
        await self.db.execute(
            """
            INSERT INTO lesson_progress
                (learner_id, lesson_id, completed_at, attempts, last_score, mastery_score, next_review, ease_factor)
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

    async def get_lesson_progress(
        self, learner_id: int, lesson_id: str
    ) -> LessonProgress | None:
        async with self.db.execute(
            "SELECT * FROM lesson_progress WHERE learner_id = ? AND lesson_id = ?",
            (learner_id, lesson_id),
        ) as cursor:
            row = await cursor.fetchone()
        return LessonProgress(**dict(row)) if row else None

    async def get_all_progress(self, learner_id: int) -> list[LessonProgress]:
        async with self.db.execute(
            "SELECT * FROM lesson_progress WHERE learner_id = ?", (learner_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [LessonProgress(**dict(r)) for r in rows]

    async def get_mastery_scores(self, learner_id: int, lesson_ids: list[str]) -> dict[str, float]:
        """Get mastery scores for a list of lesson IDs. Returns 0.0 for missing lessons."""
        if not lesson_ids:
            return {}
        
        placeholders = ",".join("?" for _ in lesson_ids)
        async with self.db.execute(
            f"SELECT lesson_id, mastery_score FROM lesson_progress WHERE learner_id = ? AND lesson_id IN ({placeholders})",
            (learner_id, *lesson_ids),
        ) as cursor:
            rows = await cursor.fetchall()
        
        # Convert to dict and fill missing with 0.0
        result = {lesson_id: 0.0 for lesson_id in lesson_ids}
        result.update({row[0]: row[1] for row in rows})
        return result

    async def get_due_reviews(
        self, learner_id: int, today: datetime
    ) -> list[LessonProgress]:
        async with self.db.execute(
            "SELECT * FROM lesson_progress WHERE learner_id = ? AND next_review <= ?",
            (learner_id, today.isoformat()),
        ) as cursor:
            rows = await cursor.fetchall()
        return [LessonProgress(**dict(r)) for r in rows]

    # ── Quiz Sessions ──────────────────────────────────────────────────────────

    async def create_session(self, session: QuizSession) -> int:
        async with self.db.execute(
            """
            INSERT INTO quiz_sessions (learner_id, lesson_id, started_at, total_questions)
            VALUES (?, ?, ?, ?)
            """,
            (
                session.learner_id,
                session.lesson_id,
                (session.started_at or datetime.now()).isoformat(),
                session.total_questions,
            ),
        ) as cursor:
            rowid = cursor.lastrowid
        await self.db.commit()
        return rowid  # type: ignore[return-value]

    async def complete_session(
        self,
        session_id: int,
        correct: int,
        total: int,
        score: float,
        feedback: dict,
    ) -> None:
        await self.db.execute(
            """
            UPDATE quiz_sessions
            SET completed_at = ?, correct_answers = ?, total_questions = ?,
                score = ?, llm_feedback = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(),
                correct,
                total,
                score,
                json.dumps(feedback),
                session_id,
            ),
        )
        await self.db.commit()

    async def get_recent_sessions(self, learner_id: int, limit: int = 10) -> list[dict]:
        # Note: llm_feedback values in returned dicts are raw JSON strings.
        # Callers must json.loads() them if dict access is needed.
        async with self.db.execute(
            """
            SELECT qs.*, lp.mastery_score
            FROM quiz_sessions qs
            LEFT JOIN lesson_progress lp
                ON lp.lesson_id = qs.lesson_id AND lp.learner_id = qs.learner_id
            WHERE qs.learner_id = ?
            ORDER BY qs.started_at DESC
            LIMIT ?
            """,
            (learner_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def count_vocab_cards(self, learner_id: int) -> int:
        async with self.db.execute(
            "SELECT COUNT(*) FROM vocabulary_cards WHERE learner_id = ?",
            (learner_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    # ── Quiz Responses ─────────────────────────────────────────────────────────

    async def save_response(self, response: QuizResponse) -> None:
        """Insert a quiz response row. Caller must commit the surrounding transaction."""
        await self.db.execute(
            """
            INSERT INTO quiz_responses
                (session_id, question_id, user_answer, is_correct, time_taken_seconds, llm_evaluation)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                response.session_id,
                response.question_id,
                response.user_answer,
                response.is_correct,
                response.time_taken_seconds,
                json.dumps(response.llm_evaluation)
                if response.llm_evaluation
                else None,
            ),
        )
        # No commit here — batched with complete_session

    async def get_session_responses(self, session_id: int) -> list[QuizResponse]:
        async with self.db.execute(
            "SELECT * FROM quiz_responses WHERE session_id = ?", (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("llm_evaluation"):
                d["llm_evaluation"] = json.loads(d["llm_evaluation"])
            result.append(QuizResponse(**d))
        return result

    # ── Vocabulary Cards ───────────────────────────────────────────────────────

    async def upsert_vocab_card(
        self, learner_id: int, german: str, english: str, level: str
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO vocabulary_cards (learner_id, german_word, english_word, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(learner_id, german_word) DO NOTHING
            """,
            (learner_id, german, english, level),
        )
        await self.db.commit()

    async def upsert_vocab_cards_bulk(
        self,
        learner_id: int,
        entries: list[tuple[str, str, str]],
    ) -> None:
        if not entries:
            return
        await self.db.executemany(
            """
            INSERT INTO vocabulary_cards (learner_id, german_word, english_word, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(learner_id, german_word) DO NOTHING
            """,
            [(learner_id, german, english, level) for (german, english, level) in entries],
        )
        await self.db.commit()

    async def update_vocab_card_sm2(
        self,
        card_id: int,
        ease: float,
        interval: int,
        reps: int,
        next_review: datetime,
    ) -> None:
        await self.db.execute(
            """
            UPDATE vocabulary_cards
            SET ease_factor = ?, interval_days = ?, repetitions = ?, next_review = ?
            WHERE id = ?
            """,
            (ease, interval, reps, next_review.isoformat(), card_id),
        )
        await self.db.commit()

    async def get_due_vocab_cards(
        self, learner_id: int, today: datetime, limit: int = 20
    ) -> list[dict]:
        async with self.db.execute(
            """
            SELECT * FROM vocabulary_cards
            WHERE learner_id = ? AND (next_review IS NULL OR next_review <= ?)
            ORDER BY next_review ASC
            LIMIT ?
            """,
            (learner_id, today.isoformat(), limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_today_session_minutes(self, learner_id: int) -> float:
        """Get total minutes spent in quiz sessions today."""
        async with self.db.execute(
            """
            SELECT SUM((julianday(completed_at) - julianday(started_at)) * 1440) as total_minutes
            FROM quiz_sessions 
            WHERE learner_id = ? 
            AND date(completed_at) = date('now') 
            AND completed_at IS NOT NULL
            """,
            (learner_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0

    async def update_vocab_card_gender(self, card_id: int, gender: str) -> None:
        """Update the gender field for a vocabulary card."""
        await self.db.execute(
            "UPDATE vocabulary_cards SET gender = ? WHERE id = ?",
            (gender, card_id),
        )
        await self.db.commit()

    async def get_cards_for_gender_drill(self, learner_id: int, limit: int = 20) -> list[dict]:
        """Get vocabulary cards suitable for gender drill practice."""
        async with self.db.execute(
            """
            SELECT * FROM vocabulary_cards 
            WHERE learner_id = ? 
            AND (german_word LIKE UPPER(substr(german_word, 1, 1)) || '%' OR gender IS NOT NULL)
            ORDER BY next_review ASC
            LIMIT ?
            """,
            (learner_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Vocabulary Topic Progress ─────────────────────────────────────────────

    async def upsert_vocab_topic_progress(
        self,
        learner_id: int,
        topic_id: str,
        topic_level: str,
        total_words: int,
        words_seen: int,
        completed_percent: float,
        current_word_index: int,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO vocabulary_topic_progress
                (learner_id, topic_id, topic_level, total_words, words_seen, completed_percent, current_word_index, last_interacted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(learner_id, topic_id) DO UPDATE SET
                total_words = excluded.total_words,
                words_seen = excluded.words_seen,
                completed_percent = excluded.completed_percent,
                current_word_index = excluded.current_word_index,
                last_interacted_at = datetime('now')
            """,
            (
                learner_id,
                topic_id,
                topic_level,
                total_words,
                words_seen,
                completed_percent,
                current_word_index,
            ),
        )
        await self.db.commit()

    async def get_vocab_topic_progress_map(
        self, learner_id: int, topic_ids: list[str]
    ) -> dict[str, dict]:
        if not topic_ids:
            return {}
        placeholders = ",".join("?" for _ in topic_ids)
        async with self.db.execute(
            f"""
            SELECT * FROM vocabulary_topic_progress
            WHERE learner_id = ? AND topic_id IN ({placeholders})
            """,
            (learner_id, *topic_ids),
        ) as cursor:
            rows = await cursor.fetchall()
        return {row["topic_id"]: dict(row) for row in rows}

    async def get_latest_vocab_topic_progress(self, learner_id: int) -> dict[str, Any] | None:
        async with self.db.execute(
            """
            SELECT *
            FROM vocabulary_topic_progress
            WHERE learner_id = ?
            ORDER BY datetime(last_interacted_at) DESC
            LIMIT 1
            """,
            (learner_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_vocab_topic_summary(self, learner_id: int) -> dict[str, int]:
        async with self.db.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN completed_percent >= 100 THEN 1 ELSE 0 END) as completed
            FROM vocabulary_topic_progress
            WHERE learner_id = ?
            """,
            (learner_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return {"total": 0, "completed": 0}
        return {"total": row["total"], "completed": row["completed"] or 0}

    async def reset_vocab_topic_progress(self, learner_id: int) -> None:
        await self.db.execute(
            "DELETE FROM vocabulary_topic_progress WHERE learner_id = ?",
            (learner_id,),
        )
        await self.db.commit()
