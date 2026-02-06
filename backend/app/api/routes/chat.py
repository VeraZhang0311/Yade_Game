"""Chat REST endpoints - for non-WebSocket chat operations."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.chat_history import ChatMessage
from app.schemas.chat import ChatHistory

router = APIRouter()


@router.get("/history/{player_id}", response_model=ChatHistory)
async def get_chat_history(
    player_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    """Get recent chat history for a player."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.player_id == player_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()  # chronological order

    return ChatHistory(
        messages=[{"role": m.role, "content": m.content} for m in messages]
    )
