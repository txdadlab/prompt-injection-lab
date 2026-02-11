# Prompt Injection Lab

A local CTF-style web app for practicing prompt injection attacks against a local LLM. Each of 7 challenge levels has a hidden secret protected by progressively stronger (but intentionally bypassable) defenses.

Built as a portfolio piece demonstrating AI security skills.

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) (or any OpenAI-compatible API)

### Quick Start with Ollama

```bash
# Install Ollama, then pull a model (see Model Choice below)
ollama pull dolphin-mistral
```

## Setup

```bash
cd prompt-injection-lab
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Environment variables (all optional — defaults point to Ollama):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible API endpoint |
| `LLM_API_KEY` | `ollama` | API key |
| `LLM_MODEL` | `dolphin-mistral` | Model name |
| `LLM_TEMPERATURE` | `0.7` | Generation temperature |
| `LLM_MAX_TOKENS` | `512` | Max response tokens |
| `APP_HOST` | `127.0.0.1` | Server bind address |
| `APP_PORT` | `8080` | Server port |

## Model Choice

The model you choose significantly affects the experience. This lab's challenges are designed around bypassing the **lab's own defense layers** (input filters, output filters, sandwich defense, judge LLM) — not the model's built-in safety training.

**Recommended: Uncensored models** like `dolphin-mistral` or `dolphin-llama3`. These have their refusal training removed, so the model cooperates with its system prompt and the challenge is purely about beating the lab's defenses. This is the intended experience.

**Censored models** like `llama3.2`, `mistral`, or `gemma2` add an extra layer of difficulty — the model's own RLHF safety training will fight you on top of the lab's defenses. Some levels may become frustratingly difficult or unsolvable because the model refuses to engage regardless of your injection technique. Small models (3B) also tend to garble secrets due to limited context recall.

## Run

```bash
python run.py
```

Open http://127.0.0.1:8080 in your browser.

## Challenge Levels

| # | Name | Difficulty | Defenses |
|---|------|-----------|----------|
| 1 | Welcome to the Vault | Easy | None |
| 2 | Sworn to Secrecy | Easy | Instruction only |
| 3 | The Keyword Gauntlet | Medium | Input filter |
| 4 | The Censored Response | Medium | Output filter |
| 5 | The Sandwich Trap | Hard | Sandwich defense |
| 6 | Trained Resistance | Hard | Few-shot examples |
| 7 | Fort Knox | Expert | All defenses + Judge LLM |

## Defense Pipeline

```
User Input → Input Filter → Build Prompt → LLM Call → Output Filter → Judge LLM → Response
```

Each defense is intentionally bypassable — that's the point of the lab.

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **LLM**: Ollama (or any OpenAI-compatible API)
- **Frontend**: Static HTML + Tailwind CSS (CDN) + vanilla JS
- **Storage**: JSON file (single-user local app)

## Project Structure

```
├── config.py              # App settings (env-overridable)
├── run.py                 # Entry point
├── levels/definitions.py  # All 7 level configs
├── defenses/              # Input filter, output filter, sandwich, judge
├── server/                # FastAPI app, LLM client, progress persistence
├── static/                # Single-page frontend (HTML + CSS + JS)
└── data/                  # Runtime progress storage
```
