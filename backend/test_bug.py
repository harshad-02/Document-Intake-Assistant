import asyncio
import os
import sys

# Ensure we can import app
sys.path.insert(0, os.path.abspath("."))

from app.store import store
from app.services.conversation import handle_message

async def main():
    session = store.create()
    print("SESSION CREATED:", session.id)
    
    msgs = [
        "Harshad from pune",
        "no I have only 1 house",
        "yes jonn and mia",
        "both of them"
    ]
    
    for m in msgs:
        print("\n\n>>> SENDING MESSAGE:", m)
        res = await handle_message(session.id, m)
        print("REPLY:", res.reply)
        print("NEXT MISSING:", res.missing_fields)

if __name__ == "__main__":
    asyncio.run(main())
