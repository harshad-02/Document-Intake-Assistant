"""Document state models."""

from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Status = Literal[
    "missing",
    "confirmed",
    "unconfirmed",
    "declined",
    "unknown",
    "not_decided",
    "not_applicable"
]

class FieldValue(BaseModel):
    value: Optional[str] = None
    status: Status = "missing"

class ChildrenState(BaseModel):
    has_children: Optional[bool] = None
    expected_count: Optional[int] = None
    names: List[str] = Field(default_factory=list)
    status: Status = "missing"

class ExecutorState(BaseModel):
    names: List[str] = Field(default_factory=list)
    relationship: Optional[str] = None
    status: Status = "missing"

class DocumentState(BaseModel):
    full_name: FieldValue = Field(default_factory=FieldValue)
    home_address: FieldValue = Field(default_factory=FieldValue)
    covers_worldwide_assets: FieldValue = Field(default_factory=FieldValue)
    children: ChildrenState = Field(default_factory=ChildrenState)
    executor: ExecutorState = Field(default_factory=ExecutorState)
    specific_gifts: FieldValue = Field(default_factory=FieldValue)
    additional_wishes: FieldValue = Field(default_factory=FieldValue)
