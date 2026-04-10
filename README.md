# podclean

A podcast management platform that automatically transcribes episodes, detects advertisements using AI, and produces ad-free audio files.

## Features

- RSS feed polling and episode discovery
- Audio transcription via [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) (CPU and GPU)
- Ad segment detection using the [Claude API](https://www.anthropic.com) (or local Ollama LLMs)
- Automated ad removal from audio files
- Optional human review gate before audio is modified
- Ad-free RSS feed generation with original episode metadata
- Dashboard with processing history, time-savings stats, and GPU status
- Backup and restore support

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic, Celery |
| Frontend | React 18, React Router, Vite |
| Message broker | Redis |
| AI / transcription | Claude API (Anthropic), Faster-Whisper, Ollama |
| Infrastructure | Docker (CPU + GPU worker variants) |

## Getting Started

### Prerequisites

- Docker and Docker Compose
- An [Anthropic API key](https://console.anthropic.com/) (or a running Ollama instance)

### Run

```bash
docker compose up
```

The dashboard is available at `http://localhost:3000` by default.

### GPU acceleration

A GPU-enabled worker service is included in the Compose file. Ensure your host has NVIDIA drivers and the NVIDIA Container Toolkit installed, then use the `gpu` profile:

```bash
docker compose --profile gpu up
```

## Architecture

```
Frontend (React) ──► Backend API (FastAPI) ──► Redis ──► Celery Workers
                                                              │
                                              ┌───────────────┴──────────────┐
                                         CPU Worker                    GPU Worker
                                              │
                                    Faster-Whisper / Claude API / Ollama
```

Workers run a multi-stage pipeline: **download → transcribe → classify ads → remove ad segments → generate feed**.
