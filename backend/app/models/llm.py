"""LLM response models."""

from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class SpecificGiftExtraction(BaseModel):
    item: str
    recipient: str

class ExtractionUpdates(BaseModel):
    full_name: Optional[str] = None
    home_address: Optional[str] = None
    covers_worldwide_assets: Optional[bool] = None
    asset_region: Optional[str] = None
    asset_items: Optional[List[str]] = None
    has_children: Optional[bool] = None
    expected_children_count: Optional[int] = None
    children_names: Optional[List[str]] = None
    executor_names: Optional[List[str]] = None
    executor_relationship: Optional[str] = None
    executor_status: Optional[str] = None
    specific_gifts: Optional[List[SpecificGiftExtraction]] = None
    additional_wishes: Optional[str] = None

class ExtractionInterpretation(BaseModel):
    status: Literal["clear", "unclear"] = "clear"
    needs_clarification: bool = False
    reason: Optional[str] = None

class LLMExtractionResponse(BaseModel):
    intent: Literal["answer", "correction", "addition", "removal", "confirmation", "generation_confirmation"] = "answer"
    target_fields: List[str] = Field(default_factory=list)
    updates: ExtractionUpdates
    interpretation: ExtractionInterpretation

class LLMResponseGeneratorResponse(BaseModel):
    reply: str
