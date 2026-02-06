"""Memory service - manages Yade's long-term memory of the player."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.services.llm_service import llm_service


class MemoryService:
    @staticmethod
    async def get_facts(db: AsyncSession, player_id: int) -> dict:
        """Get all stored memory facts for a player."""
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one()
        return player.memory_facts or {}

    @staticmethod
    async def update_facts(db: AsyncSession, player_id: int, new_facts: dict) -> dict:
        """Merge new facts into the player's memory."""
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one()
        current = player.memory_facts or {}
        current.update(new_facts)
        player.memory_facts = current
        await db.flush()
        return current

    @staticmethod
    async def extract_and_save(
        db: AsyncSession, player_id: int, messages: list[dict]
    ) -> dict:
        """Extract memory facts from a chat session and persist them."""
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one()
        existing = player.memory_facts or {}

        new_facts = await llm_service.extract_memory_facts(messages, existing)
        if new_facts:
            existing.update(new_facts)
            player.memory_facts = existing
            await db.flush()

        return existing


memory_service = MemoryService()
