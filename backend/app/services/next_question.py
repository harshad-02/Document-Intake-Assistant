"""Next-question logic: deterministic field ordering.

Picks the first field that is unknown or unconfirmed, respecting the
children-applicability rule (skip children when has_children is false).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.state import FieldStatus, PersonalWishes


# Canonical field order from section 2.5
FIELD_ORDER = [
    "full_name",
    "home_address",
    "covers_worldwide_assets",
    "has_children",
    "children",
    "executor_name",
    "executor_relationship",
    "specific_gifts",
    "additional_wishes",
]

# Human-readable labels for template questions
FIELD_LABELS = {
    "full_name": "your full legal name",
    "home_address": "your home address",
    "covers_worldwide_assets": "whether this document should cover worldwide assets",
    "has_children": "whether you have any children",
    "children": "the names of your children",
    "executor_name": "the name of your chosen executor",
    "executor_relationship": "your relationship to the executor",
    "specific_gifts": "any specific gifts you'd like to include (or 'none')",
    "additional_wishes": "any additional wishes (or 'none')",
}


@dataclass
class NextQuestionResult:
    """What fields are still missing and what to ask next."""
    missing_fields: list[str]
    next_field: str | None
    review_time: bool


def compute_next_question(state: PersonalWishes) -> NextQuestionResult:
    """Determine the next field to ask about.

    Returns the ordered list of missing/unconfirmed fields, the single
    next_field, and whether all fields are complete (review time).
    """
    missing: list[str] = []

    # Check if children should be skipped
    hc = state.has_children
    children_applicable = not (
        hc.status == FieldStatus.CONFIRMED and hc.value is False
    )

    for field_name in FIELD_ORDER:
        # Skip children when not applicable
        if field_name == "children" and not children_applicable:
            continue

        field_obj = getattr(state, field_name)
        if field_obj.status in (FieldStatus.UNKNOWN, FieldStatus.UNCONFIRMED):
            missing.append(field_name)

    if not missing:
        return NextQuestionResult(
            missing_fields=[],
            next_field=None,
            review_time=True,
        )

    return NextQuestionResult(
        missing_fields=missing,
        next_field=missing[0],
        review_time=False,
    )


def get_template_question(field_name: str) -> str:
    """Generate a friendly template question for a field."""
    label = FIELD_LABELS.get(field_name, field_name)
    return f"Could you please tell me {label}?"
