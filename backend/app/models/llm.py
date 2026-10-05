"""LLM response models."""

from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel

class ExtractionUpdates(BaseModel):
    full_name: Optional[str] = None
    home_address: Optional[str] = None
    covers_worldwide_assets: Optional[str] = None
    has_children: Optional[bool] = None
    expected_children_count: Optional[int] = None
    children_names: List[str] = []
    executor_names: List[str] = []
    executor_relationship: Optional[str] = None
    executor_status: Optional[str] = None
    specific_gifts: List[str] = []
    additional_wishes: Optional[str] = None

class ExtractionInterpretation(BaseModel):
    status: Literal["clear", "unclear"] = "clear"
    needs_clarification: bool = False
    reason: Optional[str] = None

class LLMExtractionResponse(BaseModel):
    updates: ExtractionUpdates
    interpretation: ExtractionInterpretation

class LLMResponseGeneratorResponse(BaseModel):
    reply: str
