import asyncio
import os
import sys

# Ensure we can import app
sys.path.insert(0, os.path.abspath("."))

from app.store import store
from app.services.conversation import handle_message
from app.services.llm_extractor import extract_updates
from unittest.mock import patch

async def mock_extract(state, message):
    from app.models.llm import LLMExtractionResponse, ExtractionUpdates, ExtractionInterpretation
    
    if message == "yes jonn and mia":
        # Missing expected_children_count!
        return LLMExtractionResponse(
            intent="answer",
            target_fields=["children"],
            updates=ExtractionUpdates(
                has_children=True,
                children_names=["Jonn", "Mia"]
            ),
            interpretation=ExtractionInterpretation(status="clear")
        )
    elif message == "both of them":
        # Extractor thinks it's about executor because the user mentions "them"
        return LLMExtractionResponse(
            intent="answer",
            target_fields=["executor"],
            updates=ExtractionUpdates(
                executor_names=["Jonn", "Mia"],
                executor_relationship="children",
                executor_status="confirmed"
            ),
            interpretation=ExtractionInterpretation(status="clear")
        )
    else:
        return await extract_updates(state, message)

async def main():
    session = store.create()
    
    # Pre-fill
    session.state.document.full_name.value = "Harshad"
    session.state.document.full_name.status = "confirmed"
    session.state.document.home_address.value = "pune"
    session.state.document.home_address.status = "confirmed"
    session.state.document.covers_worldwide_assets.covers_worldwide = False
    session.state.document.covers_worldwide_assets.status = "confirmed"
    session.state.document.assets.items = ["1 house"]
    session.state.document.assets.status = "confirmed"
    session.state.current_step = "has_children"
    
    with patch("app.services.conversation.extract_updates", side_effect=mock_extract):
        res1 = await handle_message(session.id, "yes jonn and mia")
        print("\n\nRES1 NEXT MISSING:", res1.missing_fields)
        
        res2 = await handle_message(session.id, "both of them")
        print("\n\nRES2 NEXT MISSING:", res2.missing_fields)

if __name__ == "__main__":
    asyncio.run(main())
