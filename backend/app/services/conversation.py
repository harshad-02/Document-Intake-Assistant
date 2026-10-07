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
    ww = doc.covers_worldwide_assets
    ww_val = None
    if ww.covers_worldwide is not None:
        specific_text = ""
        if ww.covers_worldwide is False:
            parts = []
            if ww.region:
                parts.append(ww.region)
            if doc.assets.items:
                parts.append(", ".join(doc.assets.items))
            specific_text = "; ".join(parts)
            
        ww_val = {
            "worldwide": ww.covers_worldwide is True,
            "specific": ww.covers_worldwide is False,
            "region": specific_text
        }

    return StateSnapshot(
        full_name=FieldSnapshot(value=doc.full_name.value, status=doc.full_name.status.name if hasattr(doc.full_name.status, 'name') else doc.full_name.status),
        home_address=FieldSnapshot(value=doc.home_address.value, status=doc.home_address.status.name if hasattr(doc.home_address.status, 'name') else doc.home_address.status),
        covers_worldwide_assets=FieldSnapshot(value=ww_val, status=ww.status.name if hasattr(ww.status, 'name') else ww.status),
        assets=FieldSnapshot(value=doc.assets.items if doc.assets.items else None, status=doc.assets.status.name if hasattr(doc.assets.status, 'name') else doc.assets.status),
        has_children=FieldSnapshot(value=doc.children.has_children, status=doc.children.status.name if hasattr(doc.children.status, 'name') else doc.children.status),
        children=FieldSnapshot(value=doc.children.names, status=doc.children.status.name if hasattr(doc.children.status, 'name') else doc.children.status),
        executor_name=FieldSnapshot(value=" and ".join(doc.executor.names) if doc.executor.names else None, status=doc.executor.status.name if hasattr(doc.executor.status, 'name') else doc.executor.status),
        executor_relationship=FieldSnapshot(value=doc.executor.relationship, status=doc.executor.status.name if hasattr(doc.executor.status, 'name') else doc.executor.status),
        specific_gifts=FieldSnapshot(value=[f"{g.item} -> {g.recipient}" for g in doc.specific_gifts.items] if doc.specific_gifts.items else [], status=doc.specific_gifts.status.name if hasattr(doc.specific_gifts.status, 'name') else doc.specific_gifts.status),
        additional_wishes=FieldSnapshot(value=doc.additional_wishes.text, status=doc.additional_wishes.status.name if hasattr(doc.additional_wishes.status, 'name') else doc.additional_wishes.status)
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
            state_before = session.state.model_copy(deep=True)
            session.state, merge_warnings = update_state(session.state, patch)
            warnings.extend(merge_warnings)
            
            print("========== STATE DEBUG ==========")
            print("SESSION ID:", session_id)
            print("USER MESSAGE:", user_message)
            print("STATE BEFORE:", state_before.model_dump_json(indent=2))
            print("CURRENT STEP BEFORE:", state_before.current_step)
            print("LLM EXTRACTION:", patch.model_dump_json(indent=2))
            print("STATE AFTER UPDATE:", session.state.model_dump_json(indent=2))

        # 3. State machine gets next step
        next_step = get_next_step(session.state)
        
        print("NEXT STEP:", next_step)
        print("DOCUMENT STATE:", session.state.document.model_dump_json(indent=2))
        print("================================")
        
        session.state.current_step = next_step
        
        # 4. Response Generator LLM #2
        if patch and patch.interpretation.status != "unclear" and not patch.interpretation.needs_clarification:
            extracted_dict = patch.updates.model_dump(exclude_unset=True)
        else:
            extracted_dict = {}
            
        if next_step == "complete":
            reply = "Your final Personal Wishes document has been successfully generated. Thank you!"
        else:
            reply = await generate_response(session.state, next_step, warnings, _build_recent_messages(session), extracted_dict, user_message)
        
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
    if hasattr(doc, field_name):
        field_obj = getattr(doc, field_name)
        field_obj.value = value
        
        # If it's a list, treat empty list as missing. Otherwise check if value is present.
        if isinstance(value, list):
            field_obj.status = "confirmed" if len(value) > 0 else "missing"
        elif isinstance(value, bool):
            field_obj.status = "confirmed" # Booleans are always confirmed if explicitly set
        else:
            field_obj.status = "confirmed" if value else "missing"
            
        if field_name == "has_children" and value is False:
            doc.children.value = []
            doc.children.status = "unknown"
            
    store.save(session)
    next_step = get_next_step(session.state)
    session.state.current_step = next_step
    
    return {
        "state": _state_to_snapshot(session.state),
        "document": generate_document(session.state.document),
        "missing_fields": [next_step] if next_step != "complete" else [],
        "warnings": []
    }

async def handle_batch_edit(session_id: str, updates: dict) -> dict:
    session = store.get(session_id)
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")
        
    doc = session.state.document
    
    for field_name, value in updates.items():
        if field_name == "full_name":
            doc.full_name.value = value.title() if isinstance(value, str) else value
            doc.full_name.status = "confirmed" if value else "missing"
            
        elif field_name == "home_address":
            doc.home_address.value = value
            doc.home_address.status = "confirmed" if value else "missing"
            
        elif field_name == "covers_worldwide_assets":
            # value is expected to be a boolean or a dict containing 'worldwide'
            is_worldwide = value if isinstance(value, bool) else (value.get("worldwide") if isinstance(value, dict) else None)
            if is_worldwide is not None:
                doc.covers_worldwide_assets.covers_worldwide = is_worldwide
                doc.covers_worldwide_assets.status = "confirmed"
                
        elif field_name == "has_children":
            if isinstance(value, bool):
                doc.children.has_children = value
                if value is False:
                    doc.children.names = []
                doc.children.status = "confirmed" if (value is False or len(doc.children.names) > 0) else "unconfirmed"
                
        elif field_name == "children":
            if isinstance(value, list):
                doc.children.names = [name.title() if isinstance(name, str) else name for name in value]
                if len(value) > 0:
                    doc.children.has_children = True
                    doc.children.status = "confirmed"
            elif isinstance(value, str):
                names = [s.strip().title() for s in value.split(",")] if value.strip() else []
                doc.children.names = names
                if len(names) > 0:
                    doc.children.has_children = True
                    doc.children.status = "confirmed"
                    
        elif field_name == "executor_name":
            names = [value.title()] if isinstance(value, str) and value else ([] if not value else [n.title() if isinstance(n, str) else n for n in value])
            if isinstance(names, list):
                doc.executor.names = names
                if len(names) > 0 and doc.executor.relationship:
                    doc.executor.status = "confirmed"
                
        elif field_name == "executor_relationship":
            doc.executor.relationship = value
            if value and len(doc.executor.names) > 0:
                doc.executor.status = "confirmed"
                
        elif field_name == "specific_gifts":
            # For simplicity, if it's a string, we just store it as a single unstructured item for now, 
            # or we could try to parse "item -> recipient". Since UI is simple textarea, we'll map to text.
            from app.models.document import SpecificGift
            if isinstance(value, str) and value.strip():
                doc.specific_gifts.items = [SpecificGift(item=value.strip(), recipient="Unknown (See Wishes)")]
                doc.specific_gifts.status = "confirmed"
            elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                doc.specific_gifts.items = [SpecificGift(item=v.strip(), recipient="Unknown") for v in value]
                doc.specific_gifts.status = "confirmed"
            elif not value:
                doc.specific_gifts.items = []
                doc.specific_gifts.status = "missing"
                
        elif field_name == "additional_wishes":
            doc.additional_wishes.text = value if isinstance(value, str) else None
            doc.additional_wishes.status = "confirmed" if value else "missing"
    next_step = get_next_step(session.state)
    session.state.current_step = next_step
    
    # Generate assistant response based on the new state
    if next_step == "complete":
        reply = "I see you've updated some fields. Your document is completely filled out and ready!"
    else:
        extracted_dict = {"_system_note": "User updated fields manually via UI. Proceed to the next step."}
        reply = await generate_response(
            session.state, 
            next_step, 
            [], 
            _build_recent_messages(session), 
            extracted_dict,
            "[User manually updated fields in the UI]"
        )
        
    from app.models.conversation import Message
    session.messages.append(Message(role="assistant", content=reply))
    
    store.save(session)
    
    return {
        "state": _state_to_snapshot(session.state),
        "document": generate_document(session.state.document),
        "missing_fields": [next_step] if next_step != "complete" else [],
        "warnings": []
    }
