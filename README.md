# LangChain DeepAgent

> A production-ready FastAPI service that powers a **LangChain DeepAgent** backed by **Ollama llama3.2:3b**, featuring four specialised skills, SSE streaming, Redis rate limiting, and multi-turn session memory.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Tech Stack](#tech-stack)
5. [Quickstart](#quickstart)
   - [Docker (recommended)](#docker-recommended)
   - [Local Development](#local-development)
6. [API Reference](#api-reference)
7. [Skills Reference](#skills-reference)
8. [Configuration](#configuration)
9. [Project Structure](#project-structure)
10. [Development Guide](#development-guide)

---

## Overview

**LangChain DeepAgent** is a self-hosted AI agent API that accepts natural language queries and responds by autonomously using a set of specialised skills:

- **Think** — structured chain-of-thought reasoning
- **Plan** — multi-step task decomposition
- **Web Search** — real-time DuckDuckGo search
- **Write Report** — professional markdown report generation

The agent is built on the official [`deepagents`](https://github.com/langchain-ai/deepagents) package from LangChain, which provides the agent harness, skill discovery via `SKILL.md` files, and a built-in planning tool. The underlying LLM is **llama3.2:3b** served locally via [Ollama](https://ollama.ai), keeping all inference private and cost-free.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client                                  │
│  POST /api/v1/agent/run       GET /api/v1/agent/stream (SSE)    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────────────┐
│                       FastAPI App                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Middleware stack                                        │    │
│  │  CORSMiddleware → LoggingMiddleware → RateLimiter(Redis) │    │
│  └─────────────────────────────────────────────────────────┘    │
│                       │                                          │
│  ┌────────────────────▼────────────────────────────────────┐    │
│  │           async_create_deep_agent()                     │    │
│  │           (deepagents package — LangGraph graph)        │    │
│  └────────────────────┬────────────────────────────────────┘    │
│                       │                                          │
│  ┌────────────────────▼────────────────────────────────────┐    │
│  │           ChatOllama (llama3.2:3b)                      │    │
│  └────────────────────┬────────────────────────────────────┘    │
│                       │ tool calls                               │
│  ┌────────────────────▼────────────────────────────────────┐    │
│  │  Skills (Python tools + SKILL.md instruction files)     │    │
│  │  ┌──────────┐ ┌──────┐ ┌────────────┐ ┌─────────────┐  │    │
│  │  │  think   │ │ plan │ │ web_search │ │write_report │  │    │
│  │  └──────────┘ └──────┘ └────────────┘ └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

Infrastructure:
  Redis 7     ← rate limit counters (10 req/60s per IP by default)
  Ollama      ← llama3.2:3b weights (~2 GB, pulled automatically)
```

---

## Features

| Feature | Details |
|---|---|
| **DeepAgent skills** | Four skills via `SKILL.md` discovery + Python tool implementations |
| **Streaming** | SSE stream of tokens, tool_start, tool_end, done events |
| **Rate limiting** | Redis-backed, per-IP, fully configurable via env vars |
| **Session memory** | LangGraph MemorySaver — pass `session_id` to continue threads |
| **Structured logging** | `structlog` with JSON (production) / colored console (debug) |
| **Health probes** | Liveness `/health` and readiness `/health/ready` (Ollama + Redis) |
| **Docker** | Multi-stage Dockerfile + full `docker-compose.yml` (3 services) |
| **Config** | Pydantic Settings — all values overridable via environment variables |
| **Type safety** | Full type annotations, Pydantic v2 request/response models |
| **Async** | Fully async FastAPI + async LangGraph + async Redis |

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | [FastAPI](https://fastapi.tiangolo.com/) 0.115+ |
| Agent harness | [deepagents](https://github.com/langchain-ai/deepagents) 0.4+ |
| Agent graph | [LangGraph](https://langchain-ai.github.io/langgraph/) 0.2+ |
| LLM framework | [LangChain](https://python.langchain.com/) 0.3+ |
| LLM | [Ollama](https://ollama.ai/) + llama3.2:3b |
| Ollama client | [langchain-ollama](https://pypi.org/project/langchain-ollama/) |
| Web search | [duckduckgo-search](https://pypi.org/project/duckduckgo-search/) (DDGS) |
| Rate limiting | [fastapi-limiter](https://github.com/long2ice/fastapi-limiter) + Redis |
| Cache / state | [Redis 7](https://redis.io/) |
| SSE streaming | [sse-starlette](https://github.com/sysid/sse-starlette) |
| Logging | [structlog](https://www.structlog.org/) |
| Validation | [Pydantic](https://docs.pydantic.dev/) v2 + pydantic-settings |
| Server | [Uvicorn](https://www.uvicorn.org/) |
| Containers | Docker + Docker Compose |

---

## Quickstart

### Docker (recommended)

This is the fastest way to run the full stack (app + Ollama + Redis).

```bash
# 1. Clone the repo
git clone https://github.com/aiwithvd/langchain_deepagent.git
cd langchain_deepagent

# 2. Copy env template (edit values as needed)
cp .env.example .env

# 3. Start all services
#    First run pulls llama3.2:3b (~2 GB) — this may take several minutes
docker compose up --build

# 4. Check health
curl http://localhost:8000/health/ready
# {"status":"ok","version":"1.0.0","ollama_reachable":true,"redis_reachable":true}

# 5. Run the agent
curl -X POST http://localhost:8000/api/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"query": "Research the latest trends in AI agents and write a report"}'
```

> **GPU support**: add `deploy.resources.reservations.devices` to the `ollama` service in `docker-compose.yml` for NVIDIA GPU passthrough.

---

### Local Development

**Prerequisites**: Python 3.11+, Redis, Ollama with `llama3.2:3b` pulled.

```bash
# 1. Clone and enter repo
git clone https://github.com/aiwithvd/langchain_deepagent.git
cd langchain_deepagent

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies (runtime + dev)
pip install -e ".[dev]"

# 4. Set up env
cp .env.example .env
# Edit .env to point OLLAMA_BASE_URL and REDIS_URL to your local services

# 5. Start Ollama (separate terminal)
ollama serve
ollama pull llama3.2:3b

# 6. Start Redis (separate terminal, or use Docker)
docker run -p 6379:6379 redis:7-alpine

# 7. Run the API
uvicorn app.main:app --reload --port 8000

# 8. Open Swagger UI
open http://localhost:8000/docs
```

---

## API Reference

### `POST /api/v1/agent/run`

Invoke the agent and wait for the complete response.

**Rate limit**: 10 requests / 60 seconds per IP (configurable).

**Request body**:
```json
{
  "query": "Research quantum computing and write a report",
  "session_id": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | `string` | Yes | The question or task (1–4096 chars) |
| `session_id` | `string \| null` | No | Session ID to continue a thread |

**Response `200 OK`**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "Research quantum computing and write a report",
  "answer": "# Quantum Computing Report\n...",
  "tool_calls": [
    { "tool": "plan",        "input": "{\"goal\": \"...\"}", "output": "## Plan: ..." },
    { "tool": "web_search",  "input": "{\"query\": \"quantum computing 2025\"}", "output": "1. **Title** ..." },
    { "tool": "think",       "input": "{\"thought\": \"...\"}", "output": "[Reasoning] ..." },
    { "tool": "write_report","input": "{\"title\": \"...\"}", "output": "# Quantum Computing Report\n..." }
  ],
  "iterations": 5,
  "elapsed_seconds": 12.34
}
```

**Error responses**:

| Code | Meaning |
|---|---|
| `422` | Validation error (query too long, etc.) |
| `429` | Rate limit exceeded |
| `500` | Agent execution failed |

---

### `GET /api/v1/agent/stream`

Invoke the agent and stream events via Server-Sent Events (SSE).

**Rate limit**: same as `/run`.

**Query parameters**:

| Param | Type | Required | Description |
|---|---|---|---|
| `query` | `string` | Yes | The question or task |
| `session_id` | `string` | No | Session ID to continue a thread |

**Example**:
```bash
curl -N "http://localhost:8000/api/v1/agent/stream?query=What+is+LangGraph"
```

**SSE event stream**:
```
event: token
data: LangGraph

event: token
data:  is a library...

event: tool_start
data: web_search

event: tool_end
data: 1. **LangGraph Docs** ...

event: done
data: {"session_id": "550e8400-..."}
```

**Event types**:

| Event | Data |
|---|---|
| `token` | A single streamed LLM token |
| `tool_start` | Name of the skill being invoked |
| `tool_end` | Truncated output from the skill (max 500 chars) |
| `done` | JSON with `session_id` — stream is complete |
| `error` | Error message string |

---

### `GET /health`

Liveness probe. Always returns `200` if the process is running.

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

### `GET /health/ready`

Readiness probe. Checks Ollama and Redis connectivity.

```bash
curl http://localhost:8000/health/ready
# {"status":"ok","version":"1.0.0","ollama_reachable":true,"redis_reachable":true}
```

Returns `status: "degraded"` (but still HTTP `200`) if either dependency is unreachable.

---

### Multi-turn sessions

Pass the `session_id` from one response into the next request to continue a conversation:

```bash
# Turn 1
SESSION=$(curl -s -X POST http://localhost:8000/api/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"query": "Research AI agent frameworks"}' | jq -r '.session_id')

# Turn 2 — agent remembers the previous research
curl -X POST http://localhost:8000/api/v1/agent/run \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Now write a report based on what you found\", \"session_id\": \"$SESSION\"}"
```

---

## Skills Reference

Each skill exists as both a **Python `@tool`** and a **`SKILL.md`** instruction file the agent discovers at runtime.

### `think`
**Files**: `deepagents_skills/think/SKILL.md` · `app/agent/tools/think.py`

Structured chain-of-thought reasoning. Used before complex decisions, trade-off analysis, or when multiple approaches are possible.

- **Input**: `thought: str`
- **Output**: `[Question]` → `[Reasoning steps]` → `[Conclusion]`

### `plan`
**Files**: `deepagents_skills/plan/SKILL.md` · `app/agent/tools/plan.py`

Decomposes a high-level goal into ordered, atomic sub-tasks with assigned tools and success criteria.

- **Input**: `goal: str`, `context: str` (optional)
- **Output**: Numbered markdown plan with tool assignments

### `web_search`
**Files**: `deepagents_skills/web_search/SKILL.md` · `app/agent/tools/web_search.py`

Real-time DuckDuckGo search (no API key). Runs in a background thread to avoid blocking the async event loop.

- **Input**: `query: str`, `max_results: int` (default 5, max 10)
- **Output**: Formatted results with title, URL, snippet

### `write_report`
**Files**: `deepagents_skills/write_report/SKILL.md` · `app/agent/tools/write_report.py`

Pure formatting skill — wraps research findings in a professional markdown template with timestamp.

- **Input**: `title`, `executive_summary`, `key_findings`, `analysis`, `conclusion`
- **Output**: Complete markdown report

---

## Configuration

All settings are read from environment variables (or `.env`). Copy `.env.example` to `.env` and edit.

| Variable | Default | Description |
|---|---|---|
| `DEBUG` | `false` | Debug mode — colored logs, verbose output |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model name |
| `OLLAMA_TEMPERATURE` | `0.0` | LLM sampling temperature |
| `AGENT_RECURSION_LIMIT` | `25` | Max LangGraph iterations per request |
| `SKILLS_DIR` | `deepagents_skills` | Path to skills directory |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `RATE_LIMIT_REQUESTS` | `10` | Max requests per window per IP |
| `RATE_LIMIT_SECONDS` | `60` | Rate limit window in seconds |
| `CORS_ORIGINS` | `["*"]` | JSON list of allowed CORS origins |

---

## Project Structure

```
langchain_deepagent/
├── deepagents_skills/
│   ├── think/SKILL.md             # Chain-of-thought instructions
│   ├── plan/SKILL.md              # Planning instructions
│   ├── web_search/SKILL.md        # Web search usage guide
│   └── write_report/SKILL.md      # Report format spec
│
├── app/
│   ├── main.py                    # FastAPI app factory + lifespan
│   ├── api/routes/
│   │   ├── agent.py               # /run and /stream endpoints
│   │   └── health.py              # /health and /health/ready
│   ├── agent/
│   │   ├── factory.py             # DeepAgent singleton (thread-safe)
│   │   └── tools/
│   │       ├── think.py           # Chain-of-thought reasoning skill
│   │       ├── plan.py            # Goal decomposition skill
│   │       ├── web_search.py      # DuckDuckGo search skill
│   │       └── write_report.py    # Markdown report skill
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (env-driven)
│   │   ├── logging.py             # structlog + LoggingMiddleware
│   │   └── rate_limit.py          # Redis init + RateLimiter helpers
│   └── models/
│       └── schemas.py             # Pydantic v2 request/response models
│
├── Dockerfile                     # Multi-stage production image
├── docker-compose.yml             # app + ollama + redis services
├── pyproject.toml                 # Project metadata + dependencies
├── .env.example                   # Environment variable template
└── README.md                      # This file
```

---

## Development Guide

### Code Quality

```bash
# Lint and auto-fix
ruff check . --fix

# Type checking
mypy app/

# Format
ruff format .
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing
```

### Adding a New Skill

1. Create `deepagents_skills/<name>/SKILL.md` with YAML frontmatter + instructions
2. Create `app/agent/tools/<name>.py` with a `@tool` async function
3. Add the tool to `ALL_TOOLS` in `app/agent/tools/__init__.py`
4. Restart the app — the agent discovers the new `SKILL.md` automatically

### Changing the LLM

Set `OLLAMA_MODEL` in `.env` to any Ollama model that supports tool calling:

```bash
ollama pull llama3.1:8b    # more capable, higher VRAM
ollama pull qwen2.5:7b     # strong reasoning
ollama pull mistral:7b     # fast and capable
```

---

## Sources

- [LangChain DeepAgents Skills Docs](https://docs.langchain.com/oss/python/deepagents/skills)
- [GitHub — langchain-ai/deepagents](https://github.com/langchain-ai/deepagents)
- [LangChain Blog: Using Skills with Deep Agents](https://blog.langchain.com/using-skills-with-deep-agents/)
- [PyPI — deepagents](https://pypi.org/project/deepagents/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
