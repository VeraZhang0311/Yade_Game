"""Chat service - orchestrates free-chat sessions with Redis context management."""

import json
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.config import settings
from app.services.llm_service import llm_service


class ChatService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    def _context_key(self, player_id: int) -> str:
        return f"chat:context:{player_id}"

    async def get_context(self, player_id: int) -> list[dict]:
        """Get short-term chat context from Redis."""
        raw = await self.redis.get(self._context_key(player_id))
        if raw:
            return json.loads(raw)
        return []

    async def save_context(self, player_id: int, messages: list[dict]) -> None:
        """Save short-term chat context to Redis with TTL."""
        # Keep only the last N turns
        trimmed = messages[-(settings.MAX_CHAT_CONTEXT_TURNS * 2):]
        await self.redis.set(
            self._context_key(player_id),
            json.dumps(trimmed, ensure_ascii=False),
            ex=settings.CHAT_CONTEXT_TTL,
        )

    async def clear_context(self, player_id: int) -> None:
        """Clear chat context (e.g. when entering a new level)."""
        await self.redis.delete(self._context_key(player_id))

    async def stream_reply(
        self,
        player_id: int,
        user_message: str,
        character_prompt: str,
        affinity_score: int = 0,
        memory_facts: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Send a message and stream back the LLM response, managing context."""
        # Load existing context
        context = await self.get_context(player_id)
        context.append({"role": "user", "content": user_message})

        # Stream response
        full_response = ""
        async for chunk in llm_service.chat_stream(
            messages=context,
            character_prompt=character_prompt,
            affinity_score=affinity_score,
            memory_facts=memory_facts,
        ):
            full_response += chunk
            yield chunk

        # Save updated context
        context.append({"role": "assistant", "content": full_response})
        await self.save_context(player_id, context)
