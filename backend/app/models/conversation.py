"""Conversation models."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field
from app.models.document import DocumentState

class Message(BaseModel):
    """A single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationState(BaseModel):
    current_step: str = "full_name"
    document: DocumentState = Field(default_factory=DocumentState)

class Session(BaseModel):
    """A conversation session with state and history."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: ConversationState = Field(default_factory=ConversationState)
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    llm_call_count: int = 0
