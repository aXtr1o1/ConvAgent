from __future__ import annotations
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ingestion.retrieval.retriever      import get_decision_tree, semantic_search
from ingestion.retrieval.session_handler import (
    start_session,
    advance_session,
    get_session,
    close_session,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request / response schemas ────────────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    dtc_code: str


class SessionStartRequest(BaseModel):
    conversation_id: str
    dtc_code:        str


class SessionAnswerRequest(BaseModel):
    session_id: str
    answer:     str    # "YES" or "NO"


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5


# ── Single-shot: full decision tree dump ─────────────────────────────────────

@router.post("/diagnose")
def diagnose(body: DiagnoseRequest):
    """
    Returns the complete structured diagnostic tree for a DTC code.
    Intended for API consumers, dashboards, or external tools.

    Example:
        POST /api/v1/diagnose
        { "dtc_code": "P2463" }
    """
    tree = get_decision_tree(body.dtc_code)
    if not tree:
        raise HTTPException(
            status_code=404,
            detail=f"No diagnostic data found for {body.dtc_code}. "
                   "Ensure the document has been ingested."
        )

    # Build the full decision path as an ordered list
    decision_path = []
    for step in tree.get("steps", []):
        decision_path.append({
            "step":       step["step_order"],
            "check":      step["question"],
            "if_yes":     step.get("yes_action", "Proceed"),
            "if_no":      step.get("no_action",  "Rectify and re-test"),
        })

    return {
        "dtc_code":     tree["dtc_code"],
        "description":  tree["description"],
        "system":       tree["system"],
        "reactions":    tree["reactions"],
        "causes":       tree["causes"],
        "decision_path": decision_path,
        "repairs":      tree["repairs"],
    }


# ── Interactive: session management ──────────────────────────────────────────

@router.post("/diagnose/session")
def start_diagnostic_session(body: SessionStartRequest):
    """
    Start a new interactive diagnostic session.
    Returns the first YES/NO question to present to the technician.

    Example:
        POST /api/v1/diagnose/session
        { "conversation_id": "abc123", "dtc_code": "P2463" }
    """
    result = start_session(body.conversation_id, body.dtc_code)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/diagnose/answer")
def submit_answer(body: SessionAnswerRequest):
    """
    Submit a YES or NO answer to the current diagnostic step.
    Returns the next question or the final resolution.

    Example:
        POST /api/v1/diagnose/answer
        { "session_id": "uuid", "answer": "YES" }
    """
    result = advance_session(body.session_id, body.answer)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/diagnose/session/{session_id}")
def get_session_state(session_id: str):
    """Get the current state of a diagnostic session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.delete("/diagnose/session/{session_id}")
def cancel_session(session_id: str):
    """Cancel / close an active diagnostic session."""
    close_session(session_id)
    return {"status": "cancelled", "session_id": session_id}


# ── Semantic search ───────────────────────────────────────────────────────────

@router.post("/diagnose/search")
def search_knowledge(body: SemanticSearchRequest):
    """
    Semantic search across the vector knowledge base.
    Returns the most relevant chunks for a natural language query.

    Example:
        POST /api/v1/diagnose/search
        { "query": "DPF soot load too high", "top_k": 5 }
    """
    chunks = semantic_search(body.query, top_k=body.top_k)
    return {"query": body.query, "results": chunks, "count": len(chunks)}
