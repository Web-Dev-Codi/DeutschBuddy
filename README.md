<div align="center">

![deutschbuddy Logo](https://img.shields.io/badge/🇩🇪-deutschbuddy-FFD700?style=for-the-badge&logo=german&logoColor=black)

# 🎓 DeutschBuddy

**AI-Powered German Language Learning for English Speakers**

*Achieve conversational fluency with personalized, AI-driven lessons that adapt to your learning pace*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](https://opensource.org/licenses/MIT) [![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.ai) [![CEFR A1→B1](https://img.shields.io/badge/CEFR-A1%E2%86%92B1-32A852?style=for-the-badge)](#cefr-levels)

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

## ⚠️ Disclaimer

> **This project is highly experimental.** deutschbuddy is a work in progress and is being actively developed. You may encounter:
>
> - 🐛 Bugs and unexpected behavior
> - 🔧 Incomplete features or changing functionality
> - 📝 Evolving curriculum content
> - 🔄 Frequent updates that may break existing workflows
>
> **Use at your own risk.** This app is intended for learning purposes and should not be considered a complete replacement for formal German language education or professional language tutoring.
>
> If you encounter issues or have suggestions, please [open an issue](https://github.com/Web-Dev-Codi/deutschbuddy/issues)!

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
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              AI Curriculum Agent                        │    │
│  │  • Analyzes performance  • Identifies knowledge gaps    │    │
│  │  • Recommends next lesson • Adjusts difficulty          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           YAML Content Library                          │    │
│  │  • A1/ • A2/ • B1/ lesson files                         │    │
│  │  • Grammar • Vocabulary • Exercises                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              ↓                                  │    
│                    Learner studies → Repeat                     │
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

## ⚙️ GPU Setup on Linux (NVIDIA / AMD / Intel)

DeutschBuddy uses Ollama for local model inference, so Linux GPU
acceleration depends on the backend Ollama supports for your hardware:

- **NVIDIA**: CUDA backend, Compute Capability **5.0+**, driver **531+**
- **AMD**: ROCm backend for supported Radeon / Radeon Pro / Instinct GPUs
- **Intel**: Vulkan backend on Linux, currently **experimental** in Ollama
- **Fallback**: CPU mode if no supported GPU backend is available

### Linux Distro Coverage

The app is not limited to Ubuntu or Arch. It can run with GPU
acceleration on the major Linux distro families as long as the correct
vendor drivers and runtime libraries are installed:

- **Ubuntu / Debian**: Ubuntu 22.04+, Debian 12+, with Ollama plus
  vendor CUDA / ROCm / Vulkan packages
- **Fedora / RHEL**: Fedora, RHEL, Rocky, AlmaLinux, with Ollama plus
  vendor driver repositories or distro packages
- **Arch-based**: Arch, Manjaro, EndeavourOS, with current GPU drivers
  and Vulkan utilities
- **openSUSE**: Tumbleweed and Leap, with Ollama plus vendor drivers
  and Vulkan utilities
- **Other Linux distros**: any modern systemd-based distro with the
  matching kernel driver, userspace runtime, and `ollama serve`

<details>
<summary><b>📦 Step 1: Install Ollama on Linux</b> (click to expand)</summary>

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama -v
```

</details>

<details>
<summary><b>🟩 NVIDIA GPUs (CUDA)</b> (click to expand)</summary>

Install the current NVIDIA driver / CUDA stack for your distro, then
verify detection:

```bash
nvidia-smi
ollama serve
```

- Ollama supports NVIDIA GPUs with **Compute Capability 5.0+**
- Recommended if you have GeForce RTX, RTX A-series, Quadro RTX,
  Tesla, or newer supported cards
- If you have multiple NVIDIA GPUs, you can limit visibility with
  `CUDA_VISIBLE_DEVICES`

> 📖 NVIDIA CUDA downloads: [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)

</details>

<details>
<summary><b>🟥 AMD GPUs (ROCm)</b> (click to expand)</summary>

Install ROCm for your distro, then verify detection:

```bash
rocm-smi
ollama serve
```

- Best path for supported AMD Radeon RX, Radeon Pro, and Instinct GPUs
  on Linux
- If your GPU is close to a supported ROCm target but not recognized,
  you can try an override

Example for an RX 7800 XT:

```bash
export HSA_OVERRIDE_GFX_VERSION=11.0.2
ollama serve
```

> 📖 AMD ROCm Linux install guide: [rocm.docs.amd.com](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/tutorial/quick-start.html)

</details>

<details>
<summary><b>🟦 Intel GPUs and additional Vulkan-capable GPUs</b> (click to expand)</summary>

On Linux, Ollama also has **experimental Vulkan support**, which is
the most relevant path for Intel GPUs and some additional AMD setups.

Install your distro's Vulkan driver stack and verification tools, then
run:

```bash
export OLLAMA_VULKAN=1
vulkaninfo --summary
ollama serve
```

- Best fit for Intel Arc and other Linux systems where Vulkan is the
  available acceleration path
- Vulkan support in Ollama is still experimental, so stability may
  vary more than CUDA or ROCm
- If you need to restrict Vulkan devices, use
  `GGML_VK_VISIBLE_DEVICES`

> 📖 Intel Linux GPU docs: [dgpu-docs.intel.com](https://dgpu-docs.intel.com/driver/client/overview.html)

</details>

<details>
<summary><b>✅ Step 2: Verify your backend</b> (click to expand)</summary>

Use the command that matches your GPU vendor:

```bash
# NVIDIA
nvidia-smi

# AMD
rocm-smi

# Intel / Vulkan
vulkaninfo --summary
```

</details>

### Environment Variables

- **`CUDA_VISIBLE_DEVICES`**: limit NVIDIA GPUs visible to Ollama
- **`ROCR_VISIBLE_DEVICES`**: limit AMD GPUs visible to Ollama
- **`HSA_OVERRIDE_GFX_VERSION`**: override AMD GFX target for
  unsupported-but-similar AMD GPUs
- **`OLLAMA_VULKAN`**: enable Vulkan backend
- **`GGML_VK_VISIBLE_DEVICES`**: limit Vulkan-visible GPUs
- **`OLLAMA_GPU_OVERHEAD`**: reserve VRAM headroom if you hit OOM
- **`OLLAMA_NUM_GPU`**: control GPU offload, though auto-detection is
  usually fine

### Linux Notes

- **NVIDIA**: if GPU detection breaks after suspend/resume, reloading
  `nvidia_uvm` may help
- **AMD**: on some distros, the `ollama` user may need access to the
  `render` group
- **Intel / Vulkan**: install both Vulkan drivers and `vulkaninfo`
  tooling for your distro
- **All vendors**: if GPU setup is incomplete, Ollama will still run on
  CPU

> 💡 **16 GB VRAM class GPUs** such as the RX 7800 XT or RTX 4070
> Ti-class cards are usually a strong fit for `llama3.1:8b` and
> `mistral:7b` locally.

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
