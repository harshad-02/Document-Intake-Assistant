"""Document generator: pure function of state → markdown string.

Deterministic — same state in, same text out. Never calls the LLM.
"""

from __future__ import annotations

from app.models.state import FieldStatus, PersonalWishes, StateField


def _render_value(field: StateField, fallback: str = "[Not yet provided]") -> str:
    """Render a field value with status markers."""
    if field.status == FieldStatus.UNKNOWN or field.value is None:
        return fallback
    if field.status == FieldStatus.UNCONFIRMED:
        if isinstance(field.value, list):
            items = ", ".join(str(v) for v in field.value)
            return f"{items} ⚠️ *[To be confirmed]*"
        return f"{field.value} ⚠️ *[To be confirmed]*"
    # Confirmed
    if isinstance(field.value, bool):
        return "Yes" if field.value else "No"
    if isinstance(field.value, list):
        if len(field.value) == 0:
            return "None specified"
        return ", ".join(str(v) for v in field.value)
    return str(field.value)


def _render_bool(field: StateField) -> str:
    """Render a boolean field."""
    if field.status == FieldStatus.UNKNOWN or field.value is None:
        return "[Not yet provided]"
    val = "Yes" if field.value else "No"
    if field.status == FieldStatus.UNCONFIRMED:
        return f"{val} ⚠️ *[To be confirmed]*"
    return val


def generate_document(state: PersonalWishes) -> str:
    """Generate the Personal Wishes Document as markdown.

    Confirmed values appear plainly. Unconfirmed values are flagged.
    Unknown values show placeholders.
    """
    lines: list[str] = []

    # Banner
    lines.append("---")
    lines.append("⚠️ **FICTIONAL SAMPLE: NOT LEGAL ADVICE** ⚠️")
    lines.append("---")
    lines.append("")
    lines.append("# Personal Wishes Document")
    lines.append("")

    # Section 1: Personal Details
    lines.append("## Personal Details")
    lines.append("")
    lines.append(f"- **Full Name:** {_render_value(state.full_name)}")
    lines.append(f"- **Home Address:** {_render_value(state.home_address)}")
    lines.append("")

    # Section 2: Scope of Assets
    lines.append("## Scope of Assets")
    lines.append("")
    lines.append(f"- **Covers Worldwide Assets:** {_render_bool(state.covers_worldwide_assets)}")
    lines.append("")

    # Section 3: Family and Children
    lines.append("## Family and Children")
    lines.append("")
    hc = state.has_children
    if hc.status == FieldStatus.UNKNOWN or hc.value is None:
        lines.append("- **Has Children:** [Not yet provided]")
    elif hc.value is False:
        marker = " ⚠️ *[To be confirmed]*" if hc.status == FieldStatus.UNCONFIRMED else ""
        lines.append(f"- **Has Children:** No{marker}")
        lines.append("- **Children:** N/A (no children)")
    else:
        marker = " ⚠️ *[To be confirmed]*" if hc.status == FieldStatus.UNCONFIRMED else ""
        lines.append(f"- **Has Children:** Yes{marker}")
        lines.append(f"- **Children:** {_render_value(state.children)}")
    lines.append("")

    # Section 4: Executor
    lines.append("## Executor")
    lines.append("")
    lines.append(f"- **Executor Name:** {_render_value(state.executor_name)}")
    lines.append(f"- **Relationship:** {_render_value(state.executor_relationship)}")
    lines.append("")

    # Section 5: Specific Gifts
    lines.append("## Specific Gifts")
    lines.append("")
    gifts = state.specific_gifts
    if gifts.status == FieldStatus.UNKNOWN or gifts.value is None:
        lines.append("[Not yet provided]")
    elif gifts.status == FieldStatus.UNCONFIRMED:
        if isinstance(gifts.value, list) and len(gifts.value) == 0:
            lines.append("None specified ⚠️ *[To be confirmed]*")
        elif isinstance(gifts.value, list):
            for g in gifts.value:
                lines.append(f"- {g} ⚠️ *[To be confirmed]*")
        else:
            lines.append(f"{gifts.value} ⚠️ *[To be confirmed]*")
    else:
        if isinstance(gifts.value, list) and len(gifts.value) == 0:
            lines.append("None specified")
        elif isinstance(gifts.value, list):
            for g in gifts.value:
                lines.append(f"- {g}")
        else:
            lines.append(str(gifts.value))
    lines.append("")

    # Section 6: Additional Wishes
    lines.append("## Additional Wishes")
    lines.append("")
    wishes = state.additional_wishes
    if wishes.status == FieldStatus.UNKNOWN or wishes.value is None:
        lines.append("[Not yet provided]")
    elif wishes.status == FieldStatus.UNCONFIRMED:
        if isinstance(wishes.value, list) and len(wishes.value) == 0:
            lines.append("None specified ⚠️ *[To be confirmed]*")
        elif isinstance(wishes.value, list):
            for w in wishes.value:
                lines.append(f"- {w} ⚠️ *[To be confirmed]*")
        else:
            lines.append(f"{wishes.value} ⚠️ *[To be confirmed]*")
    else:
        if isinstance(wishes.value, list) and len(wishes.value) == 0:
            lines.append("None specified")
        elif isinstance(wishes.value, list):
            for w in wishes.value:
                lines.append(f"- {w}")
        else:
            lines.append(str(wishes.value))
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("⚠️ **FICTIONAL SAMPLE: NOT LEGAL ADVICE** ⚠️")
    lines.append("---")

    return "\n".join(lines)
