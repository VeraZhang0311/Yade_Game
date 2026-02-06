"""Affinity record model - tracks affinity score change events."""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AffinityRecord(Base):
    __tablename__ = "affinity_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    delta: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50))  # "level_choice" or "chat"
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
