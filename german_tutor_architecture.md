# 🇩🇪 GermanTutor — Textual TUI App with Ollama LLM
## Architecture & Design Document

---

## 1. Project Overview

A terminal-based German language learning application built with Python's Textual framework, powered by a local Ollama LLM. The app targets English-native speakers progressing from A1 → B1, using AI-driven adaptive learning to sequence content intelligently based on individual performance.

---

## 2. Recommended Tech Stack

| Layer | Tool | Why |
|---|---|---|
| **TUI Framework** | `Textual 0.60+` | Rich widgets, async-native, CSS theming |
| **LLM Runtime** | `Ollama` (local) | Privacy, offline-capable, AMD ROCm support |
| **Recommended Model** | `mistral:7b` or `llama3.1:8b` | Balance of speed & quality on RX 7800 XT |
| **Data Persistence** | `SQLite` via `aiosqlite` | Lightweight, zero-config, async-compatible |
| **ORM / Query** | `aiosqlite` + raw SQL or `Tortoise-ORM` | Async-first |
| **Ollama Client** | `ollama` Python SDK | Official async client |
| **Config** | `TOML` + `tomllib` (stdlib 3.11+) | Simple, readable |
| **Packaging** | `uv` + `pyproject.toml` | Modern, fast |

---

## 3. Recommended Ollama Models

For your RX 7800 XT (16GB VRAM) with ROCm:

```
# Best for structured teaching + German grammar
mistral:7b-instruct        # Fast, excellent instruction following
llama3.1:8b-instruct       # Strong multilingual, good English<>German cross-ref
aya:8b                     # Cohere's multilingual model, strong for language tasks

# Fallback / lightweight
gemma2:2b                  # Extremely fast for simple quizzes
```

**Architecture tip:** Use **two model roles** via Ollama:
- **Curriculum Model** (`llama3.1:8b`) — decides what to teach next (heavier reasoning)
- **Interaction Model** (`mistral:7b`) — generates quiz questions, feedback (fast responses)

---

## 4. Project Structure

```
german_tutor/
├── pyproject.toml
├── README.md
├── .env.example
├── config/
│   └── settings.toml          # Model names, CEFR config, Ollama URL
├── data/
│   ├── curriculum/            # Static YAML lesson definitions
│   │   ├── A1/
│   │   │   ├── 01_greetings.yaml
│   │   │   ├── 02_articles_nominative.yaml
│   │   │   └── ...
│   │   ├── A2/
│   │   └── B1/
│   └── db/
│       └── learner.db         # SQLite — progress, scores, session history
├── german_tutor/
│   ├── __init__.py
│   ├── main.py                # Textual App entry point
│   ├── models/                # Data models (dataclasses / Pydantic)
│   │   ├── learner.py
│   │   ├── lesson.py
│   │   └── session.py
│   ├── db/
│   │   ├── connection.py      # aiosqlite pool
│   │   ├── migrations.py      # Schema setup
│   │   └── repositories/
│   │       ├── learner_repo.py
│   │       └── progress_repo.py
│   ├── llm/
│   │   ├── client.py          # Ollama async client wrapper
│   │   ├── curriculum_agent.py # Decides next lesson (adaptive logic)
│   │   ├── tutor_agent.py     # Explains grammar, generates feedback
│   │   └── quiz_agent.py      # Generates + evaluates quiz questions
│   ├── curriculum/
│   │   ├── loader.py          # Parses YAML lesson files
│   │   ├── cefr.py            # A1/A2/B1 progression logic
│   │   └── spaced_repetition.py # SM-2 algorithm implementation
│   ├── screens/
│   │   ├── home.py            # Dashboard / level overview
│   │   ├── lesson.py          # Grammar lesson view
│   │   ├── quiz.py            # Quiz modal screen
│   │   ├── results.py         # Performance analysis screen
│   │   ├── breakdown.py       # Sentence structure breakdown view
│   │   └── settings.py        # Model selection, preferences
│   ├── widgets/
│   │   ├── grammar_panel.py   # Side-by-side EN↔DE grammar display
│   │   ├── sentence_tree.py   # Grammatical tree breakdown widget
│   │   ├── progress_bar.py    # CEFR level progress
│   │   ├── streak_indicator.py
│   │   └── quiz_card.py       # Individual quiz question widget
│   └── styles/
│       ├── main.tcss          # Textual CSS
│       └── theme.tcss
└── tests/
    ├── test_llm/
    ├── test_curriculum/
    └── test_db/
```

