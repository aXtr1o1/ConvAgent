from __future__ import annotations
import logging
from backend.utils.utilities import db

logger = logging.getLogger(__name__)


def write_to_structured_db(parsed: dict) -> dict:
    dtc_code = parsed["dtc_code"]
    if not dtc_code:
        raise ValueError("ParsedDocument is missing dtc_code")

    # ── 1. Upsert dtc_codes ───────────────────────────────────────────────
    existing = db.table("dtc_codes") \
        .select("*").eq("dtc_code", dtc_code).limit(1).execute()

    if existing.data:
        existing_row = existing.data[0]
        update_fields = {"source_document": parsed.get("source_document", "")}
        for field in ["system", "description", "reactions"]:
            new_val = parsed.get(field, "")
            if new_val and not existing_row.get(field):
                update_fields[field] = new_val
        for field in ["spn", "fmi"]:
            new_val = parsed.get(field)
            if new_val is not None and existing_row.get(field) is None:
                update_fields[field] = new_val
        db.table("dtc_codes").update(update_fields).eq("dtc_code", dtc_code).execute()
    else:
        db.table("dtc_codes").insert({
            "dtc_code":        dtc_code,
            "system":          parsed.get("system", ""),
            "description":     parsed.get("description", ""),
            "spn":             parsed.get("spn"),
            "fmi":             parsed.get("fmi"),
            "reactions":       parsed.get("reactions", ""),
            "source_document": parsed.get("source_document", ""),
        }).execute()
    logger.info("Upserted dtc_codes: %s", dtc_code)

    # ── 2. Merge possible_cause rows ──────────────────────────────────────
    existing_causes_resp = db.table("possible_cause") \
        .select("cause, check_point").eq("dtc_code", dtc_code).execute()
    existing_cause_names = {
        row["cause"].strip().lower()
        for row in (existing_causes_resp.data or [])
    }
    new_causes = parsed.get("causes", [])
    causes_to_insert = [
        c for c in new_causes
        if c["cause"].strip().lower() not in existing_cause_names
    ]
    if causes_to_insert:
        db.table("possible_cause").insert([
            {"dtc_code": dtc_code, "cause": c["cause"], "check_point": c.get("check_point", "")}
            for c in causes_to_insert
        ]).execute()
    total_causes = len(existing_cause_names) + len(causes_to_insert)
    logger.info("possible_cause for %s: %d existing + %d new = %d total",
                dtc_code, len(existing_cause_names), len(causes_to_insert), total_causes)

    # ── 3. Prefer-more for diagnostic_steps ──────────────────────────────
    existing_steps_resp = db.table("diagnostic_steps") \
        .select("step_order").eq("dtc_code", dtc_code).execute()
    existing_step_count = len(existing_steps_resp.data or [])
    new_steps = parsed.get("diagnostic_steps", [])

    if len(new_steps) > existing_step_count:
        db.table("diagnostic_steps").delete().eq("dtc_code", dtc_code).execute()
        if new_steps:
            db.table("diagnostic_steps").insert([
                {"dtc_code": dtc_code, "step_order": s["step_order"],
                 "question": s["question"], "yes_action": s.get("yes_action", ""),
                 "no_action": s.get("no_action", "")}
                for s in new_steps
            ]).execute()
        steps_written = len(new_steps)
        logger.info("diagnostic_steps for %s: replaced with %d steps", dtc_code, steps_written)
    else:
        steps_written = existing_step_count
        logger.info("diagnostic_steps for %s: kept %d existing steps", dtc_code, existing_step_count)

    # ── 4. Prefer-more for repair_action ─────────────────────────────────
    existing_repairs_resp = db.table("repair_action") \
        .select("repair").eq("dtc_code", dtc_code).execute()
    existing_repair_count = len(existing_repairs_resp.data or [])
    new_repairs = parsed.get("repair_actions", [])

    if len(new_repairs) > existing_repair_count:
        db.table("repair_action").delete().eq("dtc_code", dtc_code).execute()
        if new_repairs:
            db.table("repair_action").insert([
                {"dtc_code": dtc_code, "repair": r["repair"], "cause_ref": r.get("cause_ref", "")}
                for r in new_repairs
            ]).execute()
        repairs_written = len(new_repairs)
        logger.info("repair_action for %s: replaced with %d repairs", dtc_code, repairs_written)
    else:
        repairs_written = existing_repair_count
        logger.info("repair_action for %s: kept %d existing repairs", dtc_code, existing_repair_count)

    return {
        "dtc_code":        dtc_code,
        "causes_written":  total_causes,
        "steps_written":   steps_written,
        "repairs_written": repairs_written,
    }