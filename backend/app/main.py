"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine, Base
from app.db.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables (dev only; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: close connections
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title="Yade Game API",
    description="Backend API for Yade - a mobile dialogue-based adventure game",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
# Import here (not at top level) so modules with heavy deps don't block startup
from app.api.routes import player, levels, chat, affinity  # noqa: E402
from app.api.websocket import chat_ws  # noqa: E402

app.include_router(player.router, prefix="/api/player", tags=["player"])
app.include_router(levels.router, prefix="/api/levels", tags=["levels"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(affinity.router, prefix="/api/affinity", tags=["affinity"])
app.include_router(chat_ws.router, tags=["websocket"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
