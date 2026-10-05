"""API request/response models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.document import Status


# ── Requests ──────────────────────────────────────────────────────────────────


class SendMessageRequest(BaseModel):
    """User sends a chat message."""
    message: str = Field(..., min_length=1, max_length=2000)


class EditFieldRequest(BaseModel):
    """Direct edit of a single field via the UI."""
    field: str
    value: Any  # type checked in the service layer


# ── Responses ─────────────────────────────────────────────────────────────────


class FieldSnapshot(BaseModel):
    """A single field's current state for the API consumer."""
    value: Any = None
    status: Status = "unknown"


class StateSnapshot(BaseModel):
    """Complete state of all fields."""
    full_name: FieldSnapshot = Field(default_factory=FieldSnapshot)
    home_address: FieldSnapshot = Field(default_factory=FieldSnapshot)
    covers_worldwide_assets: FieldSnapshot = Field(default_factory=FieldSnapshot)
    assets: FieldSnapshot = Field(default_factory=FieldSnapshot)
    has_children: FieldSnapshot = Field(default_factory=FieldSnapshot)
    children: FieldSnapshot = Field(default_factory=FieldSnapshot)
    executor_name: FieldSnapshot = Field(default_factory=FieldSnapshot)
    executor_relationship: FieldSnapshot = Field(default_factory=FieldSnapshot)
    specific_gifts: FieldSnapshot = Field(default_factory=FieldSnapshot)
    additional_wishes: FieldSnapshot = Field(default_factory=FieldSnapshot)


class MessageInfo(BaseModel):
    """A message returned in history."""
    role: str
    content: str


class SessionResponse(BaseModel):
    """Returned when creating or fetching a session."""
    id: str
    state: StateSnapshot
    document: str
    missing_fields: list[str]
    messages: list[MessageInfo] = Field(default_factory=list)


class MessageResponse(BaseModel):
    """Returned after sending a user message."""
    reply: str
    state: StateSnapshot
    document: str
    missing_fields: list[str]
    warnings: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health-check response."""
    status: str = "ok"
    provider: str
    configured: bool


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
