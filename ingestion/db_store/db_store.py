from __future__ import annotations
import json
import logging
from backend.utils.utilities import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s"
)
logger = logging.getLogger(__name__)


def load_json(filepath: str) -> list | dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_dtc(code: str) -> str:
    return code.strip().upper()


def clear_existing(dtc_code: str):
    """Clear existing data for this DTC code — child tables first."""
    logger.info("Clearing existing data for DTC: %s", dtc_code)
    db.table("diagnostic_steps").delete().eq("dtc_code", dtc_code).execute()
    logger.info("  ✅ diagnostic_steps cleared")
    db.table("repair_action").delete().eq("dtc_code", dtc_code).execute()
    logger.info("  ✅ repair_action cleared")
    db.table("possible_cause").delete().eq("dtc_code", dtc_code).execute()
    logger.info("  ✅ possible_cause cleared")
    db.table("dtc_codes").delete().eq("dtc_code", dtc_code).execute()
    logger.info("  ✅ dtc_codes cleared")


def insert_dtc_codes(records: list[dict]) -> int:
    if not records:
        logger.info("No dtc_codes to insert")
        return 0

    rows = []
    seen: set[str] = set()
    for r in records:
        dtc_code = r.get("dtc_code", "").strip().upper()
        if not dtc_code or dtc_code in seen:
            continue
        seen.add(dtc_code)
        rows.append({
            "dtc_code":        dtc_code,
            "system":          r.get("system", "") or "",
            "description":     r.get("description", "") or "",
            "spn":             r.get("spn") if isinstance(r.get("spn"), int) else None,
            "fmi":             r.get("fmi") if isinstance(r.get("fmi"), int) else None,
            "reactions":       r.get("reactions", "") or "",
            "important_note":  r.get("important_note", "") or "",
            "source_document": r.get("source_document", "") or "",
        })

    if rows:
        db.table("dtc_codes").upsert(rows, on_conflict="dtc_code").execute()
        logger.info("✅ Upserted %d rows into dtc_codes", len(rows))

    return len(rows)

def insert_diagnostic_steps(records: list[dict]) -> int:
    if not records:
        logger.info("No diagnostic_steps to insert")
        return 0

    rows = []
    for r in records:
        dtc_code = r.get("dtc_code", "").strip().upper()
        question = r.get("question", "").strip()
        if not dtc_code or not question:
            logger.warning("Skipping step — missing dtc_code or question")
            continue

        # ── step_code must be None if empty — has unique constraint ──────
        step_code = r.get("step_code", "")
        step_code = step_code.strip() if step_code else ""
        step_code = step_code if step_code else None  # empty string → None

        # ── flow_type same treatment ──────────────────────────────────────
        flow_type = r.get("flow_type", "")
        flow_type = flow_type.strip() if flow_type else ""
        flow_type = flow_type if flow_type else None

        rows.append({
            "dtc_code":         dtc_code,
            "step_order":       r.get("step_order") if isinstance(r.get("step_order"), int) else None,
            "question":         question,
            "yes_action":       r.get("yes_action", "") or "",
            "no_action":        r.get("no_action", "") or "",
            "details":          r.get("details", "") or "",
            "expected_result":  r.get("expected_result", "") or "",
            "next_step_if_yes": r.get("next_step_if_yes", "") or "",
            "next_step_if_no":  r.get("next_step_if_no", "") or "",
            "step_code":        step_code,   # ← None if empty
            "flow_type":        flow_type,   # ← None if empty
        })

    if rows:
        db.table("diagnostic_steps").insert(rows).execute()
        logger.info("✅ Inserted %d rows into diagnostic_steps", len(rows))

    return len(rows)


def insert_possible_cause(records: list[dict]) -> int:
    if not records:
        logger.info("No possible_cause to insert")
        return 0

    rows = []
    for r in records:
        dtc_code = r.get("dtc_code", "").strip().upper()
        cause    = r.get("cause", "").strip()
        if not dtc_code or not cause:
            continue
        rows.append({
            "dtc_code":    dtc_code,
            "cause":       cause,
            "check_point": r.get("check_point", "") or "",
        })

    if rows:
        db.table("possible_cause").insert(rows).execute()
        logger.info("✅ Inserted %d rows into possible_cause", len(rows))

    return len(rows)


def insert_repair_action(records: list[dict]) -> int:
    if not records:
        logger.info("No repair_action to insert")
        return 0

    rows = []
    for r in records:
        dtc_code = r.get("dtc_code", "").strip().upper()
        repair   = r.get("repair", "").strip()
        if not dtc_code or not repair:
            continue
        rows.append({
            "dtc_code":         dtc_code,
            "repair":           repair,
            "cause_ref":        r.get("cause_ref", "") or "",
            "additional_notes": r.get("additional_notes", "") or "",
        })

    if rows:
        db.table("repair_action").insert(rows).execute()
        logger.info("✅ Inserted %d rows into repair_action", len(rows))

    return len(rows)


