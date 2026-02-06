"""Player-related Pydantic schemas."""

from pydantic import BaseModel


class PlayerCreate(BaseModel):
    name: str = "Player"


class PlayerState(BaseModel):
    id: int
    name: str
    current_level_id: str
    max_unlocked_level: str
    affinity_score: int
    memory_facts: dict

    model_config = {"from_attributes": True}
