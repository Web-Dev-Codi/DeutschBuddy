# GermanTutor

AI-powered German language tutor for the terminal.

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
git clone https://github.com/Web-Dev-Codi/DeutschBuddy.git
cd DeutschBuddy
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

## Settings

Open the Settings screen by pressing `s` on the home screen, or navigating to **Settings** in the sidebar.

From there you can:

- **Curriculum model** — Ollama model used for lesson recommendations and CEFR progression (default: `llama3.1:8b-instruct`)
- **Interaction model** — Ollama model used for quiz generation and tutoring (default: `mistral:7b-instruct`)
- **Ollama host** — URL of your Ollama instance (default: `http://localhost:11434`)

Settings are persisted to `config/settings.toml`.

## CEFR Levels

GermanTutor follows the Common European Framework of Reference for Languages:

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
