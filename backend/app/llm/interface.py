"""LLM interface and error types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class LLMErrorType(str, Enum):
    RATE_LIMITED = "LLM_RATE_LIMITED"
    AUTH_ERROR = "NOT_CONFIGURED"
    TIMEOUT = "LLM_UNAVAILABLE"
    SERVER_ERROR = "LLM_UNAVAILABLE"
    BAD_OUTPUT = "LLM_BAD_OUTPUT"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    OTHER = "LLM_UNAVAILABLE"


class LLMError(Exception):
    """Raised when the LLM call fails."""
    def __init__(self, error_type: LLMErrorType, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


@dataclass
class LLMRequest:
    """Everything needed to call the LLM for one turn."""
    system_prompt: str
    state_json: str
    recent_messages: list[dict[str, str]]  # [{"role": ..., "content": ...}]
    user_message: str
    next_field: str | None
    require_json: bool = True


class LLMInterface(ABC):
    """Abstract interface for LLM providers.

    Implementations must produce raw text; parsing and validation
    happen outside so every provider is treated identically.
    """

    @abstractmethod
    async def extract_turn(self, request: LLMRequest) -> str:
        """Send the request to the LLM and return raw text."""
        ...
