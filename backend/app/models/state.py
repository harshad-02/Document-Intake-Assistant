"""State models: field statuses, personal wishes, and session."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class FieldStatus(str, enum.Enum):
    """Status of a single field in the state."""
    UNKNOWN = "unknown"
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"


class StateField(BaseModel):
    """A single field with a value and a status."""
    value: Any = None
    status: FieldStatus = FieldStatus.UNKNOWN


class PersonalWishes(BaseModel):
    """All fields to collect for the Personal Wishes Document.

    Every field defaults to unknown / null.
    List fields default to null (not empty list) — null means 'never asked',
    empty list means 'user explicitly said none'.
    """
    full_name: StateField = Field(default_factory=StateField)
    home_address: StateField = Field(default_factory=StateField)
    covers_worldwide_assets: StateField = Field(default_factory=StateField)
    has_children: StateField = Field(default_factory=StateField)
    children: StateField = Field(default_factory=StateField)
    executor_name: StateField = Field(default_factory=StateField)
    executor_relationship: StateField = Field(default_factory=StateField)
    specific_gifts: StateField = Field(default_factory=StateField)
    additional_wishes: StateField = Field(default_factory=StateField)


class Message(BaseModel):
    """A single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Session(BaseModel):
    """A conversation session with state and history."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: PersonalWishes = Field(default_factory=PersonalWishes)
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    llm_call_count: int = 0
