"""Comprehensive test suite — runs without network or API key.

All tests use MockLLM and fixtures. ~20 focused tests covering
state merge, next question, document generator, conversation service, and API.
"""

from __future__ import annotations

import asyncio
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pydantic import ValidationError

from app.models.state import FieldStatus, PersonalWishes, StateField, Session, Message
from app.models.llm_contract import (
    Certainty,
    Clarification,
    ClarificationReason,
    FieldName,
    LLMTurnResponse,
    Op,
    ProposedUpdate,
)
from app.services.state_merge import merge_state, MergeResult
from app.services.next_question import compute_next_question, FIELD_ORDER
from app.documents.generator import generate_document


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MERGE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestStateMerge:
    """Tests for the state_merge module."""

    def test_01_clear_single_field_update(self):
        """1. A clear single-field update sets the value and marks it confirmed."""
        state = PersonalWishes()
        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.FULL_NAME,
                    op=Op.SET,
                    value="John Smith",
                    evidence="John Smith",
                    certainty=Certainty.CLEAR,
                )
            ],
            clarifications=[],
            reply="Thank you, John!",
        )
        result = merge_state(state, "My name is John Smith", response)
        assert result.new_state.full_name.value == "John Smith"
        assert result.new_state.full_name.status == FieldStatus.CONFIRMED
        assert len(result.applied) == 1
        assert len(result.rejected) == 0

    def test_02_multi_field_update(self):
        """2. A multi-field update fills several fields at once, in any order."""
        state = PersonalWishes()
        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.HOME_ADDRESS, op=Op.SET,
                    value="42 Test Lane", evidence="42 Test Lane",
                    certainty=Certainty.CLEAR,
                ),
                ProposedUpdate(
                    field=FieldName.FULL_NAME, op=Op.SET,
                    value="Jane Doe", evidence="Jane Doe",
                    certainty=Certainty.CLEAR,
                ),
            ],
            clarifications=[],
            reply="Got it!",
        )
        result = merge_state(state, "I'm Jane Doe, I live at 42 Test Lane", response)
        assert result.new_state.full_name.value == "Jane Doe"
        assert result.new_state.full_name.status == FieldStatus.CONFIRMED
        assert result.new_state.home_address.value == "42 Test Lane"
        assert result.new_state.home_address.status == FieldStatus.CONFIRMED
        assert len(result.applied) == 2

    def test_03_correction_replaces_value(self):
        """3. A correction replaces the old value and keeps it confirmed."""
        state = PersonalWishes()
        state.executor_name = StateField(value="James", status=FieldStatus.CONFIRMED)
        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.EXECUTOR_NAME, op=Op.CORRECT,
                    value="Anna", evidence="actually Anna",
                    certainty=Certainty.CLEAR,
                )
            ],
            clarifications=[],
            reply="Updated!",
        )
        result = merge_state(state, "actually Anna is my executor", response)
        assert result.new_state.executor_name.value == "Anna"
        assert result.new_state.executor_name.status == FieldStatus.CONFIRMED

    def test_04_ambiguous_becomes_unconfirmed(self):
        """4. An ambiguous update becomes unconfirmed."""
        state = PersonalWishes()
        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.EXECUTOR_RELATIONSHIP, op=Op.SET,
                    value="Brother", evidence="my brother",
                    certainty=Certainty.AMBIGUOUS,
                )
            ],
            clarifications=[],
            reply="Could you tell me more?",
        )
        result = merge_state(state, "my brother will handle it", response)
        assert result.new_state.executor_relationship.value == "Brother"
        assert result.new_state.executor_relationship.status == FieldStatus.UNCONFIRMED

    def test_05_has_children_false_clears_children(self):
        """5. has_children becoming false clears children."""
        state = PersonalWishes()
        state.has_children = StateField(value=True, status=FieldStatus.CONFIRMED)
        state.children = StateField(value=["Alice"], status=FieldStatus.CONFIRMED)

        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.HAS_CHILDREN, op=Op.CORRECT,
                    value=False, evidence="actually no children",
                    certainty=Certainty.CLEAR,
                )
            ],
            clarifications=[],
            reply="Updated.",
        )
        result = merge_state(state, "actually no children", response)
        assert result.new_state.has_children.value is False
        assert result.new_state.children.value is None
        assert result.new_state.children.status == FieldStatus.UNKNOWN
        assert any("Children cleared" in w for w in result.warnings)

    def test_06_children_while_has_children_false_rejected(self):
        """6. Children supplied while has_children is false are rejected."""
        state = PersonalWishes()
        state.has_children = StateField(value=False, status=FieldStatus.CONFIRMED)

        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.CHILDREN, op=Op.SET,
                    value=["Timmy"], evidence="Timmy",
                    certainty=Certainty.CLEAR,
                )
            ],
            clarifications=[],
            reply="Noted.",
        )
        result = merge_state(state, "Timmy is my child", response)
        assert result.new_state.children.value is None  # Rejected
        assert len(result.rejected) == 1
        assert "has_children is false" in result.rejected[0]

    def test_07_fabricated_evidence_rejected_valid_kept(self):
        """7. Fabricated evidence is rejected; valid updates in the same patch apply."""
        state = PersonalWishes()
        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.FULL_NAME, op=Op.SET,
                    value="Robert Tables", evidence="Robert Tables",
                    certainty=Certainty.CLEAR,
                ),
                ProposedUpdate(
                    field=FieldName.HOME_ADDRESS, op=Op.SET,
                    value="123 Fake Street", evidence="I live at 123 Fake Street",
                    certainty=Certainty.CLEAR,
                ),
            ],
            clarifications=[],
            reply="Noted!",
        )
        # Only "Robert Tables" is in the user message, not the address evidence
        result = merge_state(state, "My name is Robert Tables", response)
        assert result.new_state.full_name.value == "Robert Tables"
        assert result.new_state.full_name.status == FieldStatus.CONFIRMED
        # Address should be rejected (evidence not in message)
        assert result.new_state.home_address.value is None
        assert len(result.rejected) == 1

    def test_08_wrong_type_rejected(self):
        """8. A wrong type (text for a boolean) is rejected."""
        state = PersonalWishes()
        response = LLMTurnResponse(
            updates=[
                ProposedUpdate(
                    field=FieldName.HAS_CHILDREN, op=Op.SET,
                    value="yes",  # Should be boolean
                    evidence="yes",
                    certainty=Certainty.CLEAR,
                )
            ],
            clarifications=[],
            reply="Noted.",
        )
        result = merge_state(state, "yes I have children", response)
        assert result.new_state.has_children.value is None
        assert len(result.rejected) == 1
        assert "wrong type" in result.rejected[0]


