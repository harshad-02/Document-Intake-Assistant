"""LLM provider factory.

Reads LLM_PROVIDER from config and returns the appropriate implementation.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.llm.interface import LLMError, LLMErrorType, LLMInterface

logger = logging.getLogger(__name__)

_instance: LLMInterface | None = None


def get_llm_provider() -> LLMInterface:
    """Return the configured LLM provider (singleton)."""
    global _instance
    if _instance is not None:
        return _instance

    provider = settings.LLM_PROVIDER.lower()

    if provider == "mock":
        from app.llm.mock import MockLLM
        _instance = MockLLM()
        logger.info("Using MockLLM provider")

    elif provider == "gemini":
        try:
            from app.llm.gemini import GeminiLLM
            _instance = GeminiLLM()
            logger.info("Using GeminiLLM provider")
        except LLMError:
            # Fall back to mock with a visible warning
            from app.llm.mock import MockLLM
            _instance = MockLLM()
            logger.warning(
                "Gemini not configured — falling back to MockLLM. "
                "Set GEMINI_API_KEY and GEMINI_MODEL in .env to use Gemini."
            )

    else:
        raise LLMError(
            LLMErrorType.NOT_CONFIGURED,
            f"Unknown LLM_PROVIDER: '{provider}'. Use 'mock' or 'gemini'."
        )

    return _instance


def reset_provider() -> None:
    """Reset the singleton (used in tests)."""
    global _instance
    _instance = None
