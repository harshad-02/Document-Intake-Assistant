"""Conversation service: orchestrates LLM calls, state merging, and response building.

One public operation: handle_message(session_id, message).
Exactly one LLM call per user message, at most one repair call.
"""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from app.documents.generator import generate_document
from app.llm.interface import LLMError, LLMRequest
from app.llm.prompts import build_system_prompt, build_user_context
from app.llm.provider import get_llm_provider
from app.models.api import MessageResponse, StateSnapshot, FieldSnapshot
from app.models.llm_contract import LLMTurnResponse
from app.models.state import FieldStatus, Message, PersonalWishes, Session, StateField
from app.services.next_question import compute_next_question, get_template_question, FIELD_ORDER
from app.services.state_merge import merge_state
from app.store import store
from app.config import settings

logger = logging.getLogger(__name__)

# Fields that are boolean vs list vs text
_BOOLEAN_FIELDS = {"covers_worldwide_assets", "has_children"}
_LIST_FIELDS = {"children", "specific_gifts", "additional_wishes"}


class SessionNotFoundError(Exception):
    pass


def _state_to_snapshot(state: PersonalWishes) -> StateSnapshot:
    """Convert internal state to API snapshot."""
    data = {}
    for field_name in FIELD_ORDER:
        sf: StateField = getattr(state, field_name)
        data[field_name] = FieldSnapshot(value=sf.value, status=sf.status)
    return StateSnapshot(**data)


def _state_to_json(state: PersonalWishes) -> str:
    """Serialize state for the LLM prompt."""
    result = {}
    for field_name in FIELD_ORDER:
        sf: StateField = getattr(state, field_name)
        result[field_name] = {"value": sf.value, "status": sf.status.value}
    return json.dumps(result, indent=2)


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from LLM output."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _parse_llm_response(raw: str) -> LLMTurnResponse:
    """Parse and validate raw LLM output into LLMTurnResponse."""
    cleaned = _strip_fences(raw)
    data = json.loads(cleaned)
    return LLMTurnResponse.model_validate(data)


def _build_recent_messages(session: Session) -> list[dict[str, str]]:
    """Get the last MAX_HISTORY_MESSAGES messages for context."""
    max_msgs = settings.MAX_HISTORY_MESSAGES
    recent = session.messages[-max_msgs:] if len(session.messages) > max_msgs else session.messages
    return [{"role": m.role, "content": m.content} for m in recent]


async def handle_message(session_id: str, user_message: str) -> MessageResponse:
    """Process a user message: LLM call, state merge, response building.

    Steps:
    1. Load session
    2. Per-session lock
    3. Compute next_field
    4. Build LLM request
    5. Call LLM (catch errors)
    6. Parse and validate response
    7. Repair attempt if needed
    8. Run state_merge
    9. Recompute missing fields
    10. Build and return response
    """
    session = store.get(session_id)
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    lock = store.get_lock(session_id)
    async with lock:
        return await _process_message(session, user_message)


