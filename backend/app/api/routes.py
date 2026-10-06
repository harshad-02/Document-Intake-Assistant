"""API routes: translate HTTP to service calls. No business logic here."""

from __future__ import annotations

import logging
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.documents.generator import generate_document
from app.llm.interface import LLMError, LLMErrorType
from app.models.api import (
    EditFieldRequest,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    MessageInfo,
    MessageResponse,
    SendMessageRequest,
    SessionResponse,
)
from app.models.conversation import Message
from app.services.conversation import (
    SessionNotFoundError,
    handle_direct_edit,
    handle_batch_edit,
    handle_message,
    _state_to_snapshot,
)
from app.services.state_machine import get_next_step
from app.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    """Status, active provider, whether it is configured."""
    configured = True
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini":
        configured = settings.gemini_configured
    return HealthResponse(
        status="ok",
        provider=provider,
        configured=configured,
    )


# ── Sessions ──────────────────────────────────────────────────────────────────

OPENING_MESSAGE = (
    "Hello! I'm here to help you create a Personal Wishes Document. "
    "This is a fictional sample and not legal advice. "
    "Let's start — could you please tell me your full legal name?"
)


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session():
    """Create a new session."""
    session = store.create()
    # Add the opening message
    session.messages.append(Message(role="assistant", content=OPENING_MESSAGE))
    store.save(session)

    next_step = get_next_step(session.state)
    session.state.current_step = next_step
    
    return SessionResponse(
        id=session.id,
        state=_state_to_snapshot(session.state),
        document=generate_document(session.state.document),
        missing_fields=[next_step] if next_step != "complete" else [],
        messages=[MessageInfo(role="assistant", content=OPENING_MESSAGE)],
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Full snapshot of a session."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="SESSION_NOT_FOUND", message=f"Session '{session_id}' not found")
            ).model_dump(),
        )

    next_step = get_next_step(session.state)
    return SessionResponse(
        id=session.id,
        state=_state_to_snapshot(session.state),
        document=generate_document(session.state.document),
        missing_fields=[next_step] if next_step != "complete" else [],
        messages=[MessageInfo(role=m.role, content=m.content) for m in session.messages],
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(session_id: str, body: SendMessageRequest):
    """Send a user message and get the assistant's reply."""
    try:
        result = await handle_message(session_id, body.message)
        return result
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="SESSION_NOT_FOUND", message=f"Session '{session_id}' not found")
            ).model_dump(),
        )
    except LLMError as e:
        status_map = {
            LLMErrorType.RATE_LIMITED: 429,
            LLMErrorType.AUTH_ERROR: 503,
            LLMErrorType.NOT_CONFIGURED: 503,
            LLMErrorType.TIMEOUT: 503,
            LLMErrorType.SERVER_ERROR: 503,
            LLMErrorType.BAD_OUTPUT: 502,
            LLMErrorType.OTHER: 503,
        }
        raise HTTPException(
            status_code=status_map.get(e.error_type, 503),
            detail=ErrorResponse(
                error=ErrorDetail(code=e.error_type.value, message=e.message)
            ).model_dump(),
        )


@router.patch("/sessions/{session_id}/state")
async def edit_field(session_id: str, body: EditFieldRequest):
    """Direct UI edit of a field. No LLM call."""
    try:
        result = handle_direct_edit(session_id, body.field, body.value)
        return result
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="SESSION_NOT_FOUND", message=f"Session '{session_id}' not found")
            ).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error=ErrorDetail(code="VALIDATION_ERROR", message=str(e))
            ).model_dump(),
        )

from typing import Dict, Any

class BatchEditRequest(BaseModel):
    updates: Dict[str, Any]

@router.patch("/sessions/{session_id}/state/batch")
async def batch_edit_fields(session_id: str, body: BatchEditRequest):
    """Batch edit multiple fields via the UI."""
    try:
        result = await handle_batch_edit(session_id, body.updates)
        return result
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="SESSION_NOT_FOUND", message=f"Session '{session_id}' not found")
            ).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error=ErrorDetail(code="VALIDATION_ERROR", message=str(e))
            ).model_dump(),
        )



@router.post("/sessions/{session_id}/reset", response_model=SessionResponse)
async def reset_session(session_id: str):
    """Reset a session (start over)."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="SESSION_NOT_FOUND", message=f"Session '{session_id}' not found")
            ).model_dump(),
        )

    from app.models.conversation import ConversationState
    session.state = ConversationState()
    session.messages = [Message(role="assistant", content=OPENING_MESSAGE)]
    session.llm_call_count = 0
    store.save(session)

    next_step = get_next_step(session.state)
    return SessionResponse(
        id=session.id,
        state=_state_to_snapshot(session.state),
        document=generate_document(session.state.document),
        missing_fields=[next_step] if next_step != "complete" else [],
        messages=[MessageInfo(role="assistant", content=OPENING_MESSAGE)],
    )
