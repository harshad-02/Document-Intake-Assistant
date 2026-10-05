import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from app.store import store
from app.services.conversation import handle_message

async def main():
    session = store.create()
    
    await handle_message(session.id, "Harshad from pune")
    await handle_message(session.id, "no I had 1 car")
    res = await handle_message(session.id, "2 jonn and mia")
    
    print("\n\nSTATE SNAPSHOT JSON:")
    print(res.state.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