---

## 5. Core Architecture Patterns

### 5.1 Adaptive Curriculum Agent

The LLM acts as a **curriculum planner**, not just a content generator. After each quiz, it receives the learner's performance history and decides what to present next.

```python
# llm/curriculum_agent.py

CURRICULUM_SYSTEM_PROMPT = """
You are a German language curriculum planner for English-native speakers.
Your job is to analyze a learner's performance history and select the most
beneficial next lesson topic from the available curriculum.

Rules:
- If accuracy < 60% on a topic, recommend revisiting it before advancing
- Introduce new grammar concepts only after prerequisite topics score > 75%
- Interleave vocabulary and grammar lessons
- Always return a JSON object with: next_lesson_id, reason, difficulty_adjustment
"""

class CurriculumAgent:
    def __init__(self, client: OllamaClient, model: str = "llama3.1:8b"):
        self.client = client
        self.model = model

    async def recommend_next_lesson(
        self,
        performance_history: list[dict],
        available_lessons: list[Lesson],
        current_level: CEFRLevel
    ) -> LessonRecommendation:
        prompt = self._build_prompt(performance_history, available_lessons)
        response = await self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format="json"  # Ollama structured output
        )
        return LessonRecommendation.model_validate_json(response.message.content)
```

### 5.2 Grammar Breakdown Engine

The key feature — side-by-side EN↔DE grammatical analysis:

```python
# llm/tutor_agent.py

GRAMMAR_BREAKDOWN_PROMPT = """
You are a German grammar teacher for English speakers.
Given a German sentence, produce a detailed grammatical breakdown.

Return JSON with this structure:
{
  "german_sentence": "...",
  "english_translation": "...",
  "word_analysis": [
    {
      "german_word": "Das",
      "english_equivalent": "The",
      "part_of_speech": "definite article",
      "grammatical_role": "nominative, neuter, singular",
      "english_comparison": "English 'the' doesn't change — German articles change based on gender and case",
      "case": "Nominative",
      "gender": "Neuter"
    }
  ],
  "sentence_structure": {
    "german_pattern": "Subject + Verb + Object",
    "english_pattern": "Subject + Verb + Object",
    "key_difference": "German main clauses share SVO word order with English, BUT verbs move to position 2 when another element leads",
    "verb_position_note": "..."
  },
  "grammar_rules_applied": ["...", "..."],
  "common_mistakes_for_english_speakers": ["..."]
}
"""
```

### 5.3 Spaced Repetition (SM-2 Algorithm)

Integrate spaced repetition for vocabulary and grammar points:

```python
# curriculum/spaced_repetition.py
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CardState:
    item_id: str
    ease_factor: float = 2.5
    interval: int = 1           # days
    repetitions: int = 0
    next_review: datetime = None

def calculate_next_review(card: CardState, quality: int) -> CardState:
    """
    quality: 0-5 (0=blackout, 3=correct with difficulty, 5=perfect)
    SM-2 algorithm implementation
    """
    if quality < 3:
        card.repetitions = 0
        card.interval = 1
    else:
        if card.repetitions == 0:
            card.interval = 1
        elif card.repetitions == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.ease_factor)
        card.repetitions += 1

    card.ease_factor = max(
        1.3,
        card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    )
    card.next_review = datetime.now() + timedelta(days=card.interval)
    return card
```

---

## 6. CEFR Curriculum Structure (YAML Lessons)

