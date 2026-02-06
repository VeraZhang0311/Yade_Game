# Yade Game - AI Assistant Guide

## Project Overview

**Yade Game** is a mobile dialogue-based adventure game (手机端对话类闯关游戏). The player interacts with a character called **亚德 (Yade)** through two modes:

1. **Fixed Levels (关卡)** - Story chapters with branching dialogue trees. Players pick from fixed options to advance the plot. Each option can affect affinity score (好感度).
2. **Free Chat (闲聊)** - Between levels, players can voice-chat freely with Yade. Yade's responses come from an LLM (通义千问max via DashScope). Chat quality also affects affinity.

**MVP scope**: Single player, one character (Yade), linear level unlock (complete one to unlock the next), backend only.

## Tech Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Framework       | **FastAPI** (Python 3.11+)          |
| ORM             | **SQLAlchemy 2.0** (async)          |
| Migrations      | **Alembic**                         |
| Database        | **PostgreSQL 16** (via Docker)      |
| Cache/Sessions  | **Redis 7** (via Docker)            |
| LLM             | **DashScope SDK** (通义千问max)      |
| WebSocket       | FastAPI native WebSocket            |
| Testing         | **pytest** + pytest-asyncio         |
| Linting         | **ruff**                            |
| Type checking   | **mypy**                            |

## Repository Structure

```
Yade_Game/
├── CLAUDE.md                          # This file
├── README.md
├── docker/
│   └── docker-compose.yml             # PostgreSQL + Redis containers
├── backend/
│   ├── pyproject.toml                 # Project metadata, dependencies, tool config
│   ├── requirements.txt               # Pip-installable dependencies
│   ├── .env.example                   # Environment variable template
│   ├── .gitignore
│   ├── alembic.ini                    # Alembic migration config
│   ├── alembic/
│   │   ├── env.py                     # Async Alembic environment
│   │   └── versions/                  # Migration scripts
│   ├── app/
│   │   ├── main.py                    # FastAPI app entrypoint, lifespan, middleware
│   │   ├── config.py                  # Pydantic Settings (env-driven config)
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── player.py          # Player CRUD endpoints
│   │   │   │   ├── levels.py          # Level listing, data, choice submission
│   │   │   │   ├── chat.py            # Chat history REST endpoints
│   │   │   │   └── affinity.py        # Affinity status query
│   │   │   └── websocket/
│   │   │       └── chat_ws.py         # WebSocket streaming free-chat
│   │   ├── core/
│   │   │   └── level_engine.py        # Level pause/resume state (Redis)
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── player.py              # Player state, progress, memory
│   │   │   ├── level.py               # Level metadata + player choices
│   │   │   ├── chat_history.py        # Persisted chat messages
│   │   │   └── affinity.py            # Affinity change event log
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   │   ├── player.py
│   │   │   ├── level.py               # DialogueNode, DialogueOption, LevelData
│   │   │   ├── chat.py
│   │   │   └── affinity.py
│   │   ├── services/                  # Business logic layer
│   │   │   ├── llm_service.py         # DashScope/Qwen integration, streaming
│   │   │   ├── level_service.py       # YAML level loader + progression
│   │   │   ├── chat_service.py        # Redis context + LLM orchestration
│   │   │   ├── affinity_service.py    # Affinity tiers + score updates
│   │   │   └── memory_service.py      # Long-term memory extraction (LLM)
│   │   ├── db/
│   │   │   ├── database.py            # Async SQLAlchemy engine + session
│   │   │   └── redis.py               # Async Redis client
│   │   └── data/                      # Static game content (YAML)
│   │       ├── characters/
│   │       │   └── yade.yaml          # Yade's personality + system prompt
│   │       └── levels/
│   │           └── chapter_01.yaml    # Level dialogue tree definitions
│   └── tests/
│       ├── conftest.py                # Shared fixtures (async test client)
│       ├── test_level_service.py
│       └── test_affinity_service.py
├── frontend/                          # Frontend code (separate team)
└── shared/                            # Shared resources between frontend/backend
```

## Architecture Concepts

### Layer Separation

The backend follows a **3-layer architecture**:

1. **API layer** (`app/api/`) - HTTP routes and WebSocket handlers. Thin controllers that validate input and delegate to services.
2. **Service layer** (`app/services/`) - Business logic. Services are stateless singletons (instantiated at module level). They orchestrate between models, Redis, and external APIs.
3. **Data layer** (`app/models/` + `app/db/`) - SQLAlchemy models and database/Redis connections.

### Key Data Flows

**Level Playthrough:**
```
Client → POST /api/levels/choice → levels.py route → level_service (loads YAML)
    → affinity_service (updates score) → DB commit → response with next node
```

