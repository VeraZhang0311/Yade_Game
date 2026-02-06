"""Level models - stores level definitions and player choices within levels."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Level(Base):
    """Metadata about a level, loaded from YAML data files."""
    __tablename__ = "levels"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. "chapter_01"
    title: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer)  # linear ordering


class LevelChoice(Base):
    """Records which choices a player made in a level."""
    __tablename__ = "level_choices"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    level_id: Mapped[str] = mapped_column(String(50))
    node_id: Mapped[str] = mapped_column(String(100))  # dialogue node identifier
    choice_id: Mapped[str] = mapped_column(String(100))  # chosen option identifier
    affinity_delta: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