```yaml
# data/curriculum/A1/02_articles_nominative.yaml
id: "A1-GRM-002"
level: "A1"
category: "grammar"
title: "Definite Articles — Nominative Case"
prerequisites: ["A1-GRM-001"]
estimated_minutes: 15
tags: ["articles", "nominative", "gender", "nouns"]

explanation:
  concept: |
    German has THREE grammatical genders: masculine (der), feminine (die),
    and neuter (das). Unlike English which uses only "the", German articles
    change based on gender AND grammatical case.
  
  english_comparison: |
    In English: "the dog", "the woman", "the house" — always "the"
    In German: "der Hund" (m), "die Frau" (f), "das Haus" (n)
    
    Think of German articles like "a/an" in English — English speakers
    already do this with vowel sounds. German just extends this logic
    to gender and case.

  table:
    title: "Nominative Articles (Subject of sentence)"
    headers: ["Gender", "Definite (the)", "Indefinite (a/an)", "Example"]
    rows:
      - ["Masculine", "der", "ein", "der Hund (the dog)"]
      - ["Feminine", "die", "eine", "die Katze (the cat)"]
      - ["Neuter", "das", "ein", "das Buch (the book)"]
      - ["Plural", "die", "—", "die Hunde (the dogs)"]

example_sentences:
  - german: "Der Mann liest ein Buch."
    english: "The man reads a book."
    breakdown_focus: "nominative masculine article"

quiz:
  questions:
    - type: "multiple_choice"
      question: "Which article is correct? ___ Hund ist groß."
      options: ["Der", "Die", "Das", "Den"]
      answer: "Der"
      explanation: "Hund (dog) is masculine, nominative case (subject) → 'der'"
    
    - type: "fill_blank"
      question: "Complete: ___ Frau trinkt Kaffee. (The woman drinks coffee)"
      answer: "Die"
      explanation: "Frau (woman) is feminine → 'die'"
    
    - type: "translation"
      question: "Translate: The book is on the table."
      answer: "Das Buch liegt auf dem Tisch."
      evaluation_type: "llm"   # LLM evaluates free-form answers
```

---

## 7. Textual Screen & Widget Architecture

### 7.1 App Layout

```
┌─────────────────────────────────────────────────────────┐
│  GermanTutor   [A1 ████████░░ 65%]  Streak: 🔥 7 days  │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  NAVIGATION  │         MAIN CONTENT AREA               │
│              │                                          │
│  📚 Lessons  │  ┌─── Lesson: Articles (Nominative) ──┐ │
│  🧠 Quiz     │  │                                    │ │
│  📊 Progress │  │  GERMAN        │  ENGLISH          │ │
│  🔁 Review   │  │  ─────────     │  ─────────        │ │
│  ⚙️  Settings │  │  der (m)      │  the (masc.)      │ │
│              │  │  die (f)       │  the (fem.)       │ │
│  ─────────── │  │  das (n)       │  the (neuter)     │ │
│              │  │                                    │ │
│  LEVEL: A1   │  │  [Example Sentence Breakdown]      │ │
│  Next: A2    │  │                                    │ │
│  Progress    │  └────────────────────────────────────┘ │
│  ████░░░ 70% │                                          │
│              │  [ Start Quiz ]  [ Next Lesson ]         │
└──────────────┴──────────────────────────────────────────┘
```

### 7.2 Quiz Modal

```
┌─────────────────── Quiz — A1 Articles ───────────────────┐
│                                                          │
│  Question 3 / 10          Score: 8/10  ████████░░        │
│                                                          │
│  Fill in the correct article:                            │
│                                                          │
│  "  ___  Katze schläft."                                 │
│  (The cat sleeps.)                                       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  ○  Der    ○  Die    ○  Das    ○  Den             │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  💡 Hint: Think about the gender of "Katze"              │
│                                                          │
│           [ Submit Answer ]   [ Skip ]                   │
└──────────────────────────────────────────────────────────┘
```

### 7.3 Sentence Breakdown Widget

