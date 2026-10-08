import asyncio
from app.models.conversation import ConversationState
from app.models.document import DocumentState, ExecutorState
from app.services.llm_extractor import extract_updates

async def main():
    state = ConversationState()
    state.current_step = "executor"
    result = await extract_updates(state, "no")
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
