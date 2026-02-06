"""Affinity service - manages the affinity/好感度 system."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affinity import AffinityRecord
from app.models.player import Player


# Affinity tiers for display
AFFINITY_TIERS = [
    (0, "陌生人"),
    (20, "认识"),
    (40, "朋友"),
    (60, "好友"),
    (80, "挚友"),
    (100, "羁绊"),
]


class AffinityService:
    @staticmethod
    def get_tier(score: int) -> str:
        """Get the descriptive tier for an affinity score."""
        tier_name = AFFINITY_TIERS[0][1]
        for threshold, name in AFFINITY_TIERS:
            if score >= threshold:
                tier_name = name
        return tier_name

    @staticmethod
    async def add_affinity(
        db: AsyncSession,
        player_id: int,
        delta: int,
        source: str,
        reason: str | None = None,
    ) -> int:
        """Add affinity delta and return new total score."""
        # Record the change
        record = AffinityRecord(
            player_id=player_id,
            delta=delta,
            source=source,
            reason=reason,
        )
        db.add(record)

        # Update player's total
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one()
        player.affinity_score = max(0, player.affinity_score + delta)  # floor at 0
        await db.flush()

        return player.affinity_score


affinity_service = AffinityService()
