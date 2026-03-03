from __future__ import annotations

from german_tutor.curriculum.cefr import CEFRProgressionEngine
from german_tutor.curriculum.loader import CurriculumLoader
from german_tutor.db.repositories.learner_repo import LearnerRepository
from german_tutor.db.repositories.progress_repo import ProgressRepository
from german_tutor.llm.client import OllamaClient
from german_tutor.llm.curriculum_agent import CurriculumAgent
from german_tutor.llm.quiz_agent import QuizAgent
from german_tutor.llm.tutor_agent import TutorAgent
from german_tutor.models.learner import Learner


class AppState:
    """Singleton holding all shared application resources.

    Created once at startup and passed into screens that need it.
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        learner_repo: LearnerRepository,
        progress_repo: ProgressRepository,
        curriculum_loader: CurriculumLoader,
        curriculum_agent: CurriculumAgent,
        tutor_agent: TutorAgent,
        quiz_agent: QuizAgent,
        cefr_engine: CEFRProgressionEngine,
        current_learner: Learner | None = None,
    ) -> None:
        self.ollama_client = ollama_client
        self.learner_repo = learner_repo
        self.progress_repo = progress_repo
        self.curriculum_loader = curriculum_loader
        self.curriculum_agent = curriculum_agent
        self.tutor_agent = tutor_agent
        self.quiz_agent = quiz_agent
        self.cefr_engine = cefr_engine
        self.current_learner = current_learner
