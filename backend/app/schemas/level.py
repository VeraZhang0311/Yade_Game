"""Level-related Pydantic schemas.

Simplified for frontend-driven architecture:
- Dialogue tree lives in frontend (YarnSpinner .yarn files)
- Backend only stores: choice→affinity mapping, level ordering, player progress
"""

from pydantic import BaseModel


# --- Internal: loaded from YAML ---

class ChoiceOption(BaseModel):
    """Backend config for a single choice option."""
    affinity_delta: int = 0
    is_major: bool = False


class LevelConfig(BaseModel):
    """Backend-side level config loaded from YAML (no dialogue content)."""
    id: str
    title: str
    order: int
    choices: dict[str, dict[str, ChoiceOption]]  # node_id -> {option_id -> config}


# --- API request/response schemas ---

class LevelSummary(BaseModel):
    """Returned when listing levels with unlock status."""
    id: str
    title: str
    order: int
    is_unlocked: bool


class MakeChoiceRequest(BaseModel):
    """Frontend tells backend: player chose option X at node Y in level Z."""
    level_id: str
    node_id: str
    choice_id: str


class MakeChoiceResponse(BaseModel):
    """Backend returns: affinity change from this choice."""
    affinity_delta: int
    new_affinity_total: int
    affinity_tier: str


class LevelCompleteRequest(BaseModel):
    """Frontend tells backend: player finished a level."""
    level_id: str
    ending_node: str | None = None  # optional: which ending was reached


class LevelCompleteResponse(BaseModel):
    """Backend returns: what got unlocked."""
    next_level_id: str | None
    unlocked: bool
    total_affinity: int
    affinity_tier: str


class LevelProgressResponse(BaseModel):
    """Current player progress across all levels."""
    current_level: str
    unlocked_levels: list[str]
    total_affinity: int
    affinity_tier: str
