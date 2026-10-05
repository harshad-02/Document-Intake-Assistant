"""Gemini LLM client using the google-genai SDK."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.config import settings
from app.llm.interface import LLMError, LLMErrorType, LLMInterface, LLMRequest

logger = logging.getLogger(__name__)


class GeminiLLM(LLMInterface):
    """Google Gemini (Flash-Lite) LLM client.

    Uses the google-genai SDK. Maps SDK/HTTP errors to our own error types.
    """

    def __init__(self):
        if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
            raise LLMError(
                LLMErrorType.NOT_CONFIGURED,
                "GEMINI_API_KEY or GEMINI_MODEL not set. "
                "Copy .env.example to .env and fill in your values, "
                "or use LLM_PROVIDER=mock."
            )

        try:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self._model = settings.GEMINI_MODEL
        except ImportError:
            raise LLMError(
                LLMErrorType.NOT_CONFIGURED,
                "google-genai package not installed. Run: pip install google-genai"
            )

    async def extract_turn(self, request: LLMRequest) -> str:
        """Call Gemini and return raw text."""
        from google import genai
        from google.genai import types

        # Build the conversation messages
        contents = []

        # Add recent history
        for msg in request.recent_messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))

        # Build user message with context
        from app.llm.prompts import build_user_context
        context = build_user_context(request.state_json, request.next_field)
        full_user_message = f"{context}\n\nUser message: {request.user_message}"

        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=full_user_message)]
        ))

        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            temperature=0.2,
            max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        )

        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model,
                contents=contents,
                config=config,
            )
            if not response.text:
                raise LLMError(LLMErrorType.BAD_OUTPUT, "Empty response from Gemini")
            return response.text

        except LLMError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "quota" in error_str:
                raise LLMError(
                    LLMErrorType.RATE_LIMITED,
                    "Rate limit exceeded. Daily limits reset at midnight Pacific time. "
                    "You can still edit fields directly in the form."
                )
            elif "401" in error_str or "403" in error_str or "api key" in error_str:
                raise LLMError(
                    LLMErrorType.AUTH_ERROR,
                    "Invalid API key. Please check your GEMINI_API_KEY in .env."
                )
            elif "timeout" in error_str:
                raise LLMError(LLMErrorType.TIMEOUT, "Request to Gemini timed out.")
            elif "500" in error_str or "502" in error_str or "503" in error_str:
                raise LLMError(LLMErrorType.SERVER_ERROR, "Gemini service error. Please try again.")
            else:
                logger.error(f"Unexpected Gemini error: {type(e).__name__}: {e}")
                raise LLMError(LLMErrorType.OTHER, f"Unexpected error: {type(e).__name__}")