async def _process_message(session: Session, user_message: str) -> MessageResponse:
    """Core message processing (inside lock)."""
    warnings: list[str] = []

    # 3. Compute next_field
    nq = compute_next_question(session.state)

    # 4. Build LLM request
    llm = get_llm_provider()
    request = LLMRequest(
        system_prompt=build_system_prompt(),
        state_json=_state_to_json(session.state),
        recent_messages=_build_recent_messages(session),
        user_message=user_message,
        next_field=nq.next_field,
    )

    # 5. Call the LLM
    try:
        raw = await llm.extract_turn(request)
    except LLMError:
        raise  # Let the API layer handle it

    # 6. Parse the response
    llm_response = None
    parse_error = None
    try:
        llm_response = _parse_llm_response(raw)
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        parse_error = str(e)

    # 7. Repair attempt if parsing failed
    if llm_response is None and parse_error:
        try:
            repair_request = LLMRequest(
                system_prompt=build_system_prompt(),
                state_json=request.state_json,
                recent_messages=request.recent_messages,
                user_message=f"Your previous JSON was invalid: {parse_error}. Please respond with corrected JSON only.",
                next_field=request.next_field,
            )
            raw2 = await llm.extract_turn(repair_request)
            llm_response = _parse_llm_response(raw2)
            session.llm_call_count += 1
        except Exception:
            pass  # Repair failed — use fallback

    session.llm_call_count += 1

    # If still no valid response, fallback
    if llm_response is None:
        warnings.append("Could not parse LLM response. State unchanged.")
        reply = get_template_question(nq.next_field) if nq.next_field else "I'm having trouble processing that. Could you try rephrasing?"

        # Add messages to history
        session.messages.append(Message(role="user", content=user_message))
        session.messages.append(Message(role="assistant", content=reply))
        store.save(session)

        new_nq = compute_next_question(session.state)
        return MessageResponse(
            reply=reply,
            state=_state_to_snapshot(session.state),
            document=generate_document(session.state),
            missing_fields=new_nq.missing_fields,
            warnings=warnings,
        )

    # 8. Run state_merge
    result = merge_state(session.state, user_message, llm_response)
    session.state = result.new_state
    warnings.extend(result.warnings)

    # 9. Recompute missing fields
    new_nq = compute_next_question(session.state)

    # 10. Decide the reply
    reply = llm_response.reply

    # If the reply is empty or asks about a confirmed field, replace with template
    if not reply or not reply.strip():
        reply = get_template_question(new_nq.next_field) if new_nq.next_field else "Everything looks complete! Please review the document."

    # If all fields are complete, add review message
    if new_nq.review_time and "review" not in reply.lower() and "complete" not in reply.lower():
        reply += " All fields are now complete — please review the document and let me know if anything needs changing."

    # Add messages to history
    session.messages.append(Message(role="user", content=user_message))
    session.messages.append(Message(role="assistant", content=reply))
    store.save(session)

    return MessageResponse(
        reply=reply,
        state=_state_to_snapshot(session.state),
        document=generate_document(session.state),
        missing_fields=new_nq.missing_fields,
        warnings=warnings,
    )


def handle_direct_edit(session_id: str, field_name: str, value: Any) -> dict:
    """Handle a direct UI edit of a field. No LLM call.

    Returns updated state, document, missing fields, and warnings.
    """
    session = store.get(session_id)
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    warnings: list[str] = []

    # Validate field name
    if field_name not in FIELD_ORDER:
        raise ValueError(f"Unknown field: '{field_name}'")

    # Type validation
    if field_name in _BOOLEAN_FIELDS:
        if not isinstance(value, bool):
            raise ValueError(f"Field '{field_name}' requires a boolean value")
    elif field_name in _LIST_FIELDS:
        if not isinstance(value, list):
            raise ValueError(f"Field '{field_name}' requires a list value")
    else:
        if not isinstance(value, str) or not value.strip():
            # Allow clearing (setting to None)
            if value is None:
                sf = getattr(session.state, field_name)
                sf.value = None
                sf.status = FieldStatus.UNKNOWN
                store.save(session)
                nq = compute_next_question(session.state)
                return {
                    "state": _state_to_snapshot(session.state),
                    "document": generate_document(session.state),
                    "missing_fields": nq.missing_fields,
                    "warnings": warnings,
                }
            raise ValueError(f"Field '{field_name}' requires a non-empty text value")

    # Children while has_children is false
    if field_name == "children":
        hc = session.state.has_children
        if hc.status == FieldStatus.CONFIRMED and hc.value is False:
            raise ValueError("Cannot set children while has_children is false")

    # Apply the edit
    sf: StateField = getattr(session.state, field_name)

    if value is None:
        sf.value = None
        sf.status = FieldStatus.UNKNOWN
    else:
        sf.value = value
        sf.status = FieldStatus.CONFIRMED

    # has_children → false clears children
    if field_name == "has_children" and value is False:
        children_field = session.state.children
        if children_field.value is not None and children_field.status != FieldStatus.UNKNOWN:
            children_field.value = None
            children_field.status = FieldStatus.UNKNOWN
            warnings.append("Children cleared because has_children was set to false.")

    store.save(session)
    nq = compute_next_question(session.state)

    return {
        "state": _state_to_snapshot(session.state),
        "document": generate_document(session.state),
        "missing_fields": nq.missing_fields,
        "warnings": warnings,
    }
