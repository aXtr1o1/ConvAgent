from __future__ import annotations
import uuid


def build_chunks(parsed: dict) -> list[dict]:
    dtc_code  = parsed["dtc_code"]
    system    = parsed.get("system", "")
    desc      = parsed.get("description", "")
    reactions = parsed.get("reactions", "")
    source    = parsed.get("source_document", "")
    related   = parsed.get("related_codes", [])

    chunks = []

    # ── Parent chunk — full DTC context ──────────────────────────────
    parent_text = f"DTC {dtc_code}: {desc}"
    if reactions:
        parent_text += f"\nSystem reactions: {reactions}"
    if related:
        parent_text += f"\nRelated codes: {', '.join(related)}"
    for cause in parsed.get("causes", []):
        parent_text += f"\nPossible cause: {cause['cause']}"

    parent_chunk = _make_chunk(
        text=parent_text,
        category="dtc_explanation",
        dtc_code=dtc_code,
        system=system,
        source=source,
        related=related,
        parent_id=None,
        chunk_level="parent",
    )
    chunks.append(parent_chunk)
    parent_id = parent_chunk["chunk_id"]

    # ── Child chunks — diagnostic steps ──────────────────────────────
    for step in parsed.get("diagnostic_steps", []):
        child_text = (
            f"DTC {dtc_code} — {desc}\n"
            f"Diagnostic step {step['step_order']}: {step['question']}\n"
            f"If YES: {step.get('yes_action', '')}\n"
            f"If NO: {step.get('no_action', '')}"
        )
        chunks.append(_make_chunk(
            text=child_text,
            category="diagnostic_step",
            dtc_code=dtc_code,
            system=system,
            source=source,
            related=related,
            parent_id=parent_id,
            chunk_level="child",
        ))

    # ── Child chunks — repair actions ─────────────────────────────────
    for repair in parsed.get("repair_actions", []):
        child_text = (
            f"DTC {dtc_code} — {desc}\n"
            f"Repair action: {repair['repair']}\n"
            f"Addresses cause: {repair.get('cause_ref', '')}"
        )
        chunks.append(_make_chunk(
            text=child_text,
            category="repair_action",
            dtc_code=dtc_code,
            system=system,
            source=source,
            related=related,
            parent_id=parent_id,
            chunk_level="child",
        ))

    return chunks


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_chunk(
    text: str,
    category: str,
    dtc_code: str,
    system: str,
    source: str,
    related: list[str],
    parent_id: str | None,
    chunk_level: str,
) -> dict:
    return {
        "chunk_id":        str(uuid.uuid4()),
        "chunk_text":      text.strip(),
        "category":        category,
        "dtc_code":        dtc_code,
        "system":          system,
        "component":       _system_to_component(system),
        "source_document": source,
        "related_codes":   related,
        "parent_id":       parent_id or "",
        "chunk_level":     chunk_level,
    }


def _system_to_component(system: str) -> str:
    mapping = {
        "DPF":  "Diesel Particulate Filter",
        "EGR":  "Exhaust Gas Recirculation",
        "SCR":  "Selective Catalytic Reduction",
        "Fuel": "Fuel System",
    }
    return mapping.get(system, system)