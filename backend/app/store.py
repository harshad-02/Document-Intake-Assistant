"""In-memory session store, keyed by session id."""

from __future__ import annotations

import asyncio
from typing import Optional

from app.models.state import Session


class SessionStore:
    """Thread-safe in-memory session store."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def create(self) -> Session:
        """Create a new session and return it."""
        session = Session()
        self._sessions[session.id] = session
        self._locks[session.id] = asyncio.Lock()
        return session

    def get(self, session_id: str) -> Optional[Session]:
        """Get a session by id, or None if not found."""
        return self._sessions.get(session_id)

    def save(self, session: Session) -> None:
        """Save (update) a session."""
        self._sessions[session.id] = session

    def delete(self, session_id: str) -> None:
        """Delete a session."""
        self._sessions.pop(session_id, None)
        self._locks.pop(session_id, None)

    def get_lock(self, session_id: str) -> asyncio.Lock:
        """Get the per-session lock."""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]


# Global singleton
store = SessionStore()
