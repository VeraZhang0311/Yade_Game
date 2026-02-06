"""Level-related Pydantic schemas."""

from pydantic import BaseModel


class DialogueOption(BaseModel):
    """A single selectable option in a dialogue node."""
    id: str
    text: str
    affinity_delta: int = 0
    next_node: str  # which node this choice leads to


class DialogueNode(BaseModel):
    """A single dialogue node (one screen of dialogue)."""
    id: str
    speaker: str  # "yade", "narrator", etc.
    text: str
    options: list[DialogueOption] | None = None  # None = auto-advance
    next_node: str | None = None  # for auto-advance nodes
    is_ending: bool = False


class LevelData(BaseModel):
    """Full level definition loaded from YAML."""
    id: str
    title: str
    order: int
    start_node: str
    nodes: dict[str, DialogueNode]


class LevelSummary(BaseModel):
    id: str
    title: str
    order: int
    is_unlocked: bool


class MakeChoiceRequest(BaseModel):
    level_id: str
    node_id: str
    choice_id: str


class MakeChoiceResponse(BaseModel):
    next_node: DialogueNode | None
    affinity_delta: int
    new_affinity_total: int
