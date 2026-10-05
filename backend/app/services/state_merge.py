"""State merge: validates an LLM proposal and produces a new state.

The LLM proposes, the code decides. Every rule from section 2.4 is
enforced here. The function is pure — no side effects, returns a new state.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from app.models.llm_contract import (
    Certainty,
    FieldName,
    LLMTurnResponse,
    Op,
    ProposedUpdate,
)
from app.models.state import FieldStatus, PersonalWishes, StateField


@dataclass
class MergeResult:
    """Outcome of merging a proposal into state."""
    new_state: PersonalWishes
    applied: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

_BOOLEAN_FIELDS = {FieldName.COVERS_WORLDWIDE_ASSETS, FieldName.HAS_CHILDREN}
_LIST_FIELDS = {FieldName.CHILDREN, FieldName.SPECIFIC_GIFTS, FieldName.ADDITIONAL_WISHES}
_TEXT_FIELDS = {FieldName.FULL_NAME, FieldName.HOME_ADDRESS, FieldName.EXECUTOR_NAME, FieldName.EXECUTOR_RELATIONSHIP}


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _evidence_present(evidence: str, user_message: str) -> bool:
    """Check evidence appears in the user's message (case-insensitive, whitespace-normalised)."""
    if not evidence or not evidence.strip():
        return False
    return _normalise(evidence) in _normalise(user_message)


def _type_ok(field_name: FieldName, value: Any) -> bool:
    """Check value type matches the field's expected type."""
    if field_name in _BOOLEAN_FIELDS:
        return isinstance(value, bool)
    if field_name in _LIST_FIELDS:
        return isinstance(value, list)
    if field_name in _TEXT_FIELDS:
        return isinstance(value, str) and len(value.strip()) > 0
    return False


# ── Main merge function ──────────────────────────────────────────────────────


def merge_state(
    current: PersonalWishes,
    user_message: str,
    response: LLMTurnResponse,
) -> MergeResult:
    """Apply validated updates from an LLM response to the current state.

    Returns a MergeResult with the new state and lists of applied/rejected
    updates and warnings. Invalid updates are rejected individually; valid
    ones still apply.
    """
    # Work on a deep copy so the operation is atomic per turn
    new_state = deepcopy(current)
    applied: list[str] = []
    rejected: list[str] = []
    warnings: list[str] = []

    for update in response.updates:
        reason = _validate_update(update, user_message, new_state)
        if reason:
            rejected.append(f"{update.field.value}: {reason}")
            warnings.append(f"Rejected update for '{update.field.value}': {reason}")
            continue

        # Apply the update
        _apply_update(update, new_state, applied, warnings)

    # Post-merge contradiction checks
    _check_children_contradictions(new_state, warnings)

    return MergeResult(
        new_state=new_state,
        applied=applied,
        rejected=rejected,
        warnings=warnings,
    )


# ── Validation ────────────────────────────────────────────────────────────────


def _validate_update(
    update: ProposedUpdate,
    user_message: str,
    state: PersonalWishes,
) -> str | None:
    """Return a rejection reason or None if valid."""
    # Op=clear doesn't need value/evidence checks
    if update.op == Op.CLEAR:
        return None

    # Type check
    if not _type_ok(update.field, update.value):
        expected = "boolean" if update.field in _BOOLEAN_FIELDS else (
            "list" if update.field in _LIST_FIELDS else "non-empty text"
        )
        return f"wrong type (expected {expected})"

    # Evidence check
    if not _evidence_present(update.evidence, user_message):
        return f"evidence not found in user message"

    # Children while has_children is false
    if update.field == FieldName.CHILDREN:
        hc = state.has_children
        if hc.status == FieldStatus.CONFIRMED and hc.value is False:
            return "children supplied while has_children is false"

    return None


# ── Application ───────────────────────────────────────────────────────────────


def _apply_update(
    update: ProposedUpdate,
    state: PersonalWishes,
    applied: list[str],
    warnings: list[str],
) -> None:
    """Mutate state by applying a single validated update."""
    field_obj: StateField = getattr(state, update.field.value)

    if update.op == Op.CLEAR:
        field_obj.value = None
        field_obj.status = FieldStatus.UNKNOWN
        applied.append(f"{update.field.value}: cleared")
        return

    # Determine status from certainty
    if update.certainty == Certainty.AMBIGUOUS:
        new_status = FieldStatus.UNCONFIRMED
    else:
        new_status = FieldStatus.CONFIRMED

    # For 'correct', always mark confirmed
    if update.op == Op.CORRECT:
        new_status = FieldStatus.CONFIRMED

    field_obj.value = update.value
    field_obj.status = new_status
    applied.append(f"{update.field.value}: {update.op.value} -> {new_status.value}")


def _check_children_contradictions(state: PersonalWishes, warnings: list[str]) -> None:
    """Rule-based contradiction checks independent of the LLM."""
    hc = state.has_children
    children = state.children

    # has_children false but children are stored → clear children
    if (
        hc.status == FieldStatus.CONFIRMED
        and hc.value is False
        and children.value is not None
        and children.status != FieldStatus.UNKNOWN
    ):
        children.value = None
        children.status = FieldStatus.UNKNOWN
        warnings.append("Children cleared because has_children is false.")

    # has_children true and zero children names → children stay unknown
    if (
        hc.status == FieldStatus.CONFIRMED
        and hc.value is True
        and children.status == FieldStatus.UNKNOWN
    ):
        pass  # children will be asked next by next_question logic
