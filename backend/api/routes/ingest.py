from __future__ import annotations
import os
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ingestion.src.scheduler.pipeline import run_full_pipeline
from config import ingest_folder
router = APIRouter()
logger = logging.getLogger(__name__)

INGEST_FOLDER = Path(ingest_folder)


@router.post("/ingest/all")
def ingest_all():
    """
    Scan the entire knowledge_base folder, parse all files, merge by DTC code,
    deduplicate, and write everything to Supabase and Milvus in one job.
    No request body needed.
    """
    try:
        summary = run_full_pipeline()
        return summary
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Full ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")


@router.get("/ingest/files")
def list_ingestable_files():
    """
    List all PDF and Excel files available in the knowledge_base folder.
    """
    if not INGEST_FOLDER.exists():
        return {"files": [], "folder": str(INGEST_FOLDER.resolve())}

    files = [
        f.name for f in INGEST_FOLDER.iterdir()
        if f.suffix.lower() in {".pdf", ".xlsx", ".xls"}
    ]
    return {
        "files":  sorted(files),
        "folder": str(INGEST_FOLDER.resolve()),
        "count":  len(files),
    }