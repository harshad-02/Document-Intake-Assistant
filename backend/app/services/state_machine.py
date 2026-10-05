"""Deterministic state machine for conversation flow."""

from __future__ import annotations
from typing import Optional

from app.models.conversation import ConversationState

def get_next_step(state: ConversationState) -> Optional[str]:
    """Determines the next missing field in the conversation.
    
    Order:
    full_name -> home_address -> worldwide_assets -> has_children -> 
    (if has_children: expected_count, then children_names) -> 
    executor -> specific_gifts -> additional_wishes -> "complete".
    """
    doc = state.document
    
    if doc.full_name.status == "missing":
        return "full_name"
    if doc.home_address.status == "missing":
        return "home_address"
    if doc.covers_worldwide_assets.status == "missing":
        return "worldwide_assets"
        
    if doc.children.status == "missing":
        return "has_children"
        
    if doc.children.has_children:
        if doc.children.expected_count is None:
            return "expected_children_count"
        if len(doc.children.names) < doc.children.expected_count:
            return "children_names"
            
    if doc.executor.status == "missing":
        return "executor"
        
    if doc.specific_gifts.status == "missing":
        return "specific_gifts"
        
    if doc.additional_wishes.status == "missing":
        return "additional_wishes"
        
    return "complete"
