"""MockLLM: deterministic LLM for tests and no-key demos.

Selection strategy:
1. If a ScriptedMockLLM is used, returns responses by turn index.
2. Otherwise, matches trigger phrases in the user message.
3. Unmatched messages return a safe generic response.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from app.llm.interface import LLMError, LLMErrorType, LLMInterface, LLMRequest
from tests.fixtures.mock_responses import FIXTURE_MAP, GENERIC_RESPONSE


class MockLLM(LLMInterface):
    """Fixture-based mock LLM for tests and demos."""

    async def extract_turn(self, request: LLMRequest) -> str:
        msg = request.user_message.strip().lower()
        # Try exact match first
        if msg in FIXTURE_MAP:
            return FIXTURE_MAP[msg]
        # Try substring match
        for trigger, response in FIXTURE_MAP.items():
            if trigger in msg:
                return response
        return GENERIC_RESPONSE


class ScriptedMockLLM(LLMInterface):
    """Returns responses by turn index for scripted scenarios."""

    def __init__(self, script: list[str]):
        self._script = script
        self._turn = 0

    async def extract_turn(self, request: LLMRequest) -> str:
        if self._turn < len(self._script):
            response = self._script[self._turn]
            self._turn += 1
            return response
        return GENERIC_RESPONSE


# ── Error-simulating test doubles ─────────────────────────────────────────────


class TimeoutMockLLM(LLMInterface):
    """Simulates a timeout."""
    async def extract_turn(self, request: LLMRequest) -> str:
        raise LLMError(LLMErrorType.TIMEOUT, "LLM request timed out")


class RateLimitMockLLM(LLMInterface):
    """Simulates a rate limit."""
    async def extract_turn(self, request: LLMRequest) -> str:
        raise LLMError(LLMErrorType.RATE_LIMITED, "Rate limit exceeded. Daily limits reset at midnight Pacific time. You can still edit fields directly.")


class AuthErrorMockLLM(LLMInterface):
    """Simulates an auth error."""
    async def extract_turn(self, request: LLMRequest) -> str:
        raise LLMError(LLMErrorType.AUTH_ERROR, "Invalid or missing API key. Please check your .env configuration.")


class ServerErrorMockLLM(LLMInterface):
    """Simulates a server error."""
    async def extract_turn(self, request: LLMRequest) -> str:
        raise LLMError(LLMErrorType.SERVER_ERROR, "LLM service is temporarily unavailable")
