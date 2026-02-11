"""Level-related Pydantic schemas."""

from pydantic import BaseModel


class DialogueOption(BaseModel):
    """A single selectable option in a dialogue node."""
    id: str
    text: str
    affinity_delta: int = 0
    next_node: str  # which node this choice leads to
    is_major: bool = False  # major choices affect story branching


class DialogueNode(BaseModel):
    """A single dialogue node (one screen of dialogue).

    Node types by speaker:
    - "narrator": scene descriptions, stage directions
    - "yade": Yade's spoken dialogue
    - "yade_inner": Yade's internal thoughts (shown differently in UI)
    - "girl" / other character names: NPC dialogue
    - "action": character action descriptions (no speech bubble)
    """
    id: str
    speaker: str  # "narrator", "yade", "yade_inner", "girl", "action", etc.
    text: str
    action: str | None = None  # optional stage direction, e.g. "抬起头，拍拍手上的泥土"
    options: list[DialogueOption] | None = None  # None = auto-advance
    next_node: str | None = None  # for auto-advance nodes
    # Conditional branching: jump based on a previous choice
    # e.g. {"choice_3": {"A": "branch_together", "B": "branch_alone", "C": "branch_alone"}}
    condition: dict[str, dict[str, str]] | None = None
    is_ending: bool = False


class LevelData(BaseModel):
    """Full level definition loaded from YAML."""
    id: str
    title: str
    order: int
    scene: str = ""  # scene name/label, e.g. "情景1: 与小女孩的初遇"
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