**Free Chat (WebSocket):**
```
Client → WS /ws/chat/{player_id} → chat_ws.py
    → chat_service (manages Redis context)
    → llm_service (streams from DashScope)
    → chunks sent back via WebSocket
    → on disconnect: evaluate affinity + extract memory
```

### Game Data Format

Levels are defined in YAML files under `app/data/levels/`. Each level is a dialogue tree:
- **Nodes** are individual dialogue screens (speaker + text)
- **Options** are player choices with `affinity_delta` and `next_node`
- Nodes with `is_ending: true` trigger level completion and unlock the next level

Character definitions live in `app/data/characters/` with system prompts for the LLM.

### Affinity System (好感度)

Two sources of affinity change:
1. **Level choices** - Hard-coded `affinity_delta` per option in YAML
2. **Chat quality** - LLM evaluates chat session on disconnect (depth, emotion, engagement)

Tiers: 陌生人(0) → 认识(20) → 朋友(40) → 好友(60) → 挚友(80) → 羁绊(100)

Affinity affects Yade's personality in chat (warmer at higher levels, more guarded at lower).

### Memory System

- **Short-term**: Redis-cached chat context (last N turns, TTL-based)
- **Long-term**: LLM extracts key facts from chat → stored in `Player.memory_facts` (JSON column)
- Memory facts are injected into Yade's system prompt during chat

## Development Workflow

### Prerequisites

- Python 3.11+
- Docker & Docker Compose

### Setup

```bash
# Start databases
cd docker && docker compose up -d

# Set up Python environment
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy and fill in env vars
cp .env.example .env
# Edit .env with your DASHSCOPE_API_KEY

# Run migrations (after first setup)
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Common Commands

```bash
# Run tests (from backend/)
pytest

# Run tests with coverage
pytest --cov=app

# Lint
ruff check app/ tests/

# Format
ruff format app/ tests/

# Type check
mypy app/

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Start/stop Docker services
cd docker && docker compose up -d
cd docker && docker compose down
```

### Adding a New Level

1. Create `backend/app/data/levels/chapter_XX.yaml` following the existing format
2. Define `id`, `title`, `order`, `start_node`, and all `nodes`
3. Each node needs: `speaker`, `text`, and either `options` (for choices) or `next_node` (for auto-advance)
4. Mark the final node with `is_ending: true`
5. Set `affinity_delta` on options that should affect affinity

### Adding a New API Endpoint

1. Add Pydantic schemas in `app/schemas/`
2. Add business logic in `app/services/`
3. Add route in `app/api/routes/` and register in `app/main.py`
4. Add tests in `tests/`

## Conventions & Rules

### Code Style
- **Python 3.11+** features (type unions `X | None`, etc.)
- **Async everywhere** - all DB operations, Redis, HTTP, WebSocket are async
- **Pydantic v2** for all schemas (`model_config = {"from_attributes": True}`)
- **SQLAlchemy 2.0** mapped_column style (not legacy Column)
- **ruff** for linting and formatting (line length 100)

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- API routes: RESTful (`/api/{resource}`)
- WebSocket: `/ws/{purpose}/{id}`
- Redis keys: `namespace:sub:id` (e.g., `chat:context:1`)
- Level IDs: `chapter_XX` format
- YAML data files: match the level/character ID

### Architecture Rules
- **Routes should be thin** - validation + delegation only, no business logic
- **Services are singletons** - instantiated at module level, imported directly
- **Models map 1:1 to database tables** - no inheritance hierarchies
- **Schemas separate from models** - never return ORM models directly from routes
- **Game content in YAML** - dialogue trees and character prompts are data, not code
- **Redis for ephemeral state** - chat context, paused level state (TTL-based)
- **PostgreSQL for persistent state** - player progress, chat history, affinity records

### Environment & Secrets
- **Never commit `.env`** - use `.env.example` as template
- All config flows through `app/config.py` (`Settings` class)
- `DASHSCOPE_API_KEY` is required for chat functionality

### Testing
- Use `pytest-asyncio` for async tests
- Test services directly (unit tests) before testing through routes (integration)
- Level YAML parsing tests don't need a database
- Chat/LLM tests should mock the DashScope API

### WebSocket Protocol
Client sends JSON: `{"type": "message", "content": "user text"}`
Server responds with streaming chunks: `{"type": "chunk", "content": "partial text"}`
Server signals end: `{"type": "end"}`
Server signals error: `{"type": "error", "content": "error description"}`

## Future Considerations (Post-MVP)

- Multiple characters (new YAML in `data/characters/`, extend models)
- Branching level unlock conditions (extend `level_service`)
- Voice input/output integration
- Image generation
- Multi-user support (add auth layer)
- Per-level character personality variations
