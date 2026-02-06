"""Level endpoints - list levels, get level data, make choices."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.player import Player
from app.models.level import LevelChoice
from app.schemas.level import LevelData, LevelSummary, MakeChoiceRequest, MakeChoiceResponse
from app.services.level_service import level_service
from app.services.affinity_service import affinity_service

router = APIRouter()


@router.get("/", response_model=list[LevelSummary])
async def list_levels(player_id: int, db: AsyncSession = Depends(get_db)):
    """List all levels with unlock status for a player."""
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one()

    all_levels = level_service.list_levels()
    summaries = []
    for lvl in all_levels:
        summaries.append(LevelSummary(
            id=lvl["id"],
            title=lvl["title"],
            order=lvl["order"],
            is_unlocked=lvl["order"] <= _level_order(player.max_unlocked_level, all_levels),
        ))
    return summaries


@router.get("/{level_id}", response_model=LevelData)
async def get_level(level_id: str, player_id: int, db: AsyncSession = Depends(get_db)):
    """Get full level data (dialogue tree) if the player has unlocked it."""
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one()

    all_levels = level_service.list_levels()
    level = level_service.load_level(level_id)

    if level.order > _level_order(player.max_unlocked_level, all_levels):
        raise HTTPException(status_code=403, detail="Level not unlocked yet")

    return level


@router.post("/choice", response_model=MakeChoiceResponse)
async def make_choice(req: MakeChoiceRequest, player_id: int, db: AsyncSession = Depends(get_db)):
    """Record a player's choice in a level and return the next dialogue node."""
    level = level_service.load_level(req.level_id)

    node = level.nodes.get(req.node_id)
    if not node or not node.options:
        raise HTTPException(status_code=400, detail="Invalid node or no options")

    chosen = next((o for o in node.options if o.id == req.choice_id), None)
    if not chosen:
        raise HTTPException(status_code=400, detail="Invalid choice")

    # Record choice
    choice_record = LevelChoice(
        player_id=player_id,
        level_id=req.level_id,
        node_id=req.node_id,
        choice_id=req.choice_id,
        affinity_delta=chosen.affinity_delta,
    )
    db.add(choice_record)

    # Update affinity
    new_total = await affinity_service.add_affinity(
        db, player_id, chosen.affinity_delta, "level_choice",
        reason=f"Chose '{chosen.text}' in {req.level_id}/{req.node_id}",
    )

    # Get next node
    next_node = level.nodes.get(chosen.next_node)

    # If next node is an ending, unlock the next level
    if next_node and next_node.is_ending:
        next_level_id = level_service.get_next_level_id(req.level_id)
        if next_level_id:
            result = await db.execute(select(Player).where(Player.id == player_id))
            player = result.scalar_one()
            player.max_unlocked_level = next_level_id
            player.current_level_id = next_level_id

    return MakeChoiceResponse(
        next_node=next_node,
        affinity_delta=chosen.affinity_delta,
        new_affinity_total=new_total,
    )


def _level_order(level_id: str, all_levels: list[dict]) -> int:
    for lvl in all_levels:
        if lvl["id"] == level_id:
            return lvl["order"]
    return 0
