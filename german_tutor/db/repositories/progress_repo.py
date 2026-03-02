from __future__ import annotations

import json
from datetime import datetime

import aiosqlite

from german_tutor.models.lesson import LessonProgress
from german_tutor.models.session import QuizResponse, QuizSession


class ProgressRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    # ── Lesson Progress ────────────────────────────────────────────────────────

    async def upsert_lesson_progress(self, progress: LessonProgress) -> None:
        await self.db.execute(
            """
            INSERT INTO lesson_progress
                (learner_id, lesson_id, completed_at, attempts, last_score, mastery_score, next_review)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(learner_id, lesson_id) DO UPDATE SET
                completed_at   = excluded.completed_at,
                attempts       = lesson_progress.attempts + 1,
                last_score     = excluded.last_score,
                mastery_score  = excluded.mastery_score,
                next_review    = excluded.next_review
            """,
            (
                progress.learner_id,
                progress.lesson_id,
                progress.completed_at.isoformat() if progress.completed_at else None,
                progress.attempts,
                progress.last_score,
                progress.mastery_score,
                progress.next_review.isoformat() if progress.next_review else None,
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

    # ── Quiz Responses ─────────────────────────────────────────────────────────

    async def save_response(self, response: QuizResponse) -> None:
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
        await self.db.commit()

    async def get_session_responses(self, session_id: int) -> list[QuizResponse]:
        async with self.db.execute(
            "SELECT * FROM quiz_responses WHERE session_id = ?", (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [QuizResponse(**dict(r)) for r in rows]

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
