from __future__ import annotations
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def merge_parsed_documents(docs: list[dict]) -> list[dict]:

    # Group by normalised DTC code
    groups: dict[str, list[dict]] = defaultdict(list)
    for doc in docs:
        key = _normalise_dtc(doc.get("dtc_code", ""))
        if key:
            groups[key].append(doc)
        else:
            logger.warning("Skipping document with no DTC code: %s",
                           doc.get("source_document", "unknown"))

    merged = []
    for dtc_code, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
            logger.info("DTC %s — single source: %s",
                        dtc_code, group[0].get("source_document"))
        else:
            merged_doc = _merge_group(dtc_code, group)
            merged.append(merged_doc)
            sources = [d.get("source_document", "?") for d in group]
            logger.info("DTC %s — merged %d sources: %s",
                        dtc_code, len(group), " + ".join(sources))

    return merged


def _merge_group(dtc_code: str, docs: list[dict]) -> dict:
    """Merge a list of docs that all share the same DTC code."""

    # Sort: Excel first (has richer metadata), PDF second
    docs = _sort_excel_first(docs)

    # ── Scalar fields — first non-empty wins ─────────────────────────────
    system      = _first_nonempty(docs, "system")
    description = _first_nonempty(docs, "description")
    reactions   = _first_nonempty(docs, "reactions")
    spn         = _first_not_none(docs, "spn")
    fmi         = _first_not_none(docs, "fmi")

    # ── source_document — join all ────────────────────────────────────────
    sources = [d.get("source_document", "") for d in docs if d.get("source_document")]
    source_document = " + ".join(sources)

    # ── causes — union by normalised cause text ───────────────────────────
    seen_causes: set[str] = set()
    merged_causes: list[dict] = []
    for doc in docs:
        for cause in doc.get("causes", []):
            key = _normalise_text(cause.get("cause", ""))
            if key and key not in seen_causes:
                seen_causes.add(key)
                merged_causes.append(cause)

    # ── diagnostic_steps — prefer source with most steps ─────────────────
    all_steps = [doc.get("diagnostic_steps", []) for doc in docs]
    merged_steps = max(all_steps, key=len) if all_steps else []

    # ── repair_actions — prefer source with most repairs ─────────────────
    all_repairs = [doc.get("repair_actions", []) for doc in docs]
    merged_repairs = max(all_repairs, key=len) if all_repairs else []

    # ── related_codes — union, deduplicated ──────────────────────────────
    seen_codes: set[str] = set()
    merged_related: list[str] = []
    for doc in docs:
        for code in doc.get("related_codes", []):
            normalised = code.strip().upper()
            if normalised not in seen_codes:
                seen_codes.add(normalised)
                merged_related.append(normalised)

    return {
        "dtc_code":         dtc_code,
        "system":           system,
        "description":      description,
        "spn":              spn,
        "fmi":              fmi,
        "reactions":        reactions,
        "source_document":  source_document,
        "causes":           merged_causes,
        "diagnostic_steps": merged_steps,
        "repair_actions":   merged_repairs,
        "related_codes":    merged_related,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_dtc(code: str) -> str:
    """Normalise DTC code — strip suffix so P2463 matches P2463-00."""
    return code.strip().upper().split("-")[0] if code else ""


def _normalise_text(text: str) -> str:
    """Lowercase, strip whitespace for deduplication comparison."""
    return " ".join(text.lower().split())


def _first_nonempty(docs: list[dict], field: str) -> str:
    for doc in docs:
        val = doc.get(field, "")
        if val:
            return val
    return ""


def _first_not_none(docs: list[dict], field: str):
    for doc in docs:
        val = doc.get(field)
        if val is not None:
            return val
    return None


def _sort_excel_first(docs: list[dict]) -> list[dict]:
    """Sort so Excel files come before PDFs — Excel has richer metadata."""
    def _key(doc):
        src = doc.get("source_document", "").lower()
        if src.endswith(".xlsx") or src.endswith(".xls"):
            return 0
        return 1
    return sorted(docs, key=_key)
