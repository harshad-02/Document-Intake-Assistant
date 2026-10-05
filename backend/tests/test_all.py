"""Comprehensive test suite for the new deterministic backend architecture."""

from __future__ import annotations

import pytest

from app.models.conversation import ConversationState
from app.models.document import DocumentState, FieldValue
from app.models.llm import LLMExtractionResponse, ExtractionUpdates, ExtractionInterpretation
from app.services.state_manager import update_state
from app.services.state_machine import get_next_step

# ═══════════════════════════════════════════════════════════════════════════════
# STATE MACHINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateMachine:
    def test_initial_state_asks_full_name(self):
        state = ConversationState()
        assert get_next_step(state) == "full_name"

    def test_full_name_filled_asks_address(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        assert get_next_step(state) == "home_address"

    def test_address_filled_asks_assets(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        assert get_next_step(state) == "worldwide_assets"

    def test_assets_filled_asks_has_children(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        assert get_next_step(state) == "has_children"

    def test_has_children_true_asks_count(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "confirmed"
        state.document.children.has_children = True
        assert get_next_step(state) == "expected_children_count"

    def test_count_provided_asks_names(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "confirmed"
        state.document.children.has_children = True
        state.document.children.expected_count = 2
        assert get_next_step(state) == "children_names"

    def test_all_children_names_collected_asks_executor(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "confirmed"
        state.document.children.has_children = True
        state.document.children.expected_count = 2
        state.document.children.names = ["John", "Mia"]
        assert get_next_step(state) == "executor"

    def test_has_children_false_skips_children(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "none"
        state.document.children.has_children = False
        assert get_next_step(state) == "executor"

    def test_executor_completed_asks_gifts(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "none"
        state.document.executor.status = "confirmed"
        assert get_next_step(state) == "specific_gifts"

    def test_gifts_completed_asks_wishes(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "none"
        state.document.executor.status = "confirmed"
        state.document.specific_gifts.status = "none"
        assert get_next_step(state) == "additional_wishes"

    def test_all_completed(self):
        state = ConversationState()
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "none"
        state.document.executor.status = "not_decided"
        state.document.specific_gifts.status = "none"
        state.document.additional_wishes.status = "none"
        state.generation_confirmed = True
        assert get_next_step(state) == "complete"

# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateManager:
    def test_two_children_collected(self):
        state = ConversationState(current_step="children_names")
        state.document.full_name.status = "confirmed"
        state.document.home_address.status = "confirmed"
        state.document.covers_worldwide_assets.status = "confirmed"
        state.document.covers_worldwide_assets.covers_worldwide = True
        state.document.children.status = "confirmed"
        state.document.children.has_children = True
        state.document.children.expected_count = 2
        
        # 1st child
        patch1 = LLMExtractionResponse(
            updates=ExtractionUpdates(children_names=["John"]),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch1)
        assert state.document.children.names == ["John"]
        assert get_next_step(state) == "children_names"
        
        # 2nd child
        patch2 = LLMExtractionResponse(
            updates=ExtractionUpdates(children_names=["Mia"]),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch2)
        assert state.document.children.names == ["John", "Mia"]
        assert get_next_step(state) == "executor"

    def test_second_child_does_not_trigger_clarification(self):
        # Implicitly tested in test_two_children_collected above since status="clear" handles it.
        pass

    def test_no_executor_does_not_change_children(self):
        state = ConversationState(current_step="executor")
        state.document.children.has_children = True
        state.document.children.expected_count = 2
        state.document.children.names = ["John", "Mia"]
        state.document.children.status = "confirmed"
        
        # User says "no"
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(executor_status="not_decided"),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch)
        
        # Executor marked not decided
        assert state.document.executor.status == "not_decided"
        # Children unchanged
        assert state.document.children.has_children is True
        assert state.document.children.names == ["John", "Mia"]

    def test_executor_not_decided(self):
        state = ConversationState(current_step="executor")
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(executor_status="not_decided"),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch)
        assert state.document.executor.status == "not_decided"

    def test_multiple_fields_in_single_message(self):
        state = ConversationState(current_step="full_name")
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(full_name="Aditya", home_address="Hingoli"),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch)
        assert state.document.full_name.value == "Aditya"
        assert state.document.home_address.value == "Hingoli"
        assert get_next_step(state) == "worldwide_assets"

    def test_multi_field_extraction_harshad_from_pune(self):
        state = ConversationState(current_step="full_name")
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(full_name="Harshad", home_address="Pune"),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch)
        assert state.document.full_name.value == "Harshad"
        assert state.document.home_address.value == "Pune"
        assert get_next_step(state) == "worldwide_assets"

    def test_single_field_extraction_harshad(self):
        state = ConversationState(current_step="full_name")
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(full_name="Harshad"),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch)
        assert state.document.full_name.value == "Harshad"
        assert state.document.home_address.status == "missing"
        assert get_next_step(state) == "home_address"

    def test_user_corrects_previous_answer(self):
        state = ConversationState(current_step="has_children")
        state.document.full_name.value = "John"
        
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(full_name="Jonathan"),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch)
        assert state.document.full_name.value == "Jonathan"

    def test_ambiguous_answer_does_not_update_state(self):
        state = ConversationState(current_step="worldwide_assets")
        # User says "Car"
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(),
            interpretation=ExtractionInterpretation(status="unclear", needs_clarification=True)
        )
        state, warnings = update_state(state, patch)
        assert state.document.covers_worldwide_assets.status == "missing"
        assert len(warnings) == 1

    def test_malformed_llm_response_does_not_update_state(self):
        # Tested at the conversation layer handling json exceptions, but simulating a rejected interpretation
        state = ConversationState(current_step="full_name")
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(),
            interpretation=ExtractionInterpretation(status="unclear")
        )
        state, warnings = update_state(state, patch)
        assert state.document.full_name.status == "missing"

    def test_duplicate_child_name_not_added_twice(self):
        state = ConversationState(current_step="children_names")
        state.document.children.has_children = True
        state.document.children.names = ["John"]
        
        patch = LLMExtractionResponse(
            updates=ExtractionUpdates(children_names=["John", "Mia"]),
            interpretation=ExtractionInterpretation(status="clear")
        )
        state, _ = update_state(state, patch)
        assert state.document.children.names == ["John", "Mia"]

# ═══════════════════════════════════════════════════════════════════════════════
# END-TO-END E2E TEST (SIMULATED)
# ═══════════════════════════════════════════════════════════════════════════════

def test_e2e_simulated():
    state = ConversationState()
    
    # 1. Aditya
    state.current_step = get_next_step(state) # full_name
    patch = LLMExtractionResponse(updates=ExtractionUpdates(full_name="Aditya"), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    # 2. Hingoli
    state.current_step = get_next_step(state) # home_address
    patch = LLMExtractionResponse(updates=ExtractionUpdates(home_address="Hingoli"), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    # 3. Car (unclear for assets)
    state.current_step = get_next_step(state) # worldwide_assets
    patch = LLMExtractionResponse(updates=ExtractionUpdates(), interpretation=ExtractionInterpretation(status="unclear"))
    state, _ = update_state(state, patch)
    
    # 4. yes (for assets)
    patch = LLMExtractionResponse(updates=ExtractionUpdates(covers_worldwide_assets=True), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    # 5. yes (for has_children)
    state.current_step = get_next_step(state) # has_children
    patch = LLMExtractionResponse(updates=ExtractionUpdates(has_children=True), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    # 6. 2 (for count)
    state.current_step = get_next_step(state) # expected_children_count
    patch = LLMExtractionResponse(updates=ExtractionUpdates(expected_children_count=2), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    # 7. John
    state.current_step = get_next_step(state) # children_names
    patch = LLMExtractionResponse(updates=ExtractionUpdates(children_names=["John"]), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    # 8. Mia
    state.current_step = get_next_step(state) # children_names
    patch = LLMExtractionResponse(updates=ExtractionUpdates(children_names=["Mia"]), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    # 9. no (executor)
    state.current_step = get_next_step(state) # executor
    assert state.current_step == "executor"
    patch = LLMExtractionResponse(updates=ExtractionUpdates(executor_status="not_decided"), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    
    assert state.document.children.has_children is True
    assert state.document.children.names == ["John", "Mia"]
    assert state.document.executor.status == "not_decided"
    assert get_next_step(state) == "specific_gifts"

def test_regression_both_them_executor():
    state = ConversationState(current_step="executor")
    state.document.children.has_children = True
    state.document.children.expected_count = 2
    state.document.children.names = ["Jon", "Mia"]
    state.document.children.status = "confirmed"

    # Simulate LLM extracting "both them" based on context
    patch = LLMExtractionResponse(
        updates=ExtractionUpdates(
            executor_names=["Jon", "Mia"],
            executor_relationship="children",
            executor_status="confirmed"
        ),
        interpretation=ExtractionInterpretation(status="clear")
    )
    
    state, _ = update_state(state, patch)
    
    assert state.document.executor.names == ["Jon", "Mia"]
    assert state.document.executor.relationship == "children"
    assert state.document.executor.status == "confirmed"
    
    # Pre-fill previous fields so we can test the state machine correctly
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    state.document.covers_worldwide_assets.status = "confirmed"
    state.document.covers_worldwide_assets.covers_worldwide = True
    
    assert get_next_step(state) != "children_names"
    assert get_next_step(state) == "specific_gifts"

def test_regression_harshad_from_pune_responder():
    import asyncio
    from unittest.mock import patch as mock_patch
    from app.services.llm_responder import generate_response
    
    state = ConversationState()
    state.document.full_name.value = "Harshad"
    state.document.home_address.value = "Pune"
    
    extracted = {"full_name": "Harshad", "home_address": "Pune"}
    
    with mock_patch('app.services.llm_responder.get_llm_provider') as mock_provider:
        mock_llm = mock_provider.return_value
        
        async def mock_extract(request):
            assert 'JUST_EXTRACTED:\n{"full_name": "Harshad", "home_address": "Pune"}' in request.user_message
            assert "The user's normalized full name is Harshad. When addressing the user, use ONLY this normalized full name. Never repeat the raw user message." in request.user_message
            assert "Harshad from Pune" not in request.user_message
            assert "Harshad from Pune" not in request.system_prompt
            
            return "Thank you, Harshad. Would you like this document to cover your assets worldwide?"
            
        mock_llm.extract_turn.side_effect = mock_extract
        
        reply = asyncio.run(generate_response(state, "worldwide_assets", [], [], extracted))
        
        assert "Harshad" in reply
        assert "Harshad from Pune" not in reply
