from __future__ import annotations
import logging
import os
from pathlib import Path
from ingestion.collectors.pdf_parser           import parse_pdf
from ingestion.src.processors.merger          import merge_parsed_documents
from ingestion.src.processors.chunker          import build_chunks
from ingestion.src.storage.structured_writer   import write_to_structured_db
from ingestion.src.storage.vector_writer       import write_to_vector_db
from config import ingest_folder

logger     = logging.getLogger(__name__)
INGEST_DIR = Path(ingest_folder)
SUPPORTED = {".pdf"}


# ── Public: single file (existing API unchanged) ──────────────────────────────

def run_pipeline(filepath: str | Path) -> dict:

    path = Path(filepath)
    logger.info("Starting ingestion pipeline for: %s", path.name)

    # Parse the requested file
    target_doc = _parse_file(path)
    if not target_doc["dtc_code"]:
        raise ValueError(f"Could not extract DTC code from {path.name}")

    dtc_base = target_doc["dtc_code"].split("-")[0].upper()

    # Find all other files in knowledge_base/ with the same DTC code
    companion_docs = []
    for f in INGEST_DIR.iterdir():
        if f.suffix.lower() not in SUPPORTED:
            continue
        if f.resolve() == path.resolve():
            continue
        if dtc_base in f.name.upper():
            try:
                companion_docs.append(_parse_file(f))
                logger.info("Found companion file: %s", f.name)
            except Exception as e:
                logger.warning("Could not parse companion file %s: %s", f.name, e)

    # Merge all docs for this DTC code
    all_docs = [target_doc] + companion_docs
    merged_docs = merge_parsed_documents(all_docs)
    merged = merged_docs[0]  # only one DTC code in this run

    logger.info(
        "Merged %d source(s) for DTC %s — %d causes, %d steps, %d repairs",
        len(all_docs), merged["dtc_code"],
        len(merged["causes"]),
        len(merged["diagnostic_steps"]),
        len(merged["repair_actions"]),
    )

    return _write_merged(merged)


# ── Public: full knowledge base run ──────────────────────────────────────────

def run_full_pipeline() -> dict:

    logger.info("Starting full knowledge base ingestion from: %s", INGEST_DIR)

    # ── Stage 1: Scan ────────────────────────────────────────────────────
    files = [f for f in INGEST_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    if not files:
        raise ValueError(f"No supported files found in {INGEST_DIR}")
    logger.info("Found %d files: %s", len(files), [f.name for f in files])

    # ── Stage 2: Parse all ───────────────────────────────────────────────
    parsed_docs = []
    parse_errors = []
    for f in files:
        try:
            doc = _parse_file(f)
            parsed_docs.append(doc)
            logger.info("Parsed: %s → DTC %s", f.name, doc["dtc_code"])
        except Exception as e:
            parse_errors.append({"file": f.name, "error": str(e)})
            logger.error("Failed to parse %s: %s", f.name, e)

    if not parsed_docs:
        raise ValueError("All files failed to parse.")

    # ── Stage 3: Merge + deduplicate ─────────────────────────────────────
    merged_docs = merge_parsed_documents(parsed_docs)
    logger.info(
        "Merged into %d unique DTC code(s): %s",
        len(merged_docs),
        [d["dtc_code"] for d in merged_docs],
    )

    # ── Stage 4: Write each merged doc ───────────────────────────────────
    results = []
    write_errors = []
    for merged in merged_docs:
        try:
            summary = _write_merged(merged)
            results.append(summary)
        except Exception as e:
            write_errors.append({"dtc_code": merged["dtc_code"], "error": str(e)})
            logger.error("Failed to write %s: %s", merged["dtc_code"], e)

    return {
        "status":        "success" if not write_errors else "partial",
        "files_scanned": len(files),
        "dtc_codes":     len(merged_docs),
        "results":       results,
        "parse_errors":  parse_errors,
        "write_errors":  write_errors,
    }


# ── Shared write stage ────────────────────────────────────────────────────────

def _write_merged(merged: dict) -> dict:
    
    # Write to Supabase
    structured_summary = write_to_structured_db(merged)
    logger.info("Structured DB write complete for %s", merged["dtc_code"])

    # Build semantic chunks
    chunks = build_chunks(merged)
    logger.info("Built %d semantic chunks for %s", len(chunks), merged["dtc_code"])

    # Write to Milvus
    vector_summary = write_to_vector_db(chunks)
    logger.info("Vector DB write complete for %s", merged["dtc_code"])

    return {
        "dtc_code":      merged["dtc_code"],
        "sources":       merged["source_document"],
        "structured_db": structured_summary,
        "vector_db":     vector_summary,
        "chunks_total":  len(chunks),
    }


# ── File parser dispatcher ────────────────────────────────────────────────────

def _parse_file(path: Path) -> dict:
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")