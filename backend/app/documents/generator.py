"""Document generator: pure function of state → markdown string."""

from __future__ import annotations
from typing import Any

from app.models.document import DocumentState, FieldValue, ChildrenState, ExecutorState

def _render_value(field: FieldValue, fallback: str = "[Not yet provided]") -> str:
    if field.status in ("missing", "unknown") or field.value is None:
        if field.status == "not_applicable":
            return "N/A"
        return fallback
    if field.status == "unconfirmed":
        return f"{field.value} ⚠️ *[To be confirmed]*"
    return str(field.value)

def _render_children(children: ChildrenState) -> str:
    if children.status in ("missing", "unknown"):
        return "[Not yet provided]"
    if children.status == "not_applicable" or children.has_children is False:
        return "N/A (no children)"
    
    parts = []
    if children.expected_count is not None:
        parts.append(f"{children.expected_count} expected")
    if children.names:
        parts.append("Names: " + ", ".join(children.names))
    
    if not parts:
        return "Yes, but details not provided"
    
    res = " — ".join(parts)
    if children.status == "unconfirmed":
        return f"{res} ⚠️ *[To be confirmed]*"
    return res

def _render_executor(executor: ExecutorState) -> str:
    if executor.status in ("missing", "unknown"):
        return "[Not yet provided]"
    if executor.status == "not_decided":
        return "Not decided yet"
    if executor.status == "declined":
        return "Declined to provide"
        
    parts = []
    if executor.names:
        parts.append(", ".join(executor.names))
    if executor.relationship:
        parts.append(f"({executor.relationship})")
        
    res = " ".join(parts)
    if executor.status == "unconfirmed":
        return f"{res} ⚠️ *[To be confirmed]*"
    return res

def generate_document(state: DocumentState) -> str:
    """Generate the Personal Wishes Document as markdown."""
    lines: list[str] = []

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
    ca = state.covers_worldwide_assets
    if ca.status in ("missing", "unknown") or not ca.value:
        lines.append("- **Assets Covered:** [Not yet provided]")
    elif ca.value == "worldwide":
        marker = " ⚠️ *[To be confirmed]*" if ca.status == "unconfirmed" else ""
        lines.append(f"- **Assets Covered:** Worldwide assets (properties, bank accounts, investments, etc.){marker}")
    else:
        marker = " ⚠️ *[To be confirmed]*" if ca.status == "unconfirmed" else ""
        lines.append(f"- **Assets Covered:** Specific assets only: {ca.value}{marker}")
    lines.append("")

    # Section 3: Family and Children
    lines.append("## Family and Children")
    lines.append("")
    lines.append(f"- **Children:** {_render_children(state.children)}")
    lines.append("")

    # Section 4: Executor
    lines.append("## Executor")
    lines.append("")
    lines.append(f"- **Executor:** {_render_executor(state.executor)}")
    lines.append("")

    # Section 5: Specific Gifts
    lines.append("## Specific Gifts")
    lines.append("")
    lines.append(f"- **Gifts:** {_render_value(state.specific_gifts)}")
    lines.append("")

    # Section 6: Additional Wishes
    lines.append("## Additional Wishes")
    lines.append("")
    lines.append(f"- **Additional Wishes:** {_render_value(state.additional_wishes)}")
    lines.append("")

    return "\n".join(lines)
