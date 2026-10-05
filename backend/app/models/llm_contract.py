"""LLM contract models — the schema the LLM must return each turn."""

from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class FieldName(str, enum.Enum):
    """Valid field names the LLM may reference."""
    FULL_NAME = "full_name"
    HOME_ADDRESS = "home_address"
    COVERS_WORLDWIDE_ASSETS = "covers_worldwide_assets"
    HAS_CHILDREN = "has_children"
    CHILDREN = "children"
    EXECUTOR_NAME = "executor_name"
    EXECUTOR_RELATIONSHIP = "executor_relationship"
    SPECIFIC_GIFTS = "specific_gifts"
    ADDITIONAL_WISHES = "additional_wishes"


class Op(str, enum.Enum):
    """Operations on a field."""
    SET = "set"
    CORRECT = "correct"
    CLEAR = "clear"


class Certainty(str, enum.Enum):
    """How certain the LLM is about the extracted value."""
    CLEAR = "clear"
    AMBIGUOUS = "ambiguous"


class ClarificationReason(str, enum.Enum):
    """Reason a clarification is needed."""
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    CONTRADICTORY = "contradictory"


class ProposedUpdate(BaseModel):
    """A single proposed change from the LLM."""
    field: FieldName
    op: Op
    value: Optional[object] = None
    evidence: str = ""
    certainty: Certainty = Certainty.CLEAR

    model_config = {"extra": "forbid"}


class Clarification(BaseModel):
    """A follow-up item the LLM thinks is needed."""
    field: FieldName
    reason: ClarificationReason

    model_config = {"extra": "forbid"}


class LLMTurnResponse(BaseModel):
    """The complete response expected from the LLM each turn."""
    updates: list[ProposedUpdate] = Field(default_factory=list)
    clarifications: list[Clarification] = Field(default_factory=list)
    reply: str

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def reply_must_not_be_empty(self) -> "LLMTurnResponse":
        if not self.reply or not self.reply.strip():
            raise ValueError("reply must not be empty")
        return self