def store_json_to_supabase(
    steps_filepath: str,
    dtc_filepath: str = None,
    causes_filepath: str = None,
    repairs_filepath: str = None,
    clear_first: bool = True,
):
    """
    Stores JSON data into Supabase.

    steps_filepath:  path to diagnostic steps JSON (flat list)
    dtc_filepath:    path to dtc_codes JSON (optional separate file)
    causes_filepath: path to possible_cause JSON (optional separate file)
    repairs_filepath: path to repair_action JSON (optional separate file)
    """

    # ── Load diagnostic steps ─────────────────────────────────────────────
    logger.info("Loading diagnostic steps from: %s", steps_filepath)
    steps_data = load_json(steps_filepath)

    # Steps file is a flat list
    if isinstance(steps_data, list):
        diagnostic_steps = steps_data
    elif isinstance(steps_data, dict):
        diagnostic_steps = steps_data.get("diagnostic_steps", [])
    else:
        diagnostic_steps = []

    # ── Load other files if provided ──────────────────────────────────────
    dtc_codes       = []
    possible_causes = []
    repair_actions  = []

    if dtc_filepath:
        dtc_data = load_json(dtc_filepath)
        dtc_codes = dtc_data if isinstance(dtc_data, list) else dtc_data.get("dtc_codes", [])

    if causes_filepath:
        causes_data = load_json(causes_filepath)
        possible_causes = causes_data if isinstance(causes_data, list) else causes_data.get("possible_cause", [])

    if repairs_filepath:
        repairs_data = load_json(repairs_filepath)
        repair_actions = repairs_data if isinstance(repairs_data, list) else repairs_data.get("repair_action", [])

    # ── Normalize all DTC codes ───────────────────────────────────────────
    all_records = diagnostic_steps + dtc_codes + possible_causes + repair_actions
    for r in all_records:
        if r.get("dtc_code"):
            r["dtc_code"] = _normalize_dtc(r["dtc_code"])

    # ── Extract unique DTC codes from steps if no dtc file provided ───────
    if not dtc_codes:
        seen_dtc: set[str] = set()
        for r in diagnostic_steps:
            code = r.get("dtc_code", "").strip().upper()
            if code and code not in seen_dtc:
                seen_dtc.add(code)
                dtc_codes.append({
                    "dtc_code":        code,
                    "system":          "",
                    "description":     "",
                    "reactions":       "",
                    "important_note":  "",
                    "source_document": steps_filepath,
                })

    logger.info(
        "Found: %d dtc_codes | %d causes | %d steps | %d repairs",
        len(dtc_codes),
        len(possible_causes),
        len(diagnostic_steps),
        len(repair_actions),
    )

    # ── Clear existing data ───────────────────────────────────────────────
    if clear_first:
        all_codes: set[str] = set()
        for r in dtc_codes + diagnostic_steps + possible_causes + repair_actions:
            code = r.get("dtc_code", "").strip().upper()
            if code:
                all_codes.add(code)
        for code in all_codes:
            clear_existing(code)

    # ── Insert in correct order ───────────────────────────────────────────
    logger.info("=" * 50)
    logger.info("INSERTING INTO SUPABASE")
    logger.info("=" * 50)

    dtc_count     = insert_dtc_codes(dtc_codes)
    cause_count   = insert_possible_cause(possible_causes)
    steps_count   = insert_diagnostic_steps(diagnostic_steps)
    repairs_count = insert_repair_action(repair_actions)

    logger.info("=" * 50)
    logger.info("INGESTION COMPLETE")
    logger.info("  dtc_codes:         %d rows", dtc_count)
    logger.info("  possible_cause:    %d rows", cause_count)
    logger.info("  diagnostic_steps:  %d rows", steps_count)
    logger.info("  repair_action:     %d rows", repairs_count)
    logger.info("=" * 50)

    return {
        "status":           "success",
        "dtc_codes":        dtc_count,
        "possible_cause":   cause_count,
        "diagnostic_steps": steps_count,
        "repair_action":    repairs_count,
    }


if __name__ == "__main__":
    import sys

    # ── Run with just the steps file ──────────────────────────────────────
    # It will auto-create dtc_codes entries from the DTC codes found in steps
    steps_file = sys.argv[1] if len(sys.argv) > 1 else "supabase_ready.json"
    dtc_file   = sys.argv[2] if len(sys.argv) > 2 else None

    result = store_json_to_supabase(
        steps_filepath=steps_file,
        dtc_filepath=dtc_file,
        clear_first=True
    )
    print(json.dumps(result, indent=2))