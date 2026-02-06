"""Player-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    name: str = Field(default="Player", min_length=1, max_length=100)
    nickname: str | None = None


class PlayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    nickname: str | None = None
    bio: str | None = None


class PlayerState(BaseModel):
    id: int
    name: str
    nickname: str | None
    current_level_id: str
    max_unlocked_level: str
    affinity_score: int
    affinity_tier: str = ""
    memory_facts: dict
    bio: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlayerResetResponse(BaseModel):
    message: str
    player: PlayerState
