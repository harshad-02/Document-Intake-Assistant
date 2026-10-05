from app.models.conversation import ConversationState
from app.models.llm import LLMExtractionResponse, ExtractionUpdates, ExtractionInterpretation, SpecificGiftExtraction
from app.services.state_manager import update_state
from app.services.state_machine import get_next_step
import pytest

def test_regression_address_correction():
    state = ConversationState()
    state.document.home_address.value = "Pune"
    state.document.home_address.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="correction",
        updates=ExtractionUpdates(home_address="Mumbai"),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    
    assert state.document.home_address.value == "Mumbai"
    assert state.document.home_address.status == "confirmed"

def test_regression_child_correction():
    state = ConversationState()
    state.document.children.has_children = True
    state.document.children.names = ["Mia", "Jonn"]
    state.document.children.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="correction",
        updates=ExtractionUpdates(children_names=["Mia", "John"]),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    
    assert state.document.children.names == ["Mia", "John"]

def test_regression_executor_correction():
    state = ConversationState()
    state.document.executor.names = ["Mia", "Jonn"]
    state.document.executor.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="correction",
        updates=ExtractionUpdates(executor_names=["Mia"]),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    
    assert state.document.executor.names == ["Mia"]

def test_regression_gift_removal():
    from app.models.document import SpecificGift
    state = ConversationState()
    state.document.specific_gifts.items = [SpecificGift(item="1 car", recipient="Jonn")]
    state.document.specific_gifts.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="removal",
        updates=ExtractionUpdates(specific_gifts=[]),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    
    assert state.document.specific_gifts.items == []
    assert state.document.specific_gifts.status == "none"

def test_regression_additional_wish_correction():
    state = ConversationState()
    state.document.additional_wishes.text = "I want to give both of them 1 billion"
    state.document.additional_wishes.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="correction",
        updates=ExtractionUpdates(additional_wishes="I want to give both of them 500 million"),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    
    assert state.document.additional_wishes.text == "I want to give both of them 500 million"

def test_regression_specific_gifts_structured():
    state = ConversationState()
    
    patch = LLMExtractionResponse(
        intent="answer",
        updates=ExtractionUpdates(
            specific_gifts=[
                SpecificGiftExtraction(item="1 car", recipient="Jonn"),
                SpecificGiftExtraction(item="1 house", recipient="Mia")
            ]
        ),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    
    assert len(state.document.specific_gifts.items) == 2
    assert state.document.specific_gifts.items[0].item == "1 car"
    assert state.document.specific_gifts.items[0].recipient == "Jonn"
    assert state.document.specific_gifts.items[1].item == "1 house"
    assert state.document.specific_gifts.items[1].recipient == "Mia"

def test_regression_final_generation_flow():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    state.document.covers_worldwide_assets.status = "confirmed"
    state.document.covers_worldwide_assets.covers_worldwide = True
    state.document.children.status = "none"
    state.document.executor.status = "none"
    state.document.specific_gifts.status = "none"
    state.document.additional_wishes.status = "none"
    
    assert get_next_step(state) == "generation_confirmation"
    
    patch = LLMExtractionResponse(
        intent="generation_confirmation",
        updates=ExtractionUpdates(),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    
    assert state.generation_confirmed is True
    assert get_next_step(state) == "complete"

def test_regression_worldwide_assets_yes():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    state.current_step = get_next_step(state)
    assert state.current_step == "worldwide_assets"

    patch = LLMExtractionResponse(
        intent="answer",
        updates=ExtractionUpdates(covers_worldwide_assets=True),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)

    assert state.document.covers_worldwide_assets.covers_worldwide is True
    assert get_next_step(state) == "has_children"

def test_regression_worldwide_assets_no():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"

    patch = LLMExtractionResponse(
        intent="answer",
        updates=ExtractionUpdates(covers_worldwide_assets=False),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)

    assert state.document.covers_worldwide_assets.covers_worldwide is False
    assert get_next_step(state) == "specific_assets"

def test_regression_worldwide_assets_region():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"

    patch = LLMExtractionResponse(
        intent="answer",
        updates=ExtractionUpdates(covers_worldwide_assets=False, asset_region="India"),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)

    assert state.document.covers_worldwide_assets.covers_worldwide is False
    assert state.document.covers_worldwide_assets.region == "India"
    assert get_next_step(state) == "has_children"

def test_regression_generator_worldwide():
    from app.documents.generator import generate_document
    state = ConversationState()
    state.document.covers_worldwide_assets.covers_worldwide = True
    state.document.covers_worldwide_assets.status = "confirmed"
    
    doc = generate_document(state.document)
    assert "Worldwide assets (properties, bank accounts, investments, etc.)" in doc
    assert "Specific region:" not in doc

def test_regression_generator_specific():
    from app.documents.generator import generate_document
    state = ConversationState()
    state.document.covers_worldwide_assets.covers_worldwide = False
    state.document.covers_worldwide_assets.region = "India"
    state.document.covers_worldwide_assets.status = "confirmed"
    
    doc = generate_document(state.document)
    assert "Specific assets only: India" in doc
    assert "Worldwide assets" not in doc

def test_regression_generator_specific_multiple():
    from app.documents.generator import generate_document
    state = ConversationState()
    state.document.covers_worldwide_assets.covers_worldwide = False
    state.document.covers_worldwide_assets.region = "India and UAE"
    state.document.covers_worldwide_assets.status = "confirmed"
    
    doc = generate_document(state.document)
    assert "Specific assets only: India and UAE" in doc
    assert "Worldwide assets" not in doc

def test_regression_generator_combined_assets():
    from app.documents.generator import generate_document
    state = ConversationState()
    state.document.covers_worldwide_assets.covers_worldwide = False
    state.document.covers_worldwide_assets.region = "India"
    state.document.covers_worldwide_assets.status = "confirmed"
    state.document.assets.items = ["1 car", "2 houses"]
    state.document.assets.status = "confirmed"
    
    doc = generate_document(state.document)
    assert "Specific assets only: India; 1 car, 2 houses" in doc
    
    # And if only assets, no region
    state.document.covers_worldwide_assets.region = None
    doc = generate_document(state.document)
    assert "Specific assets only: 1 car, 2 houses" in doc

def test_regression_semantic_no_assets():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    state.document.covers_worldwide_assets.status = "confirmed"
    state.document.covers_worldwide_assets.covers_worldwide = True
    assert get_next_step(state) == "has_children"

    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["assets"],
        updates=ExtractionUpdates(has_children=False), # Simulating bad LLM hallucination for test
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)

    assert state.document.children.has_children is None
    assert state.document.children.status == "missing"
    assert get_next_step(state) == "has_children"

def test_regression_semantic_no_children():
    state = ConversationState()
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["children"],
        updates=ExtractionUpdates(has_children=False),
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)
    assert state.document.children.has_children is False

