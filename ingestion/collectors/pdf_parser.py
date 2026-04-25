from __future__ import annotations
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def parse_pdf(filepath: str | Path) -> dict:
    if pdfplumber is None:
        raise ImportError("pdfplumber is required: pip install pdfplumber")

    path = Path(filepath)
    pages = _extract_pages(path)
    full_text = "\n".join(pages)

    dtc_code, description   = _parse_header(full_text)
    reactions               = _parse_reactions(full_text)
    causes                  = _parse_causes(full_text)
    related_codes           = _parse_related_codes(full_text, dtc_code)
    diagnostic_steps, repair_actions = _parse_steps(full_text, dtc_code, description)

    return {
        "dtc_code":         dtc_code,
        "system":           _infer_system(full_text[:500]),
        "description":      description,
        "spn":              None,
        "fmi":              None,
        "reactions":        reactions,
        "source_document":  path.name,
        "causes":           causes,
        "diagnostic_steps": diagnostic_steps,
        "repair_actions":   repair_actions,
        "related_codes":    related_codes,
    }


# ── Page extractor ────────────────────────────────────────────────────────────

def _extract_pages(path: Path) -> list[str]:
    with pdfplumber.open(path) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


# ── Header: DTC code + description ───────────────────────────────────────────

def _parse_header(full_text: str) -> tuple[str, str]:
    # DTC code e.g. P2463-00
    code_match = re.search(
        r'\bDTC\s+(P[0-9A-Fa-f]{4}(?:-[0-9A-Fa-f]{2})?)\b',
        full_text
    )
    if not code_match:
        code_match = re.search(
            r'\b(P[0-9A-Fa-f]{4}-[0-9A-Fa-f]{2})\b',
            full_text
        )
    dtc_code = code_match.group(1).upper() if code_match else ""

    # Description from "DTC Description <text>" line
    desc_match = re.search(
        r'DTC Description\s+(.+?)(?:\n|Possible Causes)',
        full_text,
        re.IGNORECASE | re.DOTALL
    )
    description = ""
    if desc_match:
        description = re.sub(r'\s+', ' ', desc_match.group(1)).strip()

    return dtc_code, description


# ── Reactions / Primary Impact ────────────────────────────────────────────────

def _parse_reactions(full_text: str) -> str:
    match = re.search(
        r'Primary Impact\s+(.*?)(?=\nIMPORTANT|\n\n[A-Z]|\Z)',
        full_text,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        return re.sub(r'\s+', ' ', match.group(1)).strip()
    return ""


# ── Possible causes ───────────────────────────────────────────────────────────

def _parse_causes(full_text: str) -> list[dict]:
    causes = []
    match = re.search(
        r'Possible Causes\s*(.*?)(?=System Category|Primary Impact)',
        full_text,
        re.IGNORECASE | re.DOTALL
    )
    if not match:
        return causes

    block = match.group(1)
    for line in block.splitlines():
        line = line.strip().lstrip("•").strip()
        if line and len(line) > 3:
            causes.append({
                "cause":       line,
                "check_point": "",
            })
    return causes


# ── Related DTC codes ─────────────────────────────────────────────────────────

def _parse_related_codes(full_text: str, main_dtc: str) -> list[str]:
    all_codes = re.findall(
        r'\b(P[0-9A-Fa-f]{4}(?:-[0-9A-Fa-f]{2})?)\b',
        full_text,
        re.IGNORECASE
    )
    main_base = main_dtc.split("-")[0].upper()
    seen = set()
    related = []
    for c in all_codes:
        c = c.upper()
        base = c.split("-")[0]
        if base != main_base and c not in seen:
            seen.add(c)
            related.append(c)
    return related


# ── Diagnostic steps ──────────────────────────────────────────────────────────

def _parse_steps(
    full_text: str,
    dtc_code: str,
    description: str,
) -> tuple[list[dict], list[dict]]:

    diagnostic_steps = []
    repair_actions   = []

    step_pattern = re.compile(
        r'Step\s+(\d+)\s*[—–-]+\s*([^\n]+)\n'
        r'(.*?)'
        r'(?=Step\s+\d+\s*[—–-]|\Z)',
        re.DOTALL
    )

    for match in step_pattern.finditer(full_text):
        step_num   = int(match.group(1))
        step_title = match.group(2).strip()
        body       = match.group(3)

        # ── Expected Result ───────────────────────────────────────────
        expected_match = re.search(
            r'Expected\s*Result\s+(.*?)(?=Next Action|If Fault|If Voltage|'
            r'If Ground|If Open|If Short|If Hose|If Blockage|Step\s+\d+|\Z)',
            body,
            re.DOTALL | re.IGNORECASE
        )
        expected = ""
        if expected_match:
            expected = re.sub(r'\s+', ' ', expected_match.group(1)).strip()
            # Clean page footers from expected text
            expected = re.sub(
                r'\d+\s*-\s*www\.\S+\s*(?:AXTR LABS.*?(?=\n|$))?', 
                '', expected, flags=re.IGNORECASE
            ).strip()

        # ── Repair / fault action ─────────────────────────────────────
        # Only capture lines that describe actual repair actions
        # Skip "Next Action" lines that just say "proceed to Step-X"
        repair_match = re.search(
            r'(?:If Fault Found|If Voltage Absent or Low|'
            r'If Ground Fault Found|If Open Circuit|'
            r'If Short to Ground Found|If Short to B\+\s*Found|'
            r'If Hose Blockage Found|If Blockage Was Found and Cleared)'
            r'\s+(.*?)(?=Step\s+\d+|Expected Result|\Z)',
            body,
            re.DOTALL | re.IGNORECASE
        )
        repair = ""
        if repair_match:
            repair = re.sub(r'\s+', ' ', repair_match.group(1)).strip()
            # Clean page footers
            repair = re.sub(
                r'\d+\s*-\s*www\.\S+.*', 
                '', repair, flags=re.IGNORECASE
            ).strip()

        yes_action = expected if expected else "Proceed to next step"
        no_action  = repair   if repair   else ""

        diagnostic_steps.append({
            "step_order": step_num,
            "question":   step_title,
            "yes_action": yes_action,
            "no_action":  no_action,
        })

        # Only add to repair_actions if it's a real repair instruction
        if repair and len(repair) > 20:
            repair_actions.append({
                "repair":    repair,
                "cause_ref": step_title,
            })

    # Deduplicate by step_order — keep first occurrence
    seen: set[int] = set()
    unique_steps = []
    for s in diagnostic_steps:
        if s["step_order"] not in seen:
            seen.add(s["step_order"])
            unique_steps.append(s)

    return unique_steps, repair_actions


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_system(text: str) -> str:
    text = text.upper()
    if "DPF" in text:
        return "DPF"
    if "EGR" in text:
        return "EGR"
    if "FUEL" in text:
        return "Fuel"
    if "SCR" in text or "DEF" in text or "UREA" in text:
        return "SCR"
    return "Engine"