from __future__ import annotations
import re
import pandas as pd
from pathlib import Path


def parse_excel(filepath: str | Path) -> dict:

    path = Path(filepath)
    df = pd.read_excel(path, sheet_name=0, header=0)
    df = df.where(pd.notna(df), None)

    # ── Extract header metadata from first data row ───────────────────────
    first = df.iloc[0]

    raw_code = _str(first.get("3byte Pcode") or first.get("P codes") or "")
    dtc_code = raw_code.strip()

    system = _str(first.get("Component", "")).strip().rstrip()

    description = _str(first.get("Description", "")).strip()

    spn_raw = first.get("SPN")
    spn = int(spn_raw) if spn_raw is not None else None

    fmi_raw = first.get("FMI")
    fmi = int(fmi_raw) if fmi_raw is not None else None

    reactions = _str(first.get("Reactions H6", "")).strip()

    # ── Extract causes, checkpoints, and repair actions from all rows ─────
    causes: list[dict] = []
    repair_actions: list[dict] = []
    related_codes: list[str] = []

    for _, row in df.iterrows():
        cause_text = _str(row.get("Possible causes", "")).strip()
        check_text = _str(row.get("Check Points", "")).strip()
        action_text = _str(row.get("Further Actions", "")).strip()

        if not cause_text:
            continue

        # Related DTC codes appear inside the "Primary fault codes" check point
        if "primary" in cause_text.lower() or "primary" in check_text.lower():
            related_codes.extend(_extract_dtc_codes(check_text))

        causes.append({
            "cause": cause_text,
            "check_point": check_text,
        })

        if action_text:
            repair_actions.append({
                "repair": action_text,
                "cause_ref": cause_text,
            })

    # ── Build diagnostic_steps from causes (question = check_point) ───────
    diagnostic_steps = []
    for idx, c in enumerate(causes):
        if not c["check_point"]:
            continue
        repair = next(
            (r["repair"] for r in repair_actions if r["cause_ref"] == c["cause"]),
            None,
        )
        diagnostic_steps.append({
            "step_order": idx + 1,
            "question":   c["check_point"],
            "yes_action": "Proceed to next step",
            "no_action":  repair or "Rectify and re-test",
        })

    return {
        "dtc_code":         dtc_code,
        "system":           system,
        "description":      description,
        "spn":              spn,
        "fmi":              fmi,
        "reactions":        reactions,
        "source_document":  path.name,
        "causes":           causes,
        "diagnostic_steps": diagnostic_steps,
        "repair_actions":   repair_actions,
        "related_codes":    list(set(related_codes)),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _str(val) -> str:
    if val is None:
        return ""
    return str(val)


def _extract_dtc_codes(text: str) -> list[str]:
    """Pull DTC-style codes (e.g. P2459-00, P24A2) from free text."""
    return re.findall(r'\bP[0-9A-F]{4}(?:-[0-9A-F]{2})?\b', text, re.IGNORECASE)