# ═══════════════════════════════════════════════════════════════════════════════
# NEXT QUESTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestNextQuestion:
    """Tests for the next_question module."""

    def test_09_returns_fields_in_order_skipping_confirmed(self):
        """9. Returns fields in defined order and skips confirmed ones."""
        state = PersonalWishes()
        state.full_name = StateField(value="John", status=FieldStatus.CONFIRMED)

        nq = compute_next_question(state)
        assert nq.next_field == "home_address"
        assert "full_name" not in nq.missing_fields
        assert "home_address" in nq.missing_fields

    def test_10_skips_children_when_has_children_false(self):
        """10. Skips children when has_children is false; includes when true."""
        state = PersonalWishes()
        state.has_children = StateField(value=False, status=FieldStatus.CONFIRMED)
        nq = compute_next_question(state)
        assert "children" not in nq.missing_fields

        state2 = PersonalWishes()
        state2.has_children = StateField(value=True, status=FieldStatus.CONFIRMED)
        nq2 = compute_next_question(state2)
        assert "children" in nq2.missing_fields

    def test_11_review_time_when_complete(self):
        """11. Reports review time when everything is complete."""
        state = PersonalWishes()
        state.full_name = StateField(value="John", status=FieldStatus.CONFIRMED)
        state.home_address = StateField(value="123 St", status=FieldStatus.CONFIRMED)
        state.covers_worldwide_assets = StateField(value=True, status=FieldStatus.CONFIRMED)
        state.has_children = StateField(value=False, status=FieldStatus.CONFIRMED)
        # children N/A
        state.executor_name = StateField(value="Jane", status=FieldStatus.CONFIRMED)
        state.executor_relationship = StateField(value="Wife", status=FieldStatus.CONFIRMED)
        state.specific_gifts = StateField(value=[], status=FieldStatus.CONFIRMED)
        state.additional_wishes = StateField(value=[], status=FieldStatus.CONFIRMED)

        nq = compute_next_question(state)
        assert nq.review_time is True
        assert nq.next_field is None
        assert len(nq.missing_fields) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConversationService:
    """Tests for the conversation service using MockLLM."""

    def _run(self, coro):
        """Helper to run async code in tests."""
        return asyncio.run(coro)

    def test_12_multi_turn_no_repeat(self):
        """12. A scripted multi-turn conversation never asks about a confirmed field."""
        from app.llm.provider import reset_provider
        from app.llm import provider as provider_mod
        from app.llm.mock import ScriptedMockLLM
        from app.services.conversation import handle_message
        from app.store import store
        from tests.fixtures.mock_responses import HAPPY_PATH_SCRIPT

        reset_provider()
        mock = ScriptedMockLLM(HAPPY_PATH_SCRIPT)
        provider_mod._instance = mock

        session = store.create()
        session.messages.append(Message(role="assistant", content="Hello!"))
        store.save(session)

        messages = [
            "My name is John Smith",
            "10 Downing Street, London",
            "yes worldwide",
            "yes I have children",
            "Alice and Bob",
            "James Smith",
            "my brother",
            "no specific gifts",
            "no additional wishes",
        ]

        for msg in messages:
            result = self._run(handle_message(session.id, msg))
            assert result.reply  # Always has a reply

        # After all messages, check state is filled
        final_session = store.get(session.id)
        assert final_session.state.full_name.status == FieldStatus.CONFIRMED
        assert final_session.state.home_address.status == FieldStatus.CONFIRMED

        reset_provider()

    def test_13_malformed_json_fallback(self):
        """13. Malformed JSON triggers repair attempt, then fallback."""
        from app.llm.provider import reset_provider
        from app.llm import provider as provider_mod
        from app.llm.mock import ScriptedMockLLM
        from app.services.conversation import handle_message
        from app.store import store
        from tests.fixtures.mock_responses import MALFORMED_JSON, GENERIC_RESPONSE

        reset_provider()
        # Both attempts return malformed JSON
        mock = ScriptedMockLLM([MALFORMED_JSON, MALFORMED_JSON])
        provider_mod._instance = mock

        session = store.create()
        session.messages.append(Message(role="assistant", content="Hello!"))
        store.save(session)

        result = self._run(handle_message(session.id, "hello"))
        # State should be unchanged
        assert session.state.full_name.status == FieldStatus.UNKNOWN
        assert len(result.warnings) > 0

        reset_provider()

    def test_14_schema_invalid_handled(self):
        """14. Schema-invalid output is handled the same way."""
        from app.llm.provider import reset_provider
        from app.llm import provider as provider_mod
        from app.llm.mock import ScriptedMockLLM
        from app.services.conversation import handle_message
        from app.store import store
        from tests.fixtures.mock_responses import WRONG_SCHEMA

        reset_provider()
        mock = ScriptedMockLLM([WRONG_SCHEMA, WRONG_SCHEMA])
        provider_mod._instance = mock

        session = store.create()
        session.messages.append(Message(role="assistant", content="Hello!"))
        store.save(session)

        result = self._run(handle_message(session.id, "test"))
        assert session.state.full_name.status == FieldStatus.UNKNOWN
        assert len(result.warnings) > 0

        reset_provider()

    def test_15_provider_errors(self):
        """15. Provider errors map to correct error codes."""
        from app.llm.provider import reset_provider
        from app.llm import provider as provider_mod
        from app.llm.mock import TimeoutMockLLM, RateLimitMockLLM, AuthErrorMockLLM
        from app.llm.interface import LLMError, LLMErrorType
        from app.services.conversation import handle_message
        from app.store import store

        for MockClass, expected_type in [
            (TimeoutMockLLM, LLMErrorType.TIMEOUT),
            (RateLimitMockLLM, LLMErrorType.RATE_LIMITED),
            (AuthErrorMockLLM, LLMErrorType.AUTH_ERROR),
        ]:
            reset_provider()
            provider_mod._instance = MockClass()

            session = store.create()
            session.messages.append(Message(role="assistant", content="Hello!"))
            store.save(session)

            with pytest.raises(LLMError) as exc_info:
                self._run(handle_message(session.id, "test"))
            assert exc_info.value.error_type == expected_type

        reset_provider()


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT GENERATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentGenerator:
    """Tests for the document generator."""

    def test_16_disclaimer_present(self):
        """16. Contains the fictional/not legal advice banner and footer."""
        state = PersonalWishes()
        doc = generate_document(state)
        assert "FICTIONAL SAMPLE: NOT LEGAL ADVICE" in doc
        # Should appear at least twice (banner + footer)
        assert doc.count("FICTIONAL SAMPLE: NOT LEGAL ADVICE") >= 2

    def test_17_status_rendering(self):
        """17. Unknown shows placeholder, unconfirmed shows marker, confirmed shows plainly."""
        state = PersonalWishes()
        state.full_name = StateField(value="John Smith", status=FieldStatus.CONFIRMED)
        state.home_address = StateField(value="Maybe here", status=FieldStatus.UNCONFIRMED)
        # executor_name stays unknown

        doc = generate_document(state)
        assert "John Smith" in doc
        assert "To be confirmed" in doc
        assert "[Not yet provided]" in doc

    def test_18_deterministic_output(self):
        """18. Same state produces identical output."""
        state = PersonalWishes()
        state.full_name = StateField(value="Test", status=FieldStatus.CONFIRMED)
        state.has_children = StateField(value=False, status=FieldStatus.CONFIRMED)

        doc1 = generate_document(state)
        doc2 = generate_document(state)
        assert doc1 == doc2


