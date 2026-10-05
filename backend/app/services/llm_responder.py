"""LLM Response Generator Service."""

from __future__ import annotations
import logging

from app.models.conversation import ConversationState
from app.llm.interface import LLMRequest
from app.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_RESPONDER = """You are a friendly legal assistant helping a user create a Personal Wishes document.
Your job is to read the CURRENT_STATE, the NEXT_STEP to ask about, and optionally any WARNINGS or context about what was just updated.
Then, output a 1-2 sentence response that:
1. Briefly acknowledge what was just recorded using ONLY the properties provided in JUST_EXTRACTED. Do NOT echo or parrot the user's raw message (e.g., if JUST_EXTRACTED contains full_name="John", acknowledge "John", do NOT say "John from Paris" even if the user said it).
2. Asks exactly ONE question corresponding to the NEXT_STEP.
3. If the user's previous answer was unclear, ask a clarifying version of the SAME question.
4. DO NOT invent state. DO NOT ask multiple questions.

Return plain text only. No JSON, no markdown.
"""

async def generate_response(
    state: ConversationState, 
    next_step: str, 
    warnings: list[str],
    recent_messages: list[dict[str, str]],
    extracted_updates: dict
) -> str:
    llm = get_llm_provider()
    
    state_json = state.document.model_dump_json(indent=2)
    
    context = []
    if warnings:
        context.append(f"WARNINGS from extraction: {', '.join(warnings)}")
    context.append(f"NEXT_STEP to ask: {next_step}")
    context.append(f"CURRENT_STATE:\n{state_json}")
    import json
    context.append(f"JUST_EXTRACTED:\n{json.dumps(extracted_updates)}")
    
    if state.document.full_name.value:
        context.append(f"The user's normalized full name is {state.document.full_name.value}. When addressing the user, use ONLY this normalized full name. Never repeat the raw user message.")
    
    user_context = "\n".join(context)
    
    request = LLMRequest(
        system_prompt=SYSTEM_PROMPT_RESPONDER,
        state_json="",
        recent_messages=recent_messages,
        user_message=user_context,
        next_field=next_step,
        require_json=False
    )
    
    try:
        raw = await llm.extract_turn(request)
        return raw.strip()
    except Exception as e:
        logger.error(f"Responder failed: {e}")
        return "I'm sorry, could you repeat that?"