```python
# widgets/grammar_panel.py
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import DataTable, Label, Static
from textual import on
from rich.table import Table
from rich.text import Text

class SentenceBreakdownWidget(Widget):
    """Displays a German sentence with grammatical breakdown."""

    DEFAULT_CSS = """
    SentenceBreakdownWidget {
        border: round $accent;
        padding: 1 2;
        height: auto;
    }
    .german-sentence { color: $warning; text-style: bold; }
    .english-sentence { color: $success; }
    .tag-nominative { color: $error; }
    .tag-accusative { color: $warning; }
    .tag-dative { color: $accent; }
    """

    def __init__(self, breakdown_data: dict):
        super().__init__()
        self.data = breakdown_data

    def compose(self) -> ComposeResult:
        yield Static(self.data["german_sentence"], classes="german-sentence")
        yield Static(self.data["english_translation"], classes="english-sentence")
        table = DataTable()
        table.add_columns("Word", "English", "Part of Speech", "Case/Role", "Note")
        for word in self.data["word_analysis"]:
            table.add_row(
                word["german_word"],
                word["english_equivalent"],
                word["part_of_speech"],
                word["grammatical_role"],
                word["english_comparison"][:50] + "..."
            )
        yield table
```

---

## 8. LLM Ollama Client (Async Streaming)

```python
# llm/client.py
import ollama
from typing import AsyncGenerator

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434"):
        self.client = ollama.AsyncClient(host=host)

    async def chat(self, model: str, messages: list, format: str = None) -> ollama.Message:
        response = await self.client.chat(
            model=model,
            messages=messages,
            format=format
        )
        return response.message

    async def stream_chat(
        self,
        model: str,
        messages: list
    ) -> AsyncGenerator[str, None]:
        """Stream tokens for real-time TUI display."""
        async for chunk in await self.client.chat(
            model=model,
            messages=messages,
            stream=True
        ):
            if chunk.message.content:
                yield chunk.message.content

    async def evaluate_answer(
        self,
        model: str,
        question: str,
        user_answer: str,
        correct_answer: str,
        context: str
    ) -> dict:
        """LLM grades free-form answers with explanation."""
        prompt = f"""
        Question: {question}
        Expected answer: {correct_answer}
        User's answer: {user_answer}
        Context: {context}

        Evaluate the user's answer. Return JSON:
        {{
          "is_correct": bool,
          "score": 0-100,
          "feedback": "short encouraging feedback",
          "explanation": "grammar explanation of why correct/incorrect",
          "english_comparison": "how this differs from English grammar"
        }}
        """
        return await self.chat(model=model, messages=[
            {"role": "user", "content": prompt}
        ], format="json")
```

---

## 9. Database Schema

```sql
-- Schema: data/db/schema.sql

CREATE TABLE learner (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    current_level TEXT DEFAULT 'A1',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lesson_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER REFERENCES learner(id),
    lesson_id TEXT NOT NULL,           -- e.g. "A1-GRM-002"
    completed_at DATETIME,
    attempts INTEGER DEFAULT 0,
    last_score REAL,                   -- 0.0 to 1.0
    mastery_score REAL DEFAULT 0.0,    -- weighted rolling average
    next_review DATETIME               -- spaced repetition
);

CREATE TABLE quiz_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id INTEGER REFERENCES learner(id),
    lesson_id TEXT NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    total_questions INTEGER,
    correct_answers INTEGER,
    score REAL,
    llm_feedback TEXT                  -- stored JSON from curriculum agent
);

CREATE TABLE quiz_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES quiz_sessions(id),
    question_id TEXT,
    user_answer TEXT,
    is_correct BOOLEAN,
    time_taken_seconds INTEGER,
    llm_evaluation TEXT               -- stored JSON feedback
);

CREATE TABLE vocabulary_cards (
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
```

---

## 10. Performance Analysis Screen

After each quiz session, the Curriculum Agent generates a performance report:

