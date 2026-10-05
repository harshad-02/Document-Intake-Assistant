"""Mock LLM response fixtures.

Each fixture is a dict keyed by a trigger phrase (from the user message).
The values are raw JSON strings that the MockLLM will return.
"""

import json

# ── 1. Valid single-field answer ──────────────────────────────────────────────
VALID_SINGLE_FIELD = json.dumps({
    "updates": [
        {
            "field": "full_name",
            "op": "set",
            "value": "John Smith",
            "evidence": "John Smith",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Thank you, John! Could you please tell me your home address?"
})

# ── 2. Valid multi-field answer ───────────────────────────────────────────────
VALID_MULTI_FIELD = json.dumps({
    "updates": [
        {
            "field": "full_name",
            "op": "set",
            "value": "Jane Doe",
            "evidence": "Jane Doe",
            "certainty": "clear"
        },
        {
            "field": "home_address",
            "op": "set",
            "value": "42 Test Lane, London",
            "evidence": "42 Test Lane, London",
            "certainty": "clear"
        },
        {
            "field": "executor_name",
            "op": "set",
            "value": "James Doe",
            "evidence": "James Doe",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Great, I've noted your name, address, and executor. Does this document need to cover worldwide assets?"
})

# ── 3. Correction ────────────────────────────────────────────────────────────
CORRECTION = json.dumps({
    "updates": [
        {
            "field": "executor_name",
            "op": "correct",
            "value": "Anna Smith",
            "evidence": "actually my sister Anna Smith",
            "certainty": "clear"
        },
        {
            "field": "executor_relationship",
            "op": "correct",
            "value": "Sister",
            "evidence": "my sister",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Got it — I've updated your executor to your sister Anna Smith."
})

# ── 4. Ambiguous answer ──────────────────────────────────────────────────────
AMBIGUOUS = json.dumps({
    "updates": [
        {
            "field": "executor_relationship",
            "op": "set",
            "value": "Brother",
            "evidence": "my brother",
            "certainty": "clear"
        }
    ],
    "clarifications": [
        {"field": "executor_name", "reason": "missing"}
    ],
    "reply": "Your brother — could you tell me his full name?"
})

# ── 5. Contradictory answer ──────────────────────────────────────────────────
CONTRADICTORY = json.dumps({
    "updates": [
        {
            "field": "children",
            "op": "set",
            "value": ["Little Timmy"],
            "evidence": "Little Timmy",
            "certainty": "clear"
        }
    ],
    "clarifications": [
        {"field": "has_children", "reason": "contradictory"}
    ],
    "reply": "I notice you mentioned Little Timmy but earlier said you have no children. Could you clarify?"
})

# ── 6. Fabricated evidence ───────────────────────────────────────────────────
FABRICATED_EVIDENCE = json.dumps({
    "updates": [
        {
            "field": "full_name",
            "op": "set",
            "value": "Robert Tables",
            "evidence": "Robert Tables",
            "certainty": "clear"
        },
        {
            "field": "home_address",
            "op": "set",
            "value": "123 Fake Street",
            "evidence": "I live at 123 Fake Street",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Thank you! I've noted your details."
})

# ── 7. Malformed JSON ────────────────────────────────────────────────────────
MALFORMED_JSON = '```json\n{"updates": [{"field": "full_name", "op": "set"'

# ── 8. Wrong schema ──────────────────────────────────────────────────────────
WRONG_SCHEMA = json.dumps({
    "updates": [
        {
            "field": "favourite_color",
            "op": "set",
            "value": "blue",
            "evidence": "blue",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Noted your favourite colour!"
})

# ── 9. Empty reply ───────────────────────────────────────────────────────────
EMPTY_REPLY = json.dumps({
    "updates": [],
    "clarifications": [],
    "reply": ""
})

# ── 10. Boolean field ────────────────────────────────────────────────────────
VALID_BOOLEAN = json.dumps({
    "updates": [
        {
            "field": "has_children",
            "op": "set",
            "value": True,
            "evidence": "yes I have children",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Could you tell me the names of your children?"
})

# ── 11. Children names ───────────────────────────────────────────────────────
VALID_CHILDREN = json.dumps({
    "updates": [
        {
            "field": "children",
            "op": "set",
            "value": ["Alice", "Bob"],
            "evidence": "Alice and Bob",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Thank you! Who would you like as your executor?"
})

# ── 12. No children ──────────────────────────────────────────────────────────
NO_CHILDREN = json.dumps({
    "updates": [
        {
            "field": "has_children",
            "op": "set",
            "value": False,
            "evidence": "no children",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Understood. Who would you like as your executor?"
})

# ── 13. Worldwide assets ─────────────────────────────────────────────────────
WORLDWIDE_ASSETS = json.dumps({
    "updates": [
        {
            "field": "covers_worldwide_assets",
            "op": "set",
            "value": True,
            "evidence": "yes worldwide",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Got it — worldwide coverage. Do you have any children?"
})

# ── 14. Specific gifts none ──────────────────────────────────────────────────
NO_GIFTS = json.dumps({
    "updates": [
        {
            "field": "specific_gifts",
            "op": "set",
            "value": [],
            "evidence": "no specific gifts",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "No specific gifts noted. Do you have any additional wishes?"
})

# ── 15. No additional wishes ─────────────────────────────────────────────────
NO_WISHES = json.dumps({
    "updates": [
        {
            "field": "additional_wishes",
            "op": "set",
            "value": [],
            "evidence": "no additional wishes",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Thank you! Let me prepare a summary for your review."
})

# ── 16. Address ───────────────────────────────────────────────────────────────
VALID_ADDRESS = json.dumps({
    "updates": [
        {
            "field": "home_address",
            "op": "set",
            "value": "10 Downing Street, London",
            "evidence": "10 Downing Street, London",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Thank you! Does this document need to cover assets worldwide?"
})

# ── 17. Executor relationship ─────────────────────────────────────────────────
EXECUTOR_RELATIONSHIP = json.dumps({
    "updates": [
        {
            "field": "executor_relationship",
            "op": "set",
            "value": "Brother",
            "evidence": "my brother",
            "certainty": "clear"
        }
    ],
    "clarifications": [],
    "reply": "Do you have any specific gifts you'd like to include?"
})

# ── Default / generic ─────────────────────────────────────────────────────────
GENERIC_RESPONSE = json.dumps({
    "updates": [],
    "clarifications": [],
    "reply": "Could you tell me a bit more about that?"
})


# ── Fixture map: trigger phrase → raw JSON string ─────────────────────────────
FIXTURE_MAP: dict[str, str] = {
    "my name is john smith": VALID_SINGLE_FIELD,
    "i'm jane doe, i live at 42 test lane, london, and my executor is james doe": VALID_MULTI_FIELD,
    "actually my sister anna smith": CORRECTION,
    "my brother": AMBIGUOUS,
    "little timmy": CONTRADICTORY,
    "my name is robert tables": FABRICATED_EVIDENCE,
    "malformed response trigger": MALFORMED_JSON,
    "wrong schema trigger": WRONG_SCHEMA,
    "empty reply trigger": EMPTY_REPLY,
    "yes i have children": VALID_BOOLEAN,
    "alice and bob": VALID_CHILDREN,
    "no children": NO_CHILDREN,
    "yes worldwide": WORLDWIDE_ASSETS,
    "no specific gifts": NO_GIFTS,
    "no additional wishes": NO_WISHES,
    "10 downing street, london": VALID_ADDRESS,
    "my brother is my executor": EXECUTOR_RELATIONSHIP,
}

# ── Scripted scenario: happy path full interview ──────────────────────────────
HAPPY_PATH_SCRIPT = [
    VALID_SINGLE_FIELD,   # Turn 0: name
    VALID_ADDRESS,        # Turn 1: address
    WORLDWIDE_ASSETS,     # Turn 2: worldwide
    VALID_BOOLEAN,        # Turn 3: has_children
    VALID_CHILDREN,       # Turn 4: children names
    json.dumps({          # Turn 5: executor name
        "updates": [
            {"field": "executor_name", "op": "set", "value": "James Smith",
             "evidence": "James Smith", "certainty": "clear"}
        ],
        "clarifications": [],
        "reply": "And what is your relationship to James?"
    }),
    EXECUTOR_RELATIONSHIP,  # Turn 6: executor relationship
    NO_GIFTS,              # Turn 7: gifts
    NO_WISHES,             # Turn 8: additional wishes
]
