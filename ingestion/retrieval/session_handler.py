from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime, timezone

from backend.utils.utilities import db
from ingestion.retrieval.retriever import get_decision_tree

logger = logging.getLogger(__name__)

STATUS_ACTIVE   = "active"
STATUS_RESOLVED = "resolved"
STATUS_ESCALATE = "escalate"


# ── Public API ────────────────────────────────────────────────────────────────

def start_session(conversation_id: str, dtc_code: str) -> dict:

    tree = get_decision_tree(dtc_code)
    if not tree or not tree.get("steps"):
        return {
            "error": f"No diagnostic data found for {dtc_code}. "
                     "Ensure the document has been ingested."
        }

    session_id = str(uuid.uuid4())
    steps      = tree["steps"]

    db.table("diagnostic_sessions").insert({
        "session_id":      session_id,
        "conversation_id": conversation_id,
        "dtc_code":        tree["dtc_code"],
        "current_step":    0,
        "answers":         json.dumps([]),
        "status":          STATUS_ACTIVE,
    }).execute()

    first_step = steps[0]
    intro = (
        f"Starting diagnostic for **{tree['dtc_code']}** — "
        f"{tree['description']}.\n\n"
    )
    if tree.get("reactions"):
        intro += f"Expected system reactions: {tree['reactions']}\n\n"
    intro += f"**Step 1 of {len(steps)}:** {first_step['question']}\n\n"
    intro += "Reply **YES** if the check passes or **NO** if it fails."

    return {
        "session_id":   session_id,
        "dtc_code":     tree["dtc_code"],
        "description":  tree["description"],
        "reactions":    tree.get("reactions", ""),
        "message":      intro,
        "step_total":   len(steps),
        "step_current": 1,
    }


def advance_session(session_id: str, answer: str) -> dict:
    """
    Process a YES/NO answer and advance to the next step.

    Returns:
    {
        "message":      str,   ← next question or resolution text
        "status":       str,   ← active | resolved | escalate
        "step_current": int,
        "step_total":   int,
        "action_taken": str | None,
    }
    """
    session = _load_session(session_id)
    if not session:
        return {"error": "Session not found or already closed."}

    if session["status"] != STATUS_ACTIVE:
        return {"error": f"Session is already {session['status']}."}

    tree    = get_decision_tree(session["dtc_code"])
    steps   = tree.get("steps", [])
    answers = json.loads(session.get("answers", "[]"))
    idx     = session["current_step"]   # 0-based index into steps[]

    if idx >= len(steps):
        return _resolve(session_id, "All steps completed.")

    current_step = steps[idx]
    normalised   = answer.strip().upper()
    is_yes       = normalised in {"YES", "Y", "1", "TRUE", "PASS"}

    # Record the answer
    answers.append({
        "step":     idx + 1,
        "question": current_step["question"],
        "answer":   "YES" if is_yes else "NO",
    })

    if is_yes:
        # YES → move to the next step
        action_text = current_step.get("yes_action", "Proceed to next step.")
        next_idx    = idx + 1
    else:
        # NO → this step's no_action is the repair instruction → resolve here
        action_text = current_step.get("no_action", "Rectify and re-test.")
        next_idx    = len(steps)  # force resolution after repair given

    if next_idx >= len(steps):
        # Resolution
        if is_yes:
            message = (
                "All diagnostic checks passed. No fault confirmed at this stage.\n\n"
                f"Last step recommendation: {action_text}\n\n"
                "If the DTC persists, please escalate to technical support."
            )
            status = STATUS_ESCALATE
        else:
            message = (
                f"**Fault identified at step {idx + 1}.**\n\n"
                f"Check that failed: {current_step['question']}\n\n"
                f"**Recommended action:** {action_text}\n\n"
                "After completing the repair, clear the fault code and "
                "perform a drive cycle to verify."
            )
            status = STATUS_RESOLVED

        _update_session(session_id, next_idx, answers, status)
        return {
            "message":      message,
            "status":       status,
            "step_current": next_idx,
            "step_total":   len(steps),
            "action_taken": action_text,
        }

    # More steps remaining
    next_step = steps[next_idx]
    message = (
        f"Step {idx + 1} — {'passed' if is_yes else 'failed'}. "
        f"{action_text}\n\n"
        f"**Step {next_idx + 1} of {len(steps)}:** {next_step['question']}\n\n"
        "Reply **YES** if the check passes or **NO** if it fails."
    )

    _update_session(session_id, next_idx, answers, STATUS_ACTIVE)
    return {
        "message":      message,
        "status":       STATUS_ACTIVE,
        "step_current": next_idx + 1,
        "step_total":   len(steps),
        "action_taken": action_text,
    }


def get_session(session_id: str) -> dict | None:
    """Return the current session state."""
    return _load_session(session_id)


def get_active_session_for_conversation(conversation_id: str) -> dict | None:
    """
    Find the most recent active session for a given conversation.
    Used by conversations.py to detect if a session is already in progress.
    """
    resp = (
        db.table("diagnostic_sessions")
        .select("*")
        .eq("conversation_id", conversation_id)
        .eq("status", STATUS_ACTIVE)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def close_session(session_id: str) -> None:
    """Manually close a session (e.g. technician typed 'cancel')."""
    db.table("diagnostic_sessions").update({
        "status":     STATUS_RESOLVED,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("session_id", session_id).execute()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_session(session_id: str) -> dict | None:
    resp = (
        db.table("diagnostic_sessions")
        .select("*")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def _update_session(
    session_id: str,
    next_idx: int,
    answers: list,
    status: str,
) -> None:
    db.table("diagnostic_sessions").update({
        "current_step": next_idx,
        "answers":      json.dumps(answers),
        "status":       status,
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }).eq("session_id", session_id).execute()


def _resolve(session_id: str, message: str) -> dict:
    _update_session(session_id, 0, [], STATUS_RESOLVED)
    return {"message": message, "status": STATUS_RESOLVED}
