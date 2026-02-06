"""Player endpoints - create and manage player state."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerState

router = APIRouter()


@router.post("/", response_model=PlayerState)
async def create_player(data: PlayerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new player (MVP: single player, but supports multiple)."""
    player = Player(name=data.name)
    db.add(player)
    await db.flush()
    await db.refresh(player)
    return player


@router.get("/{player_id}", response_model=PlayerState)
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    """Get current player state."""
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one()
    return player