def test_regression_semantic_no_car():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    state.document.covers_worldwide_assets.status = "confirmed"
    state.document.covers_worldwide_assets.covers_worldwide = True

    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["assets"],
        updates=ExtractionUpdates(has_children=False), # Simulated bad output
        interpretation=ExtractionInterpretation(status="clear")
    )
    state, _ = update_state(state, patch)

    assert state.document.children.has_children is None
    assert get_next_step(state) == "has_children"

def test_regression_semantic_mixed_answer():
    state = ConversationState()

    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["assets", "children"],
        updates=ExtractionUpdates(
            asset_items=[],
            has_children=True,
            expected_children_count=2,
            children_names=["Mia", "Jonn"]
        ),
        interpretation=ExtractionInterpretation(status="clear")
    )
    # mock the "none" logic for empty asset array via update_state intent=removal is required for full overwrite, but wait...
    # actually the test only asked to check children fields!
    state, _ = update_state(state, patch)

    assert state.document.children.has_children is True
    assert state.document.children.expected_count == 2
    assert state.document.children.names == ["Mia", "Jonn"]

def test_regression_semantic_short_answers():
    state = ConversationState()
    patch = LLMExtractionResponse(intent="answer", target_fields=["children"], updates=ExtractionUpdates(has_children=True, expected_children_count=2), interpretation=ExtractionInterpretation())
    state, _ = update_state(state, patch)
    assert state.document.children.has_children is True
    assert state.document.children.expected_count == 2

def test_regression_multi_field_worldwide_no_items():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["covers_worldwide_assets", "assets"],
        updates=ExtractionUpdates(covers_worldwide_assets=False, asset_items=["one car", "one house"]),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.covers_worldwide_assets.covers_worldwide is False
    assert state.document.assets.items == ["one car", "one house"]
    assert get_next_step(state) == "has_children"

def test_regression_multi_field_worldwide_no_only():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["covers_worldwide_assets"],
        updates=ExtractionUpdates(covers_worldwide_assets=False),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.covers_worldwide_assets.covers_worldwide is False
    assert not state.document.assets.items
    assert not state.document.covers_worldwide_assets.region
    assert get_next_step(state) == "specific_assets"

def test_regression_multi_field_worldwide_no_car():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["covers_worldwide_assets", "assets"],
        updates=ExtractionUpdates(covers_worldwide_assets=False, asset_items=["car"]),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.covers_worldwide_assets.covers_worldwide is False
    assert state.document.assets.items == ["car"]
    assert get_next_step(state) == "has_children"

def test_regression_multi_field_worldwide_yes():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["covers_worldwide_assets"],
        updates=ExtractionUpdates(covers_worldwide_assets=True),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.covers_worldwide_assets.covers_worldwide is True
    assert not state.document.assets.items
    assert get_next_step(state) == "has_children"

def test_regression_multi_field_worldwide_no_india():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["covers_worldwide_assets"],
        updates=ExtractionUpdates(covers_worldwide_assets=False, asset_region="India"),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.covers_worldwide_assets.covers_worldwide is False
    assert state.document.covers_worldwide_assets.region == "India"
    assert get_next_step(state) == "has_children"

