"""Deterministic state update logic."""

from __future__ import annotations
from typing import Tuple

from app.models.conversation import ConversationState
from app.models.llm import LLMExtractionResponse

def update_state(state: ConversationState, patch: LLMExtractionResponse) -> Tuple[ConversationState, list[str]]:
    """Applies the LLM patch to the state based on business rules."""
    warnings = []
    
    # If the user declined generation at the final step, it's not an unclear response
    if patch.interpretation.needs_clarification and state.current_step == "generation_confirmation":
        pass
    elif patch.interpretation.status == "unclear" or patch.interpretation.needs_clarification:
        return state, ["Response was unclear, state unchanged."]

    u = patch.updates
    doc = state.document
    step = state.current_step

    def is_targeted(field: str) -> bool:
        if not patch.target_fields:
            return True
        if field in patch.target_fields:
            return True
        for tf in patch.target_fields:
            if field in tf or tf in field:
                return True
        return False

    # Apply updates defensively
    if u.full_name is not None and is_targeted("full_name"):
        doc.full_name.value = u.full_name.title()
        doc.full_name.status = "confirmed"

    if u.home_address is not None and is_targeted("home_address"):
        doc.home_address.value = u.home_address
        doc.home_address.status = "confirmed"

    if u.covers_worldwide_assets is not None and (is_targeted("covers_worldwide_assets") or is_targeted("assets")):
        doc.covers_worldwide_assets.covers_worldwide = u.covers_worldwide_assets
        if u.asset_region is not None:
            doc.covers_worldwide_assets.region = u.asset_region
        doc.covers_worldwide_assets.status = "confirmed"

    if u.asset_items is not None and is_targeted("assets"):
        if patch.intent in ("correction", "removal"):
            doc.assets.items = u.asset_items
        else:
            for item in u.asset_items:
                if item not in doc.assets.items:
                    doc.assets.items.append(item)
        doc.assets.status = "confirmed"

    # Children
    # If the LLM extracted names or a count, we can implicitly assume has_children is True.
    implicit_has_children = False
    if (u.children_names or u.expected_children_count) and is_targeted("children"):
        implicit_has_children = True

    if (u.has_children is not None or implicit_has_children) and is_targeted("children"):
        doc.children.has_children = u.has_children if u.has_children is not None else True
        doc.children.status = "confirmed"
        if not doc.children.has_children:
            doc.children.names = []
            doc.children.expected_count = None
            doc.children.status = "none"

    if u.expected_children_count is not None and doc.children.has_children and is_targeted("children"):
        doc.children.expected_count = u.expected_children_count
        doc.children.status = "confirmed"

    if u.children_names is not None and doc.children.has_children and is_targeted("children"):
        capitalized_names = [name.title() for name in u.children_names]
        if patch.intent in ("correction", "removal"):
            doc.children.names = capitalized_names
        else:
            for name in capitalized_names:
                if name not in doc.children.names:
                    doc.children.names.append(name)
        
        # If we have names but no count, imply the count from the names
        if doc.children.expected_count is None and len(doc.children.names) > 0:
            doc.children.expected_count = len(doc.children.names)
            
        doc.children.status = "confirmed"

    # Executor
    if u.executor_status == "not_decided" and is_targeted("executor"):
        doc.executor.status = "not_decided"
    elif (u.executor_status == "declined" or (u.executor_names is not None and len(u.executor_names) == 0 and patch.intent == "removal")) and is_targeted("executor"):
        doc.executor.status = "none"
        doc.executor.names = []
        doc.executor.relationship = None
    elif (u.executor_names is not None or u.executor_relationship is not None) and is_targeted("executor"):
        if u.executor_names is not None:
            capitalized_executor_names = [name.title() for name in u.executor_names]
            if patch.intent in ("correction", "removal"):
                doc.executor.names = capitalized_executor_names
            else:
                for name in capitalized_executor_names:
                    if name not in doc.executor.names:
                        doc.executor.names.append(name)
        if u.executor_relationship is not None:
            doc.executor.relationship = u.executor_relationship
        else:
            # Derive relationship contextually if it wasn't explicitly extracted
            # but the names match a known group (e.g. children)
            if doc.children.has_children and doc.children.names and doc.executor.names:
                if all(name in doc.children.names for name in doc.executor.names):
                    if len(doc.executor.names) == 1:
                        doc.executor.relationship = "child"
                    else:
                        doc.executor.relationship = "children"
                        
        doc.executor.status = "confirmed"

    # Specific gifts
    if u.specific_gifts is not None and is_targeted("specific_gifts"):
        from app.models.document import SpecificGift
        new_gifts = [SpecificGift(item=g.item, recipient=g.recipient.title() if g.recipient else g.recipient) for g in u.specific_gifts]
        if patch.intent in ("correction", "removal"):
            doc.specific_gifts.items = new_gifts
        else:
            doc.specific_gifts.items.extend(new_gifts)
        doc.specific_gifts.status = "confirmed"
        if not doc.specific_gifts.items and patch.intent == "removal":
            doc.specific_gifts.status = "none"
    
    if step == "specific_gifts" and u.specific_gifts is None and patch.intent == "answer" and not doc.specific_gifts.items and is_targeted("specific_gifts"):
        # If user answered the specific gifts question with "no" (meaning empty patch for gifts)
        doc.specific_gifts.status = "none"

    # Additional wishes
    if u.additional_wishes is not None and is_targeted("additional_wishes"):
        doc.additional_wishes.text = u.additional_wishes
        doc.additional_wishes.status = "confirmed"
        
    if step == "additional_wishes" and u.additional_wishes is None and patch.intent == "answer" and not doc.additional_wishes.text and is_targeted("additional_wishes"):
        doc.additional_wishes.status = "none"

    if patch.intent == "generation_confirmation":
        state.generation_confirmed = True

    return state, warnings
