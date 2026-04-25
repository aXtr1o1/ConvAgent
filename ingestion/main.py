from __future__ import annotations
import logging
import sys
from pathlib import Path
from ingestion.src.scheduler.pipeline import run_pipeline, run_full_pipeline

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    args = sys.argv[1:]

    # ── No arguments — run full pipeline ─────────────────────────────────
    if not args:
        logger.info("No file specified — running full pipeline on knowledge_base/")
        result = run_full_pipeline()
        _print_result(result)
        return

    # ── File path provided — run single file pipeline ─────────────────────
    filepath = Path(args[0])
    if not filepath.exists():
        logger.error("File not found: %s", filepath)
        sys.exit(1)

    if filepath.suffix.lower() != ".pdf":
        logger.error("Only PDF files are supported. Got: %s", filepath.suffix)
        sys.exit(1)

    logger.info("Running single file pipeline for: %s", filepath.name)
    result = run_pipeline(filepath)
    _print_single_result(result)


def _print_result(result: dict):
    print("\n" + "=" * 50)
    print("INGESTION COMPLETE")
    print("=" * 50)
    print(f"Status        : {result['status']}")
    print(f"Files scanned : {result['files_scanned']}")
    print(f"DTC codes     : {result['dtc_codes']}")

    if result["results"]:
        print("\nResults:")
        for r in result["results"]:
            print(f"  DTC {r['dtc_code']}")
            print(f"    Source      : {r['sources']}")
            print(f"    Chunks      : {r['chunks_total']}")
            print(f"    Structured  : {r['structured_db']}")
            print(f"    Vector DB   : {r['vector_db']}")

    if result["parse_errors"]:
        print("\nParse Errors:")
        for e in result["parse_errors"]:
            print(f"  {e['file']} → {e['error']}")

    if result["write_errors"]:
        print("\nWrite Errors:")
        for e in result["write_errors"]:
            print(f"  {e['dtc_code']} → {e['error']}")

    print("=" * 50 + "\n")


def _print_single_result(result: dict):
    print("\n" + "=" * 50)
    print("INGESTION COMPLETE")
    print("=" * 50)
    print(f"DTC Code    : {result['dtc_code']}")
    print(f"Source      : {result['sources']}")
    print(f"Chunks      : {result['chunks_total']}")
    print(f"Structured  : {result['structured_db']}")
    print(f"Vector DB   : {result['vector_db']}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()