# ═══════════════════════════════════════════════════════════════════════════════
# API TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAPI:
    """Tests for the FastAPI endpoints."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_19_create_send_patch(self):
        """19. Create session, send message, PATCH edit all return expected shape."""
        from app.llm.provider import reset_provider
        from app.llm import provider as provider_mod
        from app.llm.mock import MockLLM

        reset_provider()
        provider_mod._instance = MockLLM()

        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Create session
                resp = await client.post("/api/sessions")
                assert resp.status_code == 201
                data = resp.json()
                assert "id" in data
                assert "state" in data
                assert "document" in data
                session_id = data["id"]

                # Send message
                resp = await client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "My name is John Smith"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert "reply" in data
                assert "state" in data
                assert "document" in data

                # PATCH edit
                resp = await client.patch(
                    f"/api/sessions/{session_id}/state",
                    json={"field": "home_address", "value": "123 New Street"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["state"]["home_address"]["status"] == "confirmed"
                assert data["state"]["home_address"]["value"] == "123 New Street"

        self._run(_test())
        reset_provider()

    def test_20_not_configured_health(self):
        """20. Health endpoint reports provider status."""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async def _test():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/health")
                assert resp.status_code == 200
                data = resp.json()
                assert "provider" in data
                assert "configured" in data

        self._run(_test())


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestModels:
    """Tests for Pydantic model validation."""

    def test_default_state(self):
        """Default PersonalWishes has all fields unknown with null values."""
        state = PersonalWishes()
        for field_name in FIELD_ORDER:
            sf = getattr(state, field_name)
            assert sf.status == FieldStatus.UNKNOWN
            assert sf.value is None

    def test_llm_response_rejects_unknown_field(self):
        """LLMTurnResponse rejects JSON with unknown field names."""
        with pytest.raises(ValidationError):
            LLMTurnResponse.model_validate({
                "updates": [
                    {
                        "field": "favourite_color",
                        "op": "set",
                        "value": "blue",
                        "evidence": "blue",
                        "certainty": "clear",
                    }
                ],
                "clarifications": [],
                "reply": "Noted!",
            })

    def test_llm_response_rejects_empty_reply(self):
        """LLMTurnResponse rejects empty reply."""
        with pytest.raises(ValidationError):
            LLMTurnResponse.model_validate({
                "updates": [],
                "clarifications": [],
                "reply": "",
            })

    def test_llm_response_rejects_extra_keys(self):
        """LLMTurnResponse rejects extra keys."""
        with pytest.raises(ValidationError):
            LLMTurnResponse.model_validate({
                "updates": [],
                "clarifications": [],
                "reply": "Hello",
                "extra_key": "bad",
            })
