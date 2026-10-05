"""LLM Extraction Service."""

from __future__ import annotations
import json
import logging
from typing import Optional

from pydantic import ValidationError

from app.models.conversation import ConversationState
from app.models.llm import LLMExtractionResponse
from app.llm.interface import LLMRequest
from app.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_EXTRACTION = """You are an information extraction assistant.
Your job is to read a user's message, look at the CURRENT_STEP of the conversation and the current STATE, and extract any relevant updates as a structured JSON patch.

RULES:
1. If the user's message provides information for multiple fields (e.g., 'Harshad from Pune' or 'My name is Harshad and I live in Pune'), extract all identified fields separately (e.g., full_name='Harshad', home_address='Pune'). Short contextual answers ("yes", "no", "2") apply ONLY to the CURRENT_STEP.
2. The current application state is authoritative. Use previously confirmed entities when the user refers to them using pronouns or phrases such as 'both', 'both them', 'my sons', 'my children', 'the two of them', 'him', or 'her'.
3. The current step has priority when interpreting short contextual answers. Do not ask for information that can be resolved from the existing state.
4. If the user's answer doesn't fit the current question (e.g. they say "Car" but the question is "who is your executor?"), set `interpretation.status = "unclear"`, `interpretation.needs_clarification = true`, and leave updates empty.
5. If the user explicitly corrects a previous answer (e.g., "actually my address is X"), update that specific field.
6. If the current step is "executor" and the user says "no" or "none", set `executor_status` to "not_decided" or "declined". Do NOT touch `has_children` or any other field.
7. If the current step is "specific_gifts" or "additional_wishes" and the user says "no", "none", or similar, leave the field empty in updates, but set `interpretation.status = "clear"`.
8. RETURN ONLY VALID JSON. Return only a structured patch. Do not invent information. No prose, no markdown fences.

JSON SCHEMA:
{
  "updates": {
    "full_name": null, "home_address": null,
    "covers_worldwide_assets": null, // Use "worldwide" if they want all assets, or the specific assets string if they specify them
    "has_children": null, "expected_children_count": null, "children_names": [],
    "executor_names": [], "executor_relationship": null, "executor_status": null,
    "specific_gifts": [], "additional_wishes": null
  },
  "interpretation": {
    "status": "clear" | "unclear",
    "needs_clarification": false,
    "reason": null
  }
}
"""

def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # Remove first line and last line
        lines = text.split("\n")
        if len(lines) >= 2:
            lines = lines[1:-1]
            text = "\n".join(lines).strip()
    return text

async def extract_updates(state: ConversationState, user_message: str) -> Optional[LLMExtractionResponse]:
    llm = get_llm_provider()
    
    state_json = state.document.model_dump_json(indent=2)
    current_step = state.current_step
    
    user_context = f"CURRENT_STEP: {current_step}\nCURRENT_STATE:\n{state_json}\n\nUSER_MESSAGE: {user_message}"
    
    request = LLMRequest(
        system_prompt=SYSTEM_PROMPT_EXTRACTION,
        state_json="",  # handled in user_context
        recent_messages=[], # Keep extraction stateless to current message or add minimal history
        user_message=user_context,
        next_field=""
    )
    
    try:
        raw = await llm.extract_turn(request)
        cleaned = _strip_fences(raw)
        data = json.loads(cleaned)
        return LLMExtractionResponse.model_validate(data)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None
