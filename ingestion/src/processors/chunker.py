from __future__ import annotations


def build_chunks(parsed: dict) -> list[dict]:

    dtc_code   = parsed["dtc_code"]
    system     = parsed.get("system", "")
    desc       = parsed.get("description", "")
    reactions  = parsed.get("reactions", "")
    source     = parsed.get("source_document", "")
    related    = parsed.get("related_codes", [])

    chunks: list[dict] = []

    # ── 1. DTC Explanation chunk ──────────────────────────────────────────
    explanation_parts = [f"DTC {dtc_code}: {desc}"]
    if reactions:
        explanation_parts.append(f"System reactions: {reactions}")
    if related:
        explanation_parts.append(f"Related codes: {', '.join(related)}")

    chunks.append(_make_chunk(
        text="\n".join(explanation_parts),
        category="dtc_explanation",
        dtc_code=dtc_code,
        system=system,
        source=source,
        related=related,
    ))

    # ── 2. Possible cause chunks ──────────────────────────────────────────
    for cause in parsed.get("causes", []):
        parts = [
            f"DTC {dtc_code} — Possible cause: {cause['cause']}",
        ]
        if cause.get("check_point"):
            parts.append(f"Diagnostic check: {cause['check_point']}")

        chunks.append(_make_chunk(
            text="\n".join(parts),
            category="possible_cause",
            dtc_code=dtc_code,
            system=system,
            source=source,
            related=related,
        ))

    # ── 3. Diagnostic step chunks ─────────────────────────────────────────
    for step in parsed.get("diagnostic_steps", []):
        parts = [
            f"DTC {dtc_code} — Diagnostic step {step['step_order']}:",
            f"Check: {step['question']}",
        ]
        if step.get("yes_action"):
            parts.append(f"If YES (pass): {step['yes_action']}")
        if step.get("no_action"):
            parts.append(f"If NO (fail): {step['no_action']}")

        chunks.append(_make_chunk(
            text="\n".join(parts),
            category="diagnostic_step",
            dtc_code=dtc_code,
            system=system,
            source=source,
            related=related,
        ))

    # ── 4. Repair action chunks ───────────────────────────────────────────
    for repair in parsed.get("repair_actions", []):
        parts = [f"DTC {dtc_code} — Repair action: {repair['repair']}"]
        if repair.get("cause_ref"):
            parts.append(f"Addresses cause: {repair['cause_ref']}")

        chunks.append(_make_chunk(
            text="\n".join(parts),
            category="repair_action",
            dtc_code=dtc_code,
            system=system,
            source=source,
            related=related,
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
) -> dict:
    return {
        "chunk_text":      text.strip(),
        "category":        category,
        "dtc_code":        dtc_code,
        "system":          system,
        "component":       _system_to_component(system),
        "source_document": source,
        "related_codes":   related,
    }


def _system_to_component(system: str) -> str:
    mapping = {
        "DPF":  "Diesel Particulate Filter",
        "EGR":  "Exhaust Gas Recirculation",
        "SCR":  "Selective Catalytic Reduction",
        "Fuel": "Fuel System",
    }
    return mapping.get(system, system)