```python
# llm/curriculum_agent.py (analysis)

ANALYSIS_PROMPT = """
Analyze this German learner's quiz performance and provide:
1. Identified weak areas with specific grammar explanations
2. Common error patterns (e.g., always confusing accusative/dative)
3. Comparison to typical English-speaker errors at this level
4. Specific next 3 lessons recommended in order
5. Motivational summary

Performance data: {performance_json}
Current level: {level}
Session history (last 5): {history_json}

Return structured JSON for display in a TUI dashboard.
"""
```

**TUI Analysis View:**
```
┌──────────────── Session Results — A1 Quiz ────────────────┐
│                                                           │
│  Score: 7/10  ██████████░░░░  70%       🏅 Level: A1     │
│                                                           │
│  ✅ Strong Areas                                          │
│     • Definite articles (nominative) — 90%               │
│     • Basic SVO sentence structure — 85%                  │
│                                                           │
│  ⚠️  Needs Work                                           │
│     • Indefinite articles (kein/eine) — 50%              │
│     • Verb conjugation (sein/haben) — 60%                 │
│                                                           │
│  🤖 AI Analysis                                           │
│     "English speakers often confuse 'kein' with 'nicht'  │
│      because English uses 'not' for both. In German,      │
│      kein = not a/no (with nouns), nicht = not (other)"   │
│                                                           │
│  📚 Recommended Next                                      │
│     1. Negation: kein vs nicht (A1-GRM-008)              │
│     2. Review: Indefinite articles (A1-GRM-003)           │
│     3. Verb: sein & haben conjugation (A1-VRB-001)        │
│                                                           │
│  [ Review Mistakes ]  [ Next Lesson ]  [ Home ]           │
└───────────────────────────────────────────────────────────┘
```

---

## 11. Key Implementation Phases

### Phase 1 — Foundation (Week 1-2)
- Project scaffolding with `uv`, Textual app skeleton
- SQLite schema + `aiosqlite` repositories
- Ollama client wrapper with streaming support
- Basic home screen + navigation

### Phase 2 — Curriculum Engine (Week 3-4)
- YAML lesson loader (A1 content first — ~20 lessons)
- Static lesson display with grammar panels
- Side-by-side EN↔DE breakdown widget
- Basic quiz modal (multiple choice only)

### Phase 3 — AI Integration (Week 5-6)
- Curriculum Agent (lesson recommendation)
- Tutor Agent (grammar explanation generation)
- Quiz Agent (dynamic question generation + LLM evaluation)
- Performance analysis screen with AI feedback

### Phase 4 — Spaced Repetition & Polish (Week 7-8)
- SM-2 spaced repetition for vocabulary
- Streak tracking + progress dashboards
- A2 + B1 curriculum content
- Settings screen (model selection, preferences)

---

## 12. `pyproject.toml`

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
    "tomllib",          # stdlib 3.11+
]

[project.scripts]
german-tutor = "german_tutor.main:run"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "textual-dev>=0.1.0",  # Textual devtools
]
```

---

## 13. Quick Start Commands

```bash
# Setup
uv init german-tutor && cd german-tutor
uv add textual ollama aiosqlite pydantic pyyaml

# Pull Ollama models
ollama pull mistral:7b-instruct
ollama pull llama3.1:8b-instruct

# Run with Textual devtools (hot reload)
uv run textual run --dev german_tutor/main.py

# Run production
uv run german-tutor
```

---

## 14. AMD ROCm / RX 7800 XT Optimization Notes

```bash
# Verify ROCm Ollama is using GPU
ollama ps                             # Check GPU utilization

# In config/settings.toml
[ollama]
host = "http://localhost:11434"
curriculum_model = "llama3.1:8b-instruct"   # For adaptive decisions
interaction_model = "mistral:7b-instruct"   # For quiz/tutor (faster)
num_ctx = 4096                              # Context window
num_gpu = 1                                 # Force GPU layers

# For streaming in TUI — keep interaction model on GPU
# Curriculum model can share context since it's called less frequently
```

With your RX 7800 XT (16GB VRAM), you can comfortably run `mistral:7b` at full GPU with a 4096 context window, giving ~60-80 tokens/sec — fast enough for real-time TUI streaming.
