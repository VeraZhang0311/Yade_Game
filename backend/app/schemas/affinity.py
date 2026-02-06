"""Affinity-related Pydantic schemas."""

from pydantic import BaseModel


class AffinityStatus(BaseModel):
    score: int
    level: str  # descriptive tier, e.g. "stranger", "acquaintance", "friend", ...


class AffinityChangeEvent(BaseModel):
    delta: int
    source: str
    reason: str | None = None
