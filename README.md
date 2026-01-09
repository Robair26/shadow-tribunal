# Shadow Tribunal

A local-first, privacy-friendly LLM app that generates a multi-voice psychological analysis (“Analyst”, “Critic”, “Protector”) from user input, running on **Ollama** and presented via a **Streamlit** UI.

## What it does
- Runs **entirely locally** (Ollama on your machine)
- Produces structured output:
  - Psychological profile (archetype, traits, motivations, blind spots)
  - “The Tribunal Speaks” (multi-perspective synthesis)
- Designed for fast iteration on prompts + logic with a clean UI

## Tech stack
- Python
- Streamlit
- Ollama (local inference)
- httpx (HTTP client)

## Quick start (local)

### 1) Install Ollama + pull a model
Install Ollama and pull a model you want to use (examples):
- `llama3`
- `mistral`
- `qwen2.5`

Example:
```bash
ollama pull llama3
```

Start Ollama (if not already running):
```bash
ollama serve
```

### 2) Install Python deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Run the Streamlit app
From the repo root:
```bash
streamlit run streamlit_app/app.py
```

## Configuration
This app expects an Ollama generate endpoint. Defaults to:
- `http://127.0.0.1:11434/api/generate`

You can override via environment variables:

1) Copy:
```bash
cp .env.example .env
```

2) Edit `.env` if needed.

## Repo layout
- `streamlit_app/` — Streamlit UI
- `core/` — prompts + logic + LLM client
- `run_local.sh` — convenience script

## Notes for deployment
This repo is meant to be run locally. If you deploy, keep `.env` out of git and use environment variables.

## License
MIT (or your preferred license).
