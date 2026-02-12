"""Level endpoints - list levels, record choices, complete levels, query progress."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.player import Player
from app.models.level import LevelChoice
from app.schemas.level import (
    LevelSummary,
    MakeChoiceRequest,
    MakeChoiceResponse,
    LevelCompleteRequest,
    LevelCompleteResponse,
    LevelProgressResponse,
)
from app.services.level_service import level_service
from app.services.affinity_service import affinity_service

router = APIRouter()


async def _get_player_or_404(player_id: int, db: AsyncSession) -> Player:
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/", response_model=list[LevelSummary])
async def list_levels(player_id: int, db: AsyncSession = Depends(get_db)):
    """List all levels with unlock status for a player."""
    player = await _get_player_or_404(player_id, db)

    all_levels = level_service.list_levels()
    unlocked_ids = set(level_service.get_unlocked_levels(player.max_unlocked_level))

    return [
        LevelSummary(
            id=lvl["id"],
            title=lvl["title"],
            order=lvl["order"],
            is_unlocked=lvl["id"] in unlocked_ids,
        )
        for lvl in all_levels
    ]


@router.post("/choice", response_model=MakeChoiceResponse)
async def make_choice(req: MakeChoiceRequest, player_id: int, db: AsyncSession = Depends(get_db)):
    """Record a player's choice and return affinity change."""
    player = await _get_player_or_404(player_id, db)

    # Look up the choice config from YAML
    choice_opt = level_service.get_choice_affinity(req.level_id, req.node_id, req.choice_id)
    if choice_opt is None:
        raise HTTPException(status_code=400, detail="Invalid level, node, or choice ID")

    # Record the choice in DB
    choice_record = LevelChoice(
        player_id=player_id,
        level_id=req.level_id,
        node_id=req.node_id,
        choice_id=req.choice_id,
        affinity_delta=choice_opt.affinity_delta,
    )
    db.add(choice_record)

    # Update affinity score
    new_total = await affinity_service.add_affinity(
        db, player_id, choice_opt.affinity_delta, "level_choice",
        reason=f"{req.level_id}/{req.node_id}/{req.choice_id}",
    )

    return MakeChoiceResponse(
        affinity_delta=choice_opt.affinity_delta,
        new_affinity_total=new_total,
        affinity_tier=affinity_service.get_tier(new_total),
    )


@router.post("/complete", response_model=LevelCompleteResponse)
async def complete_level(
    req: LevelCompleteRequest, player_id: int, db: AsyncSession = Depends(get_db)
):
    """Mark a level as completed and unlock the next one."""
    player = await _get_player_or_404(player_id, db)

    # Verify the level exists
    try:
        level_service.load_level(req.level_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Level not found")

    # Determine next level
    next_level_id = level_service.get_next_level_id(req.level_id)
    unlocked = False

    if next_level_id:
        # Only unlock if player hasn't already passed this point
        all_levels = level_service.list_levels()
        current_max_order = _level_order(player.max_unlocked_level, all_levels)
        next_order = _level_order(next_level_id, all_levels)
        if next_order > current_max_order:
            player.max_unlocked_level = next_level_id
            unlocked = True

    # Advance current_level_id
    player.current_level_id = next_level_id or req.level_id

    await db.flush()

    return LevelCompleteResponse(
        next_level_id=next_level_id,
        unlocked=unlocked,
        total_affinity=player.affinity_score,
        affinity_tier=affinity_service.get_tier(player.affinity_score),
    )


@router.get("/progress", response_model=LevelProgressResponse)
async def get_progress(player_id: int, db: AsyncSession = Depends(get_db)):
    """Get current player progress across all levels."""
    player = await _get_player_or_404(player_id, db)

    unlocked_levels = level_service.get_unlocked_levels(player.max_unlocked_level)

    return LevelProgressResponse(
        current_level=player.current_level_id,
        unlocked_levels=unlocked_levels,
        total_affinity=player.affinity_score,
        affinity_tier=affinity_service.get_tier(player.affinity_score),
    )


def _level_order(level_id: str, all_levels: list[dict]) -> int:
    for lvl in all_levels:
        if lvl["id"] == level_id:
            return lvl["order"]
    return 0
