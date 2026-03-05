<div align="center">

![deutschbuddy Logo](https://img.shields.io/badge/🇩🇪-deutschbuddy-FFD700?style=for-the-badge&logo=german&logoColor=black)

# 🎓 DeutschBuddy

**AI-Powered German Language Learning for English Speakers**

*Achieve conversational fluency with personalized, AI-driven lessons that adapt to your learning pace*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.ai)
[![CEFR A1→B1](https://img.shields.io/badge/CEFR-A1%E2%86%92B1-32A852?style=for-the-badge)](#cefr-levels)

[Quick Start](#-quick-start) • [Features](#-features) • [Architecture](#-architecture) • [GPU Setup](#-gpu-setup-amd-rx-7800-xt--rocm) • [Examples](#-examples) • [Contributing](#-contributing)

</div>

---

## 📖 About

**DeutschBuddy** helps English speakers achieve conversational fluency in German through personalized, AI-driven lessons that adapt to your learning pace and style. The app focuses on practical language skills you'll actually use in real-world conversations.

### 🎯 Why DeutschBuddy?

| Problem | DeutschBuddy Solution |
|---------|----------------------|
| Generic one-size-fits-all lessons | **Personalized Learning Path** adapted to your weaknesses |
| Forgetting vocabulary quickly | **Spaced Repetition System** for optimal retention |
| Unclear progression | **CEFR-Aligned Curriculum** (A1 → B1) |
| Passive learning | **Interactive Practice** with conversations & quizzes |
| Waiting for corrections | **Immediate AI Feedback** on grammar & vocabulary |
| Struggling with German grammar | **English-Focused** lessons addressing common pain points |

---

## ✨ Features

> 🧠 **AI-Powered Learning**

- **Personalized Learning Path**: AI curriculum agent analyzes your performance and recommends lessons targeting your specific weaknesses
- **Spaced Repetition System**: Automatically schedules vocabulary and grammar reviews at optimal intervals
- **Dual-Layer Curriculum**: Static YAML content + dynamic AI guidance for reliable, adaptive learning

> 📚 **Structured Content**

- **CEFR-Aligned Levels**: Progress through A1 → A2 → B1 with confidence
- **Grammar Explanations**: Clear explanations with English comparisons
- **Practice Exercises**: Interactive quizzes and conversations with instant feedback

> 🎮 **Interactive Interface**

- **TUI Dashboard**: Beautiful terminal-based interface with keyboard navigation
- **Progress Tracking**: Visual mastery scores and completion statistics
- **Review Queue**: Targeted practice for vocabulary you're about to forget

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.11+
python --version  # Should be 3.11 or higher

# Ollama (https://ollama.ai)
ollama --version
```

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Web-Dev-Codi/deutschbuddy.git
cd deutschbuddy

# 2. Install dependencies with uv
uv sync

# 3. Pull required AI models
ollama pull llama3.1:8b-instruct
ollama pull mistral:7b-instruct

# 4. Launch DeutschBuddy
uv run deutschbuddy
```

<div align="center">

**Voilà!** 🎉 Press `l` to start your first lesson!

</div>

---

## 🏗️ Architecture

DeutschBuddy uses a **dual-layer curriculum system** combining static content with dynamic AI guidance:

```
┌─────────────────────────────────────────────────────────────────┐
│                       Learner completes lesson                  │
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              AI Curriculum Agent                        │   │
│  │  • Analyzes performance  • Identifies knowledge gaps    │   │
│  │  • Recommends next lesson • Adjusts difficulty          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           YAML Content Library                          │   │
│  │  • A1/ • A2/ • B1/ lesson files                         │   │
│  │  • Grammar • Vocabulary • Exercises                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│                    Learner studies → Repeat                      │
└─────────────────────────────────────────────────────────────────┘
```

### YAML Curriculum Files (Content Library)

| Location | Purpose |
|----------|---------|
| `data/curriculum/A1/` | Beginner: greetings, articles, present tense |
| `data/curriculum/A2/` | Elementary: past tenses, modal verbs, cases |
| `data/curriculum/B1/` | Intermediate: passive, Konjunktiv II, complex clauses |

### AI Curriculum Agent (Learning Strategist)

**Responsibilities:**
- 📊 Analyze learner performance and mastery scores
- 🎯 Recommend optimal next lessons based on individual needs
- 📈 Track CEFR level progression (A1 → A2 → B1)
- 🔄 Provide personalized paths based on strengths/weaknesses

---

## 🎮 Examples

### Personalized Recommendation

```
💡 Recommended Next Lesson: A1-GRM-015 (Accusative Prepositions)

Why this lesson?
• You've mastered nominative case (95% accuracy)
• Accusative prepositions need practice (62% accuracy)
• Builds on your existing knowledge
```

### Spaced Repetition Review

```
📋 Review Queue: 3 cards due

┌──────────────┬────────────────┬───────────────┐
│ Word         │ Last Review    │ Next Review   │
├──────────────┼────────────────┼───────────────┤
│ der Apfel    │ 2 days ago     │ NOW           │
│ sprechen     │ 5 days ago     │ NOW           │
│ das Haus     │ 1 day ago      │ Tomorrow      │
└──────────────┴────────────────┴───────────────┘
```

---

## ⚙️ GPU Setup (AMD RX 7800 XT / ROCm)

DeutschBuddy supports AMD GPUs via ROCm. To enable hardware acceleration:

<details>
<summary><b>📦 Step 1: Install ROCm</b> (click to expand)</summary>

```bash
# Ubuntu 22.04 / 24.04
sudo apt install rocm-hip-sdk
```

> 📖 Follow [AMD's ROCm install guide](https://rocm.docs.amd.com/en/latest/deploy/linux/index.html) for your distro.

</details>

<details>
<summary><b>✅ Step 2: Verify GPU</b> (click to expand)</summary>

```bash
rocm-smi
```

Expected output:
```
============================ ROCm System Management Interface ============================
========================================= Concise Info =========================================
Device  [Model : Revision]    Temp        Power     Partitions      SCLK    MCLK    Fans
                        Perf
          0   [0x7300 : x00]    45.0°C      N/A     N/A             2.0Ghz  2.0Ghz   N/A
          1   [0x7300 : x00]    47.0°C      N/A     N/A             2.0Ghz  2.0Ghz   N/A
===============================================================================================
```

</details>

<details>
<summary><b>🚀 Step 3: Run Ollama with ROCm</b> (click to expand)</summary>

```bash
# Override GPU architecture for RX 7800 XT (gfx1101 / RDNA3)
export HSA_OVERRIDE_GFX_VERSION=11.0.2

# Start Ollama server
ollama serve
```

</details>

### Environment Variables

| Variable | Purpose | Recommended Value |
|----------|---------|-------------------|
| `HSA_OVERRIDE_GFX_VERSION` | Override GPU architecture | `11.0.2` (RX 7800 XT) |
| `OLLAMA_GPU_OVERHEAD` | Reserved VRAM (bytes) | Tune if OOM |
| `OLLAMA_NUM_GPU` | GPU layers to offload | Auto-detected |

> 💡 **RX 7800 XT (16 GB VRAM)**: `llama3.1:8b` and `mistral:7b` will fully load on-device!

---

## 📊 CEFR Levels

DeutschBuddy follows the **Common European Framework of Reference for Languages**:

<div align="center">

| Level | Badge | Description | Lessons |
|-------|-------|-------------|---------|
| **A1** | 🟢 | Beginner — greetings, articles, present tense | 20 lessons |
| **A2** | 🟡 | Elementary — Perfekt, modals, cases | 15 lessons |
| **B1** | 🔵 | Intermediate — passive, Konjunktiv II, complex clauses | 10 lessons |

</div>

---

## ⌨️ Keyboard Shortcuts

### Global

| Key | Action |
|-----|--------|
| `q` | Quit |
| `h` | Home (dashboard) |
| `?` | Toggle help |
| `Ctrl+R` | Review queue |
| `Esc` | Back / Close |

### Home Dashboard

| Key | Action |
|-----|--------|
| `l` | Start lesson |
| `p` | View progress |
| `r` | Review vocabulary |
| `s` | Settings |

---

## 🔧 Settings

Press `s` from home or navigate to **Settings** in the sidebar.

| Setting | Description | Default |
|---------|-------------|---------|
| Curriculum model | AI for lesson recommendations | `llama3.1:8b-instruct` |
| Interaction model | AI for quizzes & tutoring | `mistral:7b-instruct` |
| Ollama host | Ollama instance URL | `http://localhost:11434` |

Settings are persisted to `config/settings.toml`.

---

## 🤝 Contributing

Contributions are welcome! 🎉

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/deutschbuddy.git
cd deutschbuddy

# Install in dev mode
uv sync --dev

# Run tests (if available)
uv run pytest
```

📖 See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📚 Additional Resources

- [CEFR Framework](https://www.coe.int/en/web/common-european-framework-reference-languages) - Official language proficiency levels
- [Ollama Documentation](https://ollama.ai/help) - Local AI model management
- [German Grammar Guide](https://www.germanwithlaura.com/) - supplementary learning

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for German learners everywhere**

[⬆️ Back to top](#-deutschbuddy)

</div>
