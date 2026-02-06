"""Chat-related Pydantic schemas."""

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    """Incoming chat message from the player."""
    content: str


class ChatMessageOut(BaseModel):
    """Outgoing chat message from Yade."""
    content: str
    is_stream_end: bool = False


class ChatHistory(BaseModel):
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]
