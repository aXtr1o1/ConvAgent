from __future__ import annotations
import fitz
import re
import json
import logging
from typing import List, Dict

# Optional LLM (safe usage only)
from config import client
openai_client = client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAIN_DTC = "P2463-00"

PRIMARY_DTCS = [
    "P245E-11",
    "P2452-12",
    "P245E-1F",
    "P1194-00",
    "P2459-00",
    "P1629-00"
]

# ==============================
# PDF TEXT EXTRACTION
# ==============================
def extract_pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc if page.get_text())


# ==============================
# EXTRACT DTC BLOCKS
# ==============================
def extract_dtc_blocks(text: str) -> List[Dict]:
    pattern = r'(P\d{4}(?:-[0-9A-F]{2})?.*?)(?=P\d{4}(?:-[0-9A-F]{2})?|$)'
    matches = re.findall(pattern, text, re.S)

    dtcs = []

    for block in matches:
        dtc_match = re.search(r'(P\d{4}(?:-[0-9A-F]{2})?)', block)
        if not dtc_match:
            continue

        dtc = dtc_match.group(1)

        dtcs.append({
            "dtc_code": dtc,
            "raw_text": block
        })

    logger.info(f"Found DTCs: {[d['dtc_code'] for d in dtcs]}")
    return dtcs


# ==============================
# EXTRACT STEPS FROM EACH DTC
# ==============================
def extract_steps(dtc_code: str, text: str) -> List[Dict]:
    step_pattern = r'(Step\s+\d+\s+—.*?)(?=Step\s+\d+\s+—|$)'
    steps = re.findall(step_pattern, text, re.S)

    structured_steps = []

    for i, step in enumerate(steps, start=1):

        expected = ""
        yes_action = "Proceed to next step"
        no_action = ""

        # Extract expected result
        expected_match = re.search(r'Expected Result(.*?)(?=If|Step|$)', step, re.S)
        if expected_match:
            expected = expected_match.group(1).strip()

        # Extract failure action
        if_match = re.search(r'(If .*?)(?=Step|$)', step, re.S)
        if if_match:
            no_action = if_match.group(1).strip()

        structured_steps.append({
            "dtc_code": dtc_code,
            "step_order": i,
            "question": step.split("\n")[0].strip(),
            "details": step.strip(),
            "expected_result": expected,
            "yes_action": yes_action,
            "no_action": no_action,
            "next_step_if_yes": f"{dtc_code}_STEP_{i+1}" if i < len(steps) else "END",
            "next_step_if_no": "END"
        })

    return structured_steps


# ==============================
# PRIMARY FLOW (CRITICAL)
# ==============================
def build_primary_flow(main_dtc: str) -> List[Dict]:
    steps = []

    for i, code in enumerate(PRIMARY_DTCS, start=1):
        steps.append({
            "dtc_code": main_dtc,
            "step_order": i,
            "question": f"Is primary DTC {code} active?",
            "details": f"Check if {code} is present using scan tool",
            "expected_result": f"{code} should be either active or inactive",
            "yes_action": f"Diagnose {code} before continuing",
            "no_action": "Check next primary DTC",
            "next_step_if_yes": f"{code}_STEP_1",
            "next_step_if_no": f"{main_dtc}_PRIMARY_{i+1}" if i < len(PRIMARY_DTCS) else f"{main_dtc}_MAIN_START"
        })

    return steps


# ==============================
# OPTIONAL LLM CLEANUP (SAFE)
# ==============================
def enrich_with_llm(step: Dict) -> Dict:
    try:
        prompt = f"""
Clean and refine this diagnostic step. DO NOT change meaning.

Return JSON:
{{
  "question": "...",
  "yes_action": "...",
  "no_action": "..."
}}

INPUT:
{json.dumps(step)}
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}]
        )

        cleaned = json.loads(response.choices[0].message.content)

        step.update(cleaned)

    except Exception as e:
        logger.warning(f"LLM skipped: {e}")

    return step


# ==============================
# TRANSFORM TO SUPABASE FORMAT
# ==============================
def transform_to_supabase(all_steps: List[Dict]) -> List[Dict]:
    supabase_steps = []

    for s in all_steps:
        supabase_steps.append({
            "dtc_code": s.get("dtc_code", "UNKNOWN"),
            "step_order": s.get("step_order", 0),
            "question": s.get("question", ""),
            "yes_action": s.get("yes_action"),
            "no_action": s.get("no_action"),
            "details": s.get("details"),
            "expected_result": s.get("expected_result"),
            "next_step_if_yes": s.get("next_step_if_yes"),
            "next_step_if_no": s.get("next_step_if_no")
        })

    return supabase_steps


# ==============================
# MAIN PIPELINE
# ==============================
def run_pipeline(pdf_path: str):

    text = extract_pdf_text(pdf_path)

    dtc_blocks = extract_dtc_blocks(text)

    all_steps = []

    for dtc in dtc_blocks:
        code = dtc["dtc_code"]
        raw = dtc["raw_text"]

        logger.info(f"Processing {code}")

        steps = extract_steps(code, raw)

        # OPTIONAL: clean steps via LLM
        # steps = [enrich_with_llm(s) for s in steps]

        all_steps.extend(steps)

    # 🔥 ADD PRIMARY FLOW FIRST
    primary_flow = build_primary_flow(MAIN_DTC)

    final_steps = primary_flow + all_steps

    final_data = transform_to_supabase(final_steps)

    # SAVE
    with open("supabase_ready.json", "w") as f:
        json.dump(final_data, f, indent=2)

    logger.info("✅ Pipeline Complete")


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    run_pipeline("C:\\Users\\Manoj Menon\\OneDrive\\Documents\\aXtrLabs\\ConvAgent\\ingestion\\knowledge_base\\DCT-P2463-KowledgeBase_Updated.pdf")