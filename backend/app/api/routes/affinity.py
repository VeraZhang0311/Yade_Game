"""Affinity endpoints - query affinity status."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.player import Player
from app.schemas.affinity import AffinityStatus
from app.services.affinity_service import affinity_service

router = APIRouter()


@router.get("/{player_id}", response_model=AffinityStatus)
async def get_affinity(player_id: int, db: AsyncSession = Depends(get_db)):
    """Get current affinity status for a player."""
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one()
    return AffinityStatus(
        score=player.affinity_score,
        level=affinity_service.get_tier(player.affinity_score),
    )
