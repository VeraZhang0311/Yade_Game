"""Player model - stores player state and progress."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="Player")

    # Progress
    current_level_id: Mapped[str] = mapped_column(String(50), default="chapter_01")
    max_unlocked_level: Mapped[str] = mapped_column(String(50), default="chapter_01")

    # Affinity
    affinity_score: Mapped[int] = mapped_column(Integer, default=0)

    # Long-term memory: key facts the character should remember
    memory_facts: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
