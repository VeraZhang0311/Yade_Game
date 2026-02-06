"""Player model - stores player state and progress."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

# Default starting level
DEFAULT_LEVEL = "chapter_01"


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="Player")
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Progress
    current_level_id: Mapped[str] = mapped_column(String(50), default=DEFAULT_LEVEL)
    max_unlocked_level: Mapped[str] = mapped_column(String(50), default=DEFAULT_LEVEL)

    # Affinity
    affinity_score: Mapped[int] = mapped_column(Integer, default=0)

    # Long-term memory: key facts the character should remember
    # e.g. {"favorite_color": "蓝色", "pet_name": "小白"}
    memory_facts: Mapped[dict] = mapped_column(JSON, default=dict)

    # Player's personal note / bio (optional)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def reset_progress(self) -> None:
        """Reset player to the beginning of the game."""
        self.current_level_id = DEFAULT_LEVEL
        self.max_unlocked_level = DEFAULT_LEVEL
        self.affinity_score = 0
        self.memory_facts = {}
