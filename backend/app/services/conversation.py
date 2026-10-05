"""Conversation service: orchestrates LLM calls, state machine, and response building."""

from __future__ import annotations

import logging
from typing import Any

from app.documents.generator import generate_document
from app.models.api import MessageResponse, StateSnapshot, FieldSnapshot, MessageInfo, SessionResponse
from app.models.conversation import Message
from app.services.state_manager import update_state
from app.services.state_machine import get_next_step
from app.services.llm_extractor import extract_updates
from app.services.llm_responder import generate_response
from app.store import store
from app.config import settings

logger = logging.getLogger(__name__)

class SessionNotFoundError(Exception):
    pass

def _state_to_snapshot(state) -> StateSnapshot:
    """Convert internal DocumentState to API snapshot for the frontend."""
    doc = state.document
    return StateSnapshot(
        full_name=FieldSnapshot(value=doc.full_name.value, status=doc.full_name.status.name if hasattr(doc.full_name.status, 'name') else doc.full_name.status),
        home_address=FieldSnapshot(value=doc.home_address.value, status=doc.home_address.status.name if hasattr(doc.home_address.status, 'name') else doc.home_address.status),
        covers_worldwide_assets=FieldSnapshot(value=doc.covers_worldwide_assets.value, status=doc.covers_worldwide_assets.status.name if hasattr(doc.covers_worldwide_assets.status, 'name') else doc.covers_worldwide_assets.status),
        has_children=FieldSnapshot(value=doc.children.has_children, status=doc.children.status.name if hasattr(doc.children.status, 'name') else doc.children.status),
        children=FieldSnapshot(value=doc.children.names, status=doc.children.status.name if hasattr(doc.children.status, 'name') else doc.children.status),
        executor_name=FieldSnapshot(value=", ".join(doc.executor.names) if doc.executor.names else None, status=doc.executor.status.name if hasattr(doc.executor.status, 'name') else doc.executor.status),
        executor_relationship=FieldSnapshot(value=doc.executor.relationship, status=doc.executor.status.name if hasattr(doc.executor.status, 'name') else doc.executor.status),
        specific_gifts=FieldSnapshot(value=[g.strip() for g in doc.specific_gifts.value.split(',')] if doc.specific_gifts.value else [], status=doc.specific_gifts.status.name if hasattr(doc.specific_gifts.status, 'name') else doc.specific_gifts.status),
        additional_wishes=FieldSnapshot(value=doc.additional_wishes.value, status=doc.additional_wishes.status.name if hasattr(doc.additional_wishes.status, 'name') else doc.additional_wishes.status)
    )

def _build_recent_messages(session) -> list[dict[str, str]]:
    max_msgs = settings.MAX_HISTORY_MESSAGES
    recent = session.messages[-max_msgs:] if len(session.messages) > max_msgs else session.messages
    return [{"role": m.role, "content": m.content} for m in recent]

async def handle_message(session_id: str, user_message: str) -> MessageResponse:
    session = store.get(session_id)
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    lock = store.get_lock(session_id)
    async with lock:
        warnings = []
        
        # 1. Extraction LLM #1
        patch = await extract_updates(session.state, user_message)
        
        if not patch:
            warnings.append("Could not parse LLM extraction response. State unchanged.")
            # Unchanged state
        else:
            # 2. State update (deterministic)
            session.state, merge_warnings = update_state(session.state, patch)
            warnings.extend(merge_warnings)

        # 3. State machine gets next step
        next_step = get_next_step(session.state)
        session.state.current_step = next_step
        
        # 4. Response Generator LLM #2
        extracted_dict = patch.updates.model_dump(exclude_unset=True) if patch else {}
        reply = await generate_response(session.state, next_step, warnings, _build_recent_messages(session), extracted_dict)
        
        session.messages.append(Message(role="user", content=user_message))
        session.messages.append(Message(role="assistant", content=reply))
        session.llm_call_count += 2
        
        store.save(session)
        
        return MessageResponse(
            reply=reply,
            state=_state_to_snapshot(session.state),
            document=generate_document(session.state.document),
            missing_fields=[next_step] if next_step != "complete" else [],
            warnings=warnings
        )

def handle_direct_edit(session_id: str, field_name: str, value: Any) -> dict:
    session = store.get(session_id)
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")
        
    doc = session.state.document
    if field_name == "full_name":
        doc.full_name.value = value
        doc.full_name.status = "confirmed" if value else "missing"
    elif field_name == "home_address":
        doc.home_address.value = value
        doc.home_address.status = "confirmed" if value else "missing"
    # Additional handling skipped for brevity for UI edits.
    # UI edits are out of scope for the major refactor besides making it not crash.
    store.save(session)
    next_step = get_next_step(session.state)
    session.state.current_step = next_step
    
    return {
        "state": _state_to_snapshot(session.state),
        "document": generate_document(session.state.document),
        "missing_fields": [next_step] if next_step != "complete" else [],
        "warnings": []
    }
