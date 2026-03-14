from __future__ import annotations
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore


def parse_pdf(filepath: str | Path) -> dict:
    """
    Parse a DTC flowchart PDF and return a normalised ParsedDocument dict.
    Same shape as excel_parser.parse_excel() output.
    """
    if pdfplumber is None:
        raise ImportError("pdfplumber is required: pip install pdfplumber")

    path = Path(filepath)
    pages = _extract_pages(path)

    dtc_code, description = _parse_header(pages)
    causes, diagnostic_steps, repair_actions, related_codes = _parse_body(pages)

    return {
        "dtc_code":         dtc_code,
        "system":           _infer_system(description),
        "description":      description,
        "spn":              None,   # not in PDF; Excel is preferred for metadata
        "fmi":              None,
        "reactions":        "",
        "source_document":  path.name,
        "causes":           causes,
        "diagnostic_steps": diagnostic_steps,
        "repair_actions":   repair_actions,
        "related_codes":    list(set(related_codes)),
    }


# ── Internal extraction ───────────────────────────────────────────────────────

def _extract_pages(path: Path) -> list[str]:
    with pdfplumber.open(path) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]


def _parse_header(pages: list[str]) -> tuple[str, str]:
    """Extract DTC code and description from page 0."""
    header = pages[0] if pages else ""

    code_match = re.search(r'(P\d{4}-\d{2})', header)
    dtc_code = code_match.group(1) if code_match else ""

    # Description is the text after the DTC code on the first line
    lines = [l.strip() for l in header.splitlines() if l.strip()]
    description = ""
    for line in lines:
        if dtc_code and dtc_code in line:
            description = line.replace(dtc_code, "").strip().lstrip("-").strip()
            break

    return dtc_code, description


def _parse_body(pages: list[str]) -> tuple[list, list, list, list]:
    """
    Walk pages 1..N, identifying each page type by its reference code:
      PCxx_1   → cause question page
      PCxx_C   → correction / NO-action page
    """
    causes: list[dict] = []
    diagnostic_steps: list[dict] = []
    repair_actions: list[dict] = []
    related_codes: list[str] = []

    step_order = 0
    pending_cause = ""
    pending_question = ""

    for page_text in pages[1:]:
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        if not lines:
            continue

        # Skip header lines that just repeat the DTC code
        content_lines = [
            l for l in lines
            if not re.match(r'^P\d{4}-\d{2}', l)
        ]
        if not content_lines:
            continue

        page_ref = content_lines[0] if content_lines else ""

        # ── Cause question page (PCxx_1) ──────────────────────────────────
        if re.match(r'PC\d{2}_1', page_ref) or (
            len(content_lines) > 1 and
            "Press YES" in page_text and
            "Press NO" in page_text
        ):
            step_order += 1
            cause_name = content_lines[1] if len(content_lines) > 1 else ""
            question = _extract_question(content_lines)
            pending_cause = cause_name
            pending_question = question

            causes.append({
                "cause":       cause_name,
                "check_point": question,
            })
            diagnostic_steps.append({
                "step_order": step_order,
                "question":   question,
                "yes_action": "Proceed to next step",
                "no_action":  "",       # filled in by following _C page
            })

            related_codes.extend(_extract_dtc_codes(page_text))

        # ── Correction / NO-action page (PCxx_C or P01_NO_x) ─────────────
        elif re.search(r'PC\d{2}_C|P0\d_NO', page_ref):
            action_text = _extract_action(content_lines)
            if action_text:
                repair_actions.append({
                    "repair":    action_text,
                    "cause_ref": pending_cause,
                })
                # Back-fill no_action into the matching diagnostic step
                if diagnostic_steps:
                    diagnostic_steps[-1]["no_action"] = action_text

    return causes, diagnostic_steps, repair_actions, related_codes


def _extract_question(lines: list[str]) -> str:
    """Pick out the actual check instruction from a question page."""
    skip = {"Yes", "Back", "No", "Press YES if", "Press NO if"}
    for line in lines[1:]:
        if any(s in line for s in skip):
            continue
        if len(line) > 10:
            return line
    return " ".join(lines[1:3])


def _extract_action(lines: list[str]) -> str:
    """Pick the repair action text from a correction page."""
    skip = {"Yes", "Back", "No"}
    for line in lines[1:]:
        if line in skip:
            continue
        if len(line) > 3:
            return line
    return ""


def _infer_system(description: str) -> str:
    desc = description.upper()
    if "DPF" in desc:
        return "DPF"
    if "EGR" in desc:
        return "EGR"
    if "FUEL" in desc:
        return "Fuel"
    if "SCR" in desc or "DEF" in desc or "UREA" in desc:
        return "SCR"
    return "Engine"


def _extract_dtc_codes(text: str) -> list[str]:
    return re.findall(r'\bP[0-9A-F]{4}(?:-[0-9A-F]{2})?\b', text, re.IGNORECASE)
