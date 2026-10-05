"""Deterministic state update logic."""

from __future__ import annotations
from typing import Tuple

from app.models.conversation import ConversationState
from app.models.llm import LLMExtractionResponse

def update_state(state: ConversationState, patch: LLMExtractionResponse) -> Tuple[ConversationState, list[str]]:
    """Applies the LLM patch to the state based on business rules."""
    warnings = []
    
    # We only update state if interpretation is clear.
    if patch.interpretation.status == "unclear" or patch.interpretation.needs_clarification:
        return state, ["Response was unclear, state unchanged."]

    u = patch.updates
    doc = state.document
    step = state.current_step

    # Apply updates defensively, mostly scoped to current_step (but allowing corrections)
    if u.full_name is not None:
        doc.full_name.value = u.full_name
        doc.full_name.status = "confirmed"

    if u.home_address is not None:
        doc.home_address.value = u.home_address
        doc.home_address.status = "confirmed"

    if u.covers_worldwide_assets is not None:
        val = str(u.covers_worldwide_assets).strip().lower()
        if val in ["true", "yes", "worldwide", "all", "worldwide assets"]:
            doc.covers_worldwide_assets.value = "worldwide"
        else:
            doc.covers_worldwide_assets.value = u.covers_worldwide_assets
        doc.covers_worldwide_assets.status = "confirmed"

    # Children
    if u.has_children is not None:
        doc.children.has_children = u.has_children
        doc.children.status = "confirmed"
        if not u.has_children:
            doc.children.names = []
            doc.children.expected_count = None
            doc.children.status = "not_applicable"

    if u.expected_children_count is not None and doc.children.has_children:
        doc.children.expected_count = u.expected_children_count
        doc.children.status = "confirmed"

    if u.children_names and doc.children.has_children:
        for name in u.children_names:
            if name not in doc.children.names:
                doc.children.names.append(name)
        doc.children.status = "confirmed"
        if doc.children.expected_count and len(doc.children.names) >= doc.children.expected_count:
            # We have all the children
            pass

    # Executor - if step is executor, a bare "no" maps to "not_decided".
    # The LLM prompt should return executor_status = "not_decided" in this case.
    if u.executor_status == "not_decided":
        doc.executor.status = "not_decided"
    elif u.executor_status == "declined":
        doc.executor.status = "declined"
    elif u.executor_names:
        for name in u.executor_names:
            if name not in doc.executor.names:
                doc.executor.names.append(name)
        if u.executor_relationship:
            doc.executor.relationship = u.executor_relationship
        doc.executor.status = "confirmed"

    # Specific gifts
    if u.specific_gifts:
        # For simplicity, if we get gifts, we just join them.
        existing = doc.specific_gifts.value
        new_gifts = ", ".join(u.specific_gifts)
        if existing:
            doc.specific_gifts.value = f"{existing}, {new_gifts}"
        else:
            doc.specific_gifts.value = new_gifts
        doc.specific_gifts.status = "confirmed"
    
    # If the user says they have no specific gifts, LLM might return an empty list but interpretation is clear.
    # To handle a clear "no" on gifts:
    if step == "specific_gifts" and not u.specific_gifts:
        # LLM couldn't extract anything from "no", but it's clear.
        doc.specific_gifts.status = "not_applicable"

    # Additional wishes
    if u.additional_wishes:
        doc.additional_wishes.value = u.additional_wishes
        doc.additional_wishes.status = "confirmed"
        
    if step == "additional_wishes" and not u.additional_wishes:
        doc.additional_wishes.status = "not_applicable"

    return state, warnings
