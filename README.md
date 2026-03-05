# deutschbuddy

AI-powered German language tutor designed specifically for English speakers who want to learn German quickly and effectively.

## Goal

deutschbuddy helps English speakers achieve conversational fluency in German through personalized, AI-driven lessons that adapt to your learning pace and style. The app focuses on practical language skills you'll actually use in real-world conversations.

## How It Helps You Learn German Fast

- **Personalized Learning Path**: The AI curriculum agent analyzes your performance and recommends lessons that target your specific weaknesses, ensuring you spend time on what you need most
- **Spaced Repetition System**: Automatically schedules vocabulary and grammar reviews at optimal intervals to maximize retention
- **CEFR-Aligned Curriculum**: Progress through structured levels (A1 → B1) with lessons designed for rapid progression
- **Interactive Practice**: Engage in conversations, quizzes, and exercises that build practical communication skills
- **Immediate Feedback**: Get instant corrections and explanations from AI tutors to reinforce proper grammar and vocabulary usage
- **Focused on English Speakers**: Lessons specifically address common challenges English speakers face when learning German (cases, word order, gendered nouns)

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) running locally
- Required models:

  ```bash
  ollama pull llama3.1:8b-instruct
  ollama pull mistral:7b-instruct
  ```

### Installation

```bash
git clone https://github.com/Web-Dev-Codi/deutschbuddy.git
cd deutschbuddy
uv sync
```

### Run

```bash
uv run german-tutor
```

## GPU Setup (AMD RX 7800 XT / ROCm)

Ollama supports AMD GPUs via ROCm. To enable hardware acceleration on an RX 7800 XT:

1. **Install ROCm** (Ubuntu/Arch):

   ```bash
   # Ubuntu 22.04 / 24.04
   sudo apt install rocm-hip-sdk
   ```

   Follow [AMD's ROCm install guide](https://rocm.docs.amd.com/en/latest/deploy/linux/index.html) for your distro.

2. **Verify GPU visibility:**

   ```bash
   rocm-smi
   ```

3. **Run Ollama with ROCm:**
   Ollama detects ROCm automatically when `rocm` libraries are installed. Optionally force GPU selection:

   ```bash
   export HSA_OVERRIDE_GFX_VERSION=11.0.2   # RX 7800 XT (gfx1101 / RDNA3)
   ollama serve
   ```

4. **Environment variables:**

   | Variable | Purpose |
   |----------|---------|
   | `HSA_OVERRIDE_GFX_VERSION` | Override GPU architecture string (use `11.0.2` for RX 7800 XT / gfx1101 RDNA3) |
   | `OLLAMA_GPU_OVERHEAD` | Reserved VRAM in bytes (tune if OOM) |
   | `OLLAMA_NUM_GPU` | Number of GPU layers to offload |

   For an RX 7800 XT (16 GB VRAM), `llama3.1:8b` and `mistral:7b` will fully load on-device.

## Architecture

deutschbuddy uses a **dual-layer curriculum system** that combines static content with dynamic AI guidance:

### YAML Curriculum Files (Content Library)
- **Location**: `data/curriculum/A1/`, `data/curriculum/A2/`, `data/curriculum/B1/`
- **Purpose**: Store lesson content, grammar explanations, vocabulary, and examples
- **Structure**: Each lesson file contains:
  - Lesson metadata (ID, title, level, prerequisites)
  - Grammar explanations and English comparisons
  - Example sentences with translations
  - Practice exercises and vocabulary lists
- **Benefits**: Reliable, version-controlled content that can be reviewed and edited

### AI Curriculum Agent (Learning Strategist)
- **Purpose**: Make intelligent decisions about learning progression
- **Responsibilities**:
  - Analyze learner performance and mastery scores
  - Recommend the optimal next lesson based on individual needs
  - Determine when to advance between CEFR levels (A1 → A2 → B1)
  - Provide personalized learning paths based on strengths and weaknesses
- **Integration**: Works with the YAML content library but doesn't create content

### How They Work Together
1. **Learner completes a lesson/quiz** → Performance data is collected
2. **AI analyzes progress** → Identifies knowledge gaps and strengths  
3. **AI recommends specific lesson** → "Study A1-GRM-015 (Accusative Prepositions) because you're strong with nominative case"
4. **YAML file provides content** → Static lesson content is loaded and displayed
5. **Learner studies** → Cycle repeats with new performance data

This separation ensures:
- **Consistent, high-quality content** (YAML files)
- **Personalized learning paths** (AI recommendations)
- **Reliable offline capability** (YAML content works without AI)
- **Adaptive difficulty** (AI adjusts pacing based on performance)

## Settings

Open the Settings screen by pressing `s` on the home screen, or navigating to **Settings** in the sidebar.

From there you can:

- **Curriculum model** — Ollama model used for lesson recommendations and CEFR progression (default: `llama3.1:8b-instruct`)
- **Interaction model** — Ollama model used for quiz generation and tutoring (default: `mistral:7b-instruct`)
- **Ollama host** — URL of your Ollama instance (default: `http://localhost:11434`)

Settings are persisted to `config/settings.toml`.

## CEFR Levels

deutschbuddy follows the Common European Framework of Reference for Languages:

| Level | Description | Lessons |
|-------|-------------|---------|
| A1 | Beginner — basic greetings, definite/indefinite articles, simple present tense verbs | 20 lessons |
| A2 | Elementary — past tenses (Perfekt), modal verbs, nominative/accusative cases | 15 lessons |
| B1 | Intermediate — passive voice, Konjunktiv II, dative/genitive cases, complex clauses | 10 lessons |

Progress through levels is tracked automatically. The AI curriculum agent recommends lessons based on your performance history and spaced-repetition review schedule.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `h` | Home (return to dashboard) |
| `?` | Toggle help overlay |
| `Ctrl+R` | Review queue (due vocabulary cards) |
| `Escape` | Back / Close |

**On the Home screen:**

| Key | Action |
|-----|--------|
| `l` | Lessons |
| `p` | Progress |
| `r` | Review |
| `s` | Settings |
