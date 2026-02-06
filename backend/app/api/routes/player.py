"""Player endpoints - create and manage player state."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerState, PlayerUpdate, PlayerResetResponse
from app.services.affinity_service import affinity_service

router = APIRouter()


async def _get_player_or_404(player_id: int, db: AsyncSession) -> Player:
    """Fetch a player by ID or raise 404."""
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


def _player_to_response(player: Player) -> PlayerState:
    """Convert ORM model to response schema with computed fields."""
    return PlayerState(
        id=player.id,
        name=player.name,
        nickname=player.nickname,
        current_level_id=player.current_level_id,
        max_unlocked_level=player.max_unlocked_level,
        affinity_score=player.affinity_score,
        affinity_tier=affinity_service.get_tier(player.affinity_score),
        memory_facts=player.memory_facts or {},
        bio=player.bio,
        created_at=player.created_at,
        updated_at=player.updated_at,
    )


@router.post("/", response_model=PlayerState, status_code=201)
async def create_player(data: PlayerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new player."""
    player = Player(name=data.name, nickname=data.nickname)
    db.add(player)
    await db.flush()
    await db.refresh(player)
    return _player_to_response(player)


@router.get("/{player_id}", response_model=PlayerState)
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    """Get current player state."""
    player = await _get_player_or_404(player_id, db)
    return _player_to_response(player)


@router.patch("/{player_id}", response_model=PlayerState)
async def update_player(
    player_id: int, data: PlayerUpdate, db: AsyncSession = Depends(get_db)
):
    """Update player profile fields (name, nickname, bio)."""
    player = await _get_player_or_404(player_id, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(player, field, value)

    await db.flush()
    await db.refresh(player)
    return _player_to_response(player)


@router.delete("/{player_id}", status_code=204)
async def delete_player(player_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a player and all associated data."""
    player = await _get_player_or_404(player_id, db)
    await db.delete(player)
    await db.flush()


@router.post("/{player_id}/reset", response_model=PlayerResetResponse)
async def reset_player_progress(player_id: int, db: AsyncSession = Depends(get_db)):
    """Reset player progress to the beginning (keeps player profile)."""
    player = await _get_player_or_404(player_id, db)
    player.reset_progress()
    await db.flush()
    await db.refresh(player)
    return PlayerResetResponse(
        message="Progress reset successfully",
        player=_player_to_response(player),
    )