def test_regression_multi_field_worldwide_no_car_india():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["covers_worldwide_assets", "assets"],
        updates=ExtractionUpdates(covers_worldwide_assets=False, asset_region="India", asset_items=["car", "two houses"]),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.covers_worldwide_assets.covers_worldwide is False
    assert state.document.covers_worldwide_assets.region == "India"
    assert state.document.assets.items == ["car", "two houses"]
    assert get_next_step(state) == "has_children"

def test_regression_executor_contextual_relationship():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    state.document.covers_worldwide_assets.covers_worldwide = True
    state.document.covers_worldwide_assets.status = "confirmed"
    state.document.children.has_children = True
    state.document.children.expected_count = 2
    state.document.children.names = ["Jonn", "Mia"]
    state.document.children.status = "confirmed"
    
    state.current_step = "executor"
    
    # "both of them" -> LLM extracts names but not relationship
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["executor"],
        updates=ExtractionUpdates(executor_names=["Jonn", "Mia"]),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.executor.names == ["Jonn", "Mia"]
    assert state.document.executor.relationship == "children"
    assert state.document.executor.status == "confirmed"
    
    assert get_next_step(state) == "specific_gifts"

def test_regression_executor_contextual_single_child():
    state = ConversationState()
    state.document.children.has_children = True
    state.document.children.names = ["Jonn", "Mia"]
    state.document.children.status = "confirmed"
    
    state.current_step = "executor"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["executor"],
        updates=ExtractionUpdates(executor_names=["Mia"]),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.executor.names == ["Mia"]
    assert state.document.executor.relationship == "child"
    
    assert state.document.children.names == ["Jonn", "Mia"] # Unchanged

def test_regression_executor_brother():
    state = ConversationState()
    state.current_step = "executor"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["executor"],
        updates=ExtractionUpdates(executor_names=["Rahul"], executor_relationship="brother"),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.executor.names == ["Rahul"]
    assert state.document.executor.relationship == "brother"

def test_regression_executor_unknown_relationship():
    state = ConversationState()
    state.document.full_name.status = "confirmed"
    state.document.home_address.status = "confirmed"
    state.document.covers_worldwide_assets.covers_worldwide = True
    state.document.covers_worldwide_assets.status = "confirmed"
    state.document.children.has_children = True
    state.document.children.expected_count = 2
    state.document.children.names = ["Jonn", "Mia"]
    state.document.children.status = "confirmed"
    
    state.current_step = "executor"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["executor"],
        updates=ExtractionUpdates(executor_names=["Rahul"]),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.executor.names == ["Rahul"]
    assert state.document.executor.relationship is None
    assert get_next_step(state) == "executor_relationship"

def test_regression_additional_wishes_text():
    state = ConversationState()
    state.current_step = "additional_wishes"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["additional_wishes"],
        updates=ExtractionUpdates(additional_wishes="to play golf"),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.additional_wishes.text == "to play golf"
    assert state.document.additional_wishes.status == "confirmed"

def test_regression_additional_wishes_none():
    state = ConversationState()
    state.current_step = "additional_wishes"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["additional_wishes"],
        updates=ExtractionUpdates(additional_wishes=None),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.additional_wishes.text is None
    assert state.document.additional_wishes.status == "none"

def test_regression_has_children_yes():
    state = ConversationState()
    state.current_step = "has_children"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["has_children"],
        updates=ExtractionUpdates(has_children=True),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.children.has_children is True
    assert state.document.children.status == "confirmed"

def test_regression_has_children_no():
    state = ConversationState()
    state.current_step = "has_children"
    
    patch = LLMExtractionResponse(
        intent="answer",
        target_fields=["has_children"],
        updates=ExtractionUpdates(has_children=False),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.children.has_children is False
    assert state.document.children.status == "none"

def test_regression_has_children_correction_to_yes():
    state = ConversationState()
    state.current_step = "executor"
    state.document.children.has_children = False
    state.document.children.status = "none"
    
    patch = LLMExtractionResponse(
        intent="correction",
        target_fields=["has_children", "expected_children_count"],
        updates=ExtractionUpdates(has_children=True, expected_children_count=2),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.children.has_children is True
    assert state.document.children.expected_count == 2
    assert state.document.children.status == "confirmed"

def test_regression_has_children_correction_to_no():
    state = ConversationState()
    state.current_step = "executor"
    state.document.children.has_children = True
    state.document.children.expected_count = 2
    state.document.children.names = ["Jonn", "Mia"]
    state.document.children.status = "confirmed"
    
    patch = LLMExtractionResponse(
        intent="correction",
        target_fields=["has_children"],
        updates=ExtractionUpdates(has_children=False),
        interpretation=ExtractionInterpretation()
    )
    state, _ = update_state(state, patch)
    
    assert state.document.children.has_children is False
    assert state.document.children.names == []
    assert state.document.children.expected_count is None
    assert state.document.children.status == "none"
