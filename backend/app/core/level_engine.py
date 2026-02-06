"""Level engine - handles level state transitions and pause/resume logic."""

import json

import redis.asyncio as aioredis

from app.config import settings


class LevelEngine:
    """Manages in-progress level state (pause/resume) via Redis."""

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    def _state_key(self, player_id: int) -> str:
        return f"level:state:{player_id}"

    async def save_state(self, player_id: int, level_id: str, node_id: str) -> None:
        """Save paused level state. Expires after TTL."""
        state = json.dumps({"level_id": level_id, "node_id": node_id})
        await self.redis.set(self._state_key(player_id), state, ex=settings.CHAT_CONTEXT_TTL)

    async def load_state(self, player_id: int) -> dict | None:
        """Load paused level state, or None if expired/doesn't exist."""
        raw = await self.redis.get(self._state_key(player_id))
        if raw:
            return json.loads(raw)
        return None

    async def clear_state(self, player_id: int) -> None:
        """Clear saved level state (player exited or completed level)."""
        await self.redis.delete(self._state_key(player_id))
