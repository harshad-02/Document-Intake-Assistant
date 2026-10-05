import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from app.store import store
from app.services.conversation import handle_message
from unittest.mock import patch

async def mock_extract(state, message):
    from app.models.llm import LLMExtractionResponse, ExtractionUpdates, ExtractionInterpretation
    
    if message == "yes jonn and mia":
        return LLMExtractionResponse(
            intent="answer",
            target_fields=["children"],
            updates=ExtractionUpdates(
                has_children=True,
                expected_children_count=2,
                children_names=["Jonn", "Mia"]
            ),
            interpretation=ExtractionInterpretation(status="clear")
        )
    elif message == "both of them":
        return LLMExtractionResponse(
            intent="correction",
            target_fields=[],
            updates=ExtractionUpdates(
                executor_names=["Jonn", "Mia"],
                executor_relationship="children",
                executor_status="confirmed",
                has_children=None,
                children_names=[]
            ),
            interpretation=ExtractionInterpretation(status="clear")
        )
    else:
        from app.services.llm_extractor import extract_updates
        return await extract_updates(state, message)

async def main():
    session = store.create()
    session.state.document.full_name.status = "confirmed"
    session.state.document.home_address.status = "confirmed"
    session.state.document.covers_worldwide_assets.covers_worldwide = False
    session.state.document.covers_worldwide_assets.status = "confirmed"
    session.state.current_step = "has_children"
    
    with patch("app.services.conversation.extract_updates", side_effect=mock_extract):
        res1 = await handle_message(session.id, "yes jonn and mia")
        res2 = await handle_message(session.id, "both of them")
        
        print("\n\nFINAL MISSING FIELDS:", res2.missing_fields)
        print("FINAL CHILDREN STATUS:", res2.state.children.status)

if __name__ == "__main__":
    asyncio.run(main())
