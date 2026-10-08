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
4. If the user's answer doesn't fit the current question, set `interpretation.status = "unclear"`, `interpretation.needs_clarification = true`, and leave updates empty.
5. If the user explicitly corrects a previous answer (e.g., "actually my address is X", "remove the car gift", "change the gift to 500 million"), set `intent="correction"`, `intent="removal"`, or `intent="addition"` and output the new values.
6. If the current step is "executor" and the user says "no" or "none", set `executor_status` to "not_decided" or "declined", and ensure `interpretation.status = "clear"`.
7. For the "worldwide_assets" step: If the user answers affirmatively ("yes", "worldwide", "all my assets"), set `covers_worldwide_assets=true`. If they answer negatively ("no", "only India", "just my house in US"), set `covers_worldwide_assets=false` and capture any specified region in `asset_region`. If the user specifies asset items ("one car and two houses"), put them in `asset_items`. IMPORTANT: A single message can contain BOTH the coverage answer and specific items. For example, "no I have only one car and house" MUST result in `covers_worldwide_assets=false` AND `asset_items=["one car", "one house"]` AND `target_fields` must include BOTH `["covers_worldwide_assets", "assets"]`.
8. Parse specific gifts into the `specific_gifts` list, separating the `item` and the `recipient`. For example, "1 car to Jonn" -> item="1 car", recipient="Jonn".
9. Any free-form extra wishes (e.g., "I want to give both of them 1 billion") that don't fit structured gifts should go to `additional_wishes`.
10. Identify exactly which fields the user is talking about in `target_fields` (e.g., `["children"]`, `["assets"]`, `["executor"]`, `["specific_gifts"]`, `["full_name"]`). The extracted `updates` must ONLY contain data for fields listed in `target_fields`.
11. Do NOT blindly map "yes" or "no" to the current step if the user's answer is clearly about something else. For example, if the current step is `has_children` and the user says "No assets", the user is talking about `assets`! You MUST output `"target_fields": ["assets"]`, `asset_items=[]`, and LEAVE `has_children` NULL.
12. RETURN ONLY VALID JSON. Return only a structured patch. Do not invent information. No prose, no markdown fences.
13. If the current step is "generation_confirmation", and the user agrees to generate (e.g., "yes", "ready"), set `intent: "generation_confirmation"`. If they decline (e.g., "no", "wait"), set `intent: "answer"` and `interpretation.needs_clarification = true` and leave updates empty.

JSON SCHEMA:
{
  "intent": "answer" | "correction" | "addition" | "removal" | "confirmation" | "generation_confirmation",
  "target_fields": ["string"],
  "updates": {
    "full_name": null, "home_address": null,
    "covers_worldwide_assets": null, "asset_region": null, "asset_items": null,
    "has_children": null, "expected_children_count": null, "children_names": null,
    "executor_names": null, "executor_relationship": null, "executor_status": null,
    "specific_gifts": [{"item": "string", "recipient": "string"}], "additional_wishes": null
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
