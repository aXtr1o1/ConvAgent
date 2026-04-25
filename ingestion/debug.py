import pdfplumber
from pathlib import Path
from ingestion.collectors.pdf_parser import parse_pdf

path = Path("ingestion/knowledge_base/DCT-P2463-KowledgeBase_Updated.pdf")

# Check raw page content
print("=" * 50)
print("RAW PDF CONTENT")
print("=" * 50)
with pdfplumber.open(path) as pdf:
    for i, page in enumerate(pdf.pages[:3]):  # first 3 pages
        print(f"\n=== PAGE {i+1} ===")
        print(page.extract_text())

# Check what parser extracts
print("\n" + "=" * 50)
print("PARSER OUTPUT")
print("=" * 50)
result = parse_pdf(path)
print("DTC Code:", result["dtc_code"])
print("Description:", result["description"])
print("System:", result["system"])
print("Causes found:", len(result["causes"]))
print("Steps found:", len(result["diagnostic_steps"]))
print("Repairs found:", len(result["repair_actions"]))
# add this to debug_pdf.py and run again
from ingestion.collectors.pdf_parser import parse_pdf
from pathlib import Path

result = parse_pdf(Path("ingestion/knowledge_base/DCT-P2463-KowledgeBase_Updated.pdf"))

print("\n=== CAUSES ===")
for c in result["causes"]:
    print(f"  - {c['cause']}")

print("\n=== FIRST 10 STEPS ===")
for s in result["diagnostic_steps"][:10]:
    print(f"\n  Step {s['step_order']}: {s['question']}")
    print(f"  YES: {s['yes_action']}")
    print(f"  NO:  {s['no_action']}")

print("\n=== REPAIRS ===")
for r in result["repair_actions"]:
    print(f"  - {r['repair']}")

print("\n=== RELATED CODES ===")
print(result["related_codes"])