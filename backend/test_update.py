import asyncio
import json
from app.models.conversation import ConversationState
from app.models.document import DocumentState
from app.services.llm_extractor import extract_updates
from app.services.state_manager import update_state

async def main():
    state = ConversationState()
    state.current_step = "executor"
    patch = await extract_updates(state, "no")
    print("PATCH:", patch.model_dump_json(indent=2))
    state, warnings = update_state(state, patch)
    print("STATE:", state.document.model_dump_json(indent=2))
    from app.services.state_machine import get_next_step
    print("NEXT_STEP:", get_next_step(state))

if __name__ == "__main__":
    asyncio.run(main())
