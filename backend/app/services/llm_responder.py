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
1. Briefly acknowledge what was just recorded. When addressing or thanking the user by name, use ONLY their exact extracted `full_name` (e.g., "Thanks, John."). DO NOT append their location or other properties to their name (e.g., NEVER say "Thanks, John from Paris"). Never parrot the user's raw message.
2. Asks exactly ONE question corresponding to the NEXT_STEP.
3. If the user's previous answer was unclear, ask a clarifying version of the SAME question.
4. If NEXT_STEP is 'generation_confirmation', ask the user if they are ready to generate the document now that all information is gathered. If the user just answered 'no' to this (check recent messages), ask them what they would like to update instead.
5. If NEXT_STEP is 'complete', simply state that the document has been successfully generated or updated. DO NOT ask any questions.
6. DO NOT invent state. DO NOT ask multiple questions.

Return plain text only. No JSON, no markdown.
"""

async def generate_response(
    state: ConversationState, 
    next_step: str, 
    warnings: list[str],
    recent_messages: list[dict[str, str]],
    extracted_updates: dict,
    user_message: str
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
    context.append(f"THE USER JUST SAID: '{user_message}'")
    
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
