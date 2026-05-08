from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
import logging
from config import azure_deployment
from backend.utils.utilities import openai_client as client
from concurrent.futures import ThreadPoolExecutor
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



PROMPT = """
You are a diagnostic document parser.

Convert the given content into structured JSON.

{
  "dtcs": [
    {
      "code": "string",
      "steps": [
        {
          "step_number": integer,
          "title": "string",
          "instructions": "string",
          "expected_result": "string",
          "next_action": "string or object"
        }
      ]
    }
  ]
}
Rules:
- Preserve ALL technical details
- Extract DTC → Sub-DTC → Steps
- Each Step must include:
  - step_number
  - title
  - instructions
  - expected_result
  - next_action
- DO NOT summarize
- DO NOT skip content

Return ONLY JSON.
"""

def iter_block_items(parent):
    for child in parent.element.body.iterchildren():
        if child.tag.endswith('p'):
            yield Paragraph(child, parent)
        elif child.tag.endswith('tbl'):
            yield Table(child, parent)
        

def parse_docs(filepath):
    doc = Document(filepath)

    blocks = []


    for block in iter_block_items(doc):

        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                blocks.append({
                    "type":"paragraph",
                    "content":text,
                })
        elif isinstance(block, Table):
            table_data = []
            for row in block.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                table_data.append(row_data)
            blocks.append(
                {
                    "type":"table",
                    "content":table_data,
                }
            )
    logger.info(f"Parsed {len(blocks)} blocks from {filepath}")
    return blocks

def table_to_text(table):
    lines = []

    headers = table[0]

    for row in table[1:]:
        row_text = ", ".join(f"{h} : {v}" for h,v in zip(headers, row))
        lines.append(row_text)
    return "\n".join(lines)

def build_llm_blocks(blocks, max_chars = 3000):

    merged = []
    current = ""
    current_raw_blocks = []
    dtc_pattern = re.compile(r"(DTC\s+)?[A-Z]{1,2}\d{3,4}(-\d{2})?")

    for block in blocks:
        text = block["content"] if block["type"] == "paragraph" else table_to_text(block["content"])
        
        if dtc_pattern.search(text) and len(current) > 0:
            merged.append({"llm_input":current, "raw_blocks":current_raw_blocks})
            current = text
            current_raw_blocks = [text]
        elif len(current) + len(text) < max_chars:
            current += "\n" + text
            current_raw_blocks.append(text)
        else:
            merged.append({
                "llm_input": current.strip(),
                "raw_blocks": current_raw_blocks.copy()
            })
            current = text
            current_raw_blocks = [text]
    if current:
        merged.append({
            "llm_input": current.strip(),
            "raw_blocks": current_raw_blocks.copy()
        })
    return merged



def process_block(text):
    try:
        res  = client.chat.completions.create(
            model = azure_deployment,
            messages = [
                {
                    "role": "system",
                    "content": PROMPT
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            response_format = {"type":"json_object"}
        )
        return res.choices[0].message.content
    except Exception as e:
        logger.error(f"Error processing block: {e}")
        return "{}"

def process_all(blocks):
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        for b in blocks:
            future = executor.submit(process_block, b["llm_input"])
            futures.append((future, b))  # ✅ store tuple manually

        for future, block in futures:
            results.append({
                "llm_output": future.result(),
                "raw_blocks": block["raw_blocks"]
            })

    return results
def merge_results(results):
    dtc_maps = {}


    for r in results:
        try:
            raw_text = "\n".join(r["raw_blocks"])
            data = json.loads(r["llm_output"])
            normalized = normalize_llm_output(data)

            for dtc in normalized:
                code = dtc["code"]
                if code not in dtc_maps:
                    dtc_maps[code] = {
                        "code":code,
                        "steps":[]
                    }
                dtc_maps[code]["steps"].extend( {
        **step,
        "raw_text": raw_text
    }
    for step in dtc["steps"] )
        except Exception as e:
            logger.error(f"Error processing result: {e}")
    for dtc in dtc_maps.values():
        dtc["steps"] = sorted(dtc["steps"], key=lambda x: x["step_number"])
    return {"dtcs":list(dtc_maps.values())}
def validate_steps(data):
    for dtc in data.get("dtcs",[]):
        if not isinstance(dtc, dict):
            continue
        for step in dtc.get("steps",[]):
            if not step.get("expected_result"):
                logger.warning(f"Missing expected result in step {step}")

def normalize_llm_output(data):
    normalized = []
    dtcs = data.get("dtcs",[])

    for dtc in dtcs:
        code = dtc.get("code","").strip()
        if not code or code.lower() in ["string", "dtc-xxxx", "dtcxxx", "dtc1234"]:
            continue
        steps = dtc.get("steps",[])
        clean_steps = []
        for step in steps:
            if not step.get("step_number"):
                continue
            clean_steps.append({
                "step_number": step.get("step_number"),
                "title": step.get("title", "").strip(),
                "instructions": step.get("instructions", "").strip(),
                "expected_result": step.get("expected_result", "").strip(),
                "next_action": step.get("next_action")
            })
        if clean_steps:
            normalized.append({
                "code":code,
                "steps":clean_steps
            })
    return normalized