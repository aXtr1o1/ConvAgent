from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime, timezone

from backend.utils.utilities import db, openai_client as client
from ingestion.retrieval.retriever import get_decision_tree
from config import azure_deployment

logger = logging.getLogger(__name__)

STATUS_ACTIVE   = "active"
STATUS_PAUSED   = "paused"
STATUS_RESOLVED = "resolved"
STATUS_ESCALATE = "escalate"


# ── LLM Intent Detector ───────────────────────────────────────────────────────

INTENT_PROMPT = """You are a diagnostic session intent classifier.

A vehicle technician is responding during an active diagnostic session.
Classify their response as YES, NO, CANCEL, or UNCLEAR.

CLASSIFY AS YES if the technician means:
- The check passed, condition is normal/good, expected result is met
- Words like: yes, yeah, yea, yep, passed, ok, looks good, confirmed, 
  correct, normal, fine, good, it's there, working, no issue, 
  all good, positive, affirmative, done, completed

CLASSIFY AS NO if the technician means:
- The check failed, something is wrong or missing
- Words like: no, nope, failed, not working, missing, damaged, broken,
  incorrect, abnormal, fault found, negative, not present,
  below spec, above spec, out of range, bad, wrong

CLASSIFY AS CANCEL if the technician wants to stop the session:
- They want to exit, quit, or stop the diagnostic
- Words like: cancel, stop, exit, quit, abort, end, terminate,
  never mind, forget it, stop this, i want to stop, exit diagnosis,
  let's stop, end session, quit session

CLASSIFY AS UNCLEAR if you cannot determine the intent.

Respond with ONLY one word: YES, NO, CANCEL, or UNCLEAR"""


def _llm_detect_intent(message: str, current_question: str, current_step: dict) -> str:
    """
    Use LLM to detect if technician means YES, NO, CANCEL or UNCLEAR.
    Returns: "YES", "NO", "CANCEL", or "UNCLEAR"
    """
    try:
        response = client.chat.completions.create(
            model=azure_deployment,
            messages=[
                {"role": "system", "content": INTENT_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Diagnostic check question: {current_question}\n"
                        f"Technician response: {message}\n"
                        f"Current step: {current_step}"
                    )
                }
            ],
            max_tokens=5,
            temperature=0.0
        )
        intent = response.choices[0].message.content.strip().upper()
        logger.info("Intent detection: '%s' → %s", message, intent)
        return intent if intent in {"YES", "NO", "CANCEL"} else "UNCLEAR"

    except Exception as e:
        logger.error("Intent detection failed: %s", e)
        # Fallback keyword match
        msg = message.strip().lower()
        if msg in {"yes", "y", "1", "true", "pass", "ok", "yeah", "yea"}:
            return "YES"
        if msg in {"no", "n", "0", "false", "fail", "failed", "nope"}:
            return "NO"
        if msg in {"cancel", "stop", "exit", "quit", "abort"}:
            return "CANCEL"
        return "UNCLEAR"


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


def _parse_decision_context(raw) -> dict:
    """
    Safely deserialise the decision_context field regardless of whether Supabase
    returned it as an already-parsed dict (JSONB column) or a JSON string
    (TEXT column).
    """
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Could not parse decision_context field: %r", raw)
        return {}


def _parse_answers(raw) -> list:
    """
    Safely deserialise the answers field regardless of whether Supabase
    returned it as an already-parsed list (JSONB column) or a JSON string
    (TEXT column). Avoids TypeError from json.loads(list).
    """
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Could not parse answers field: %r", raw)
        return []


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


def _reactivate_session(session_id: str) -> None:
    db.table("diagnostic_sessions").update({
        "status":     STATUS_ACTIVE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("session_id", session_id).execute()


def pause_session(session_id: str) -> None:
    db.table("diagnostic_sessions").update({
        "status":     STATUS_PAUSED,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("session_id", session_id).execute()


def _resume_parent_if_any(session: dict) -> dict | None:
    """
    If this session has a parent_session_id, resume the parent session and
    return {parent_id, parent_dtc, parent_step}. Otherwise return None.

    parent_step prefers the snapshot taken at switch time (parent_resume_step),
    so we resume exactly where the user left the parent flow.
    """
    ctx = _parse_decision_context(session.get("decision_context"))
    parent_id = ctx.get("parent_session_id")
    if not parent_id:
        return None
    _reactivate_session(parent_id)
    parent = _load_session(parent_id) or {}
    snap = ctx.get("parent_resume_step")
    if snap is None or snap == "":
        parent_step = int(parent.get("current_step", 0)) if parent else 0
    else:
        parent_step = int(snap)
    parent_dtc = parent.get("dtc_code", "") if parent else ""
    return {"parent_id": parent_id, "parent_dtc": parent_dtc, "parent_step": parent_step}


# ── Public API ────────────────────────────────────────────────────────────────

def start_session(conversation_id: str, dtc_code: str, parent_session_id: str | None = None) -> dict:

    tree = get_decision_tree(dtc_code)
    if not tree or not tree.get("steps"):
        return {
            "error": f"No diagnostic data found for {dtc_code}. "
                     "Ensure the document has been ingested."
        }

    session_id = str(uuid.uuid4())
    steps      = tree["steps"]
    parent_resume_step = None
    if parent_session_id:
        parent_row = _load_session(parent_session_id)
        if parent_row:
            parent_resume_step = int(parent_row.get("current_step", 0))
    decision_context = {
    "dtc_code": tree["dtc_code"],
    "description": tree["description"],
    "steps": tree["steps"],
    "reactions": tree.get("reactions", ""),
    "parent_session_id": parent_session_id,
    "parent_resume_step": parent_resume_step,
}

    db.table("diagnostic_sessions").insert({
        "session_id":      session_id,
        "conversation_id": conversation_id,
        "dtc_code":        tree["dtc_code"],
        "current_step":    0,                # int — matches integer column
        "answers":         json.dumps([]),   # JSON string — safe for both TEXT and JSONB
        "status":          STATUS_ACTIVE,
        "decision_context": json.dumps(decision_context),  
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
        "decision_context": json.dumps(decision_context),  
    }


def advance_session(session_id: str, answer: str) -> dict:

    session = _load_session(session_id)
    if not session:
        return {"error": "Session not found or already closed.", "message": "Session not found."}

    if session["status"] != STATUS_ACTIVE:
        return {
            "error": f"Session is already {session['status']}.",
            "message": f"This diagnostic session is already {session['status']}. "
                       "Start a new session by sharing a fault code.",
        }

    tree = get_decision_tree(session["dtc_code"])
    if not tree:
        # If this session was created by switching from another ("parent") session
        # and the new DTC can't be loaded, revert to the parent session.
        ctx = _parse_decision_context(session.get("decision_context"))
        parent_id = ctx.get("parent_session_id")
        if parent_id:
            try:
                close_session(session_id)
                _reactivate_session(parent_id)
                parent = _load_session(parent_id) or {}
                ctx0 = _parse_decision_context(session.get("decision_context"))
                snap0 = ctx0.get("parent_resume_step")
                if snap0 is not None and snap0 != "":
                    parent_step = int(snap0)
                else:
                    parent_step = int(parent.get("current_step", 0)) if parent else 0
                parent_dtc = parent.get("dtc_code", "")
                return {
                    "message": (
                        f"Diagnostic data for **{session.get('dtc_code', '')}** could not be loaded.\n\n"
                        f"Reverting back to your previous diagnostic session **{parent_dtc}** "
                        f"(step {parent_step + 1}).\n\n"
                        "Reply YES / NO for the previous session’s current step."
                    ),
                    "status": STATUS_ACTIVE,
                    "step_current": parent_step + 1,
                }
            except Exception as e:
                logger.error("Failed to revert to parent session: %s", e, exc_info=True)

        return _resolve(session_id, f"Diagnostic data for {session['dtc_code']} could not be loaded.")

    steps = tree.get("steps", [])
    idx = int(session.get("current_step", 0))
    answers = _parse_answers(session.get("answers", "[]"))

    if idx >= len(steps):
        return _resolve(session_id, "All diagnostic steps have been completed.")

    current_step = steps[idx]

    def _user_means_no(text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        if t in {"no", "n", "nope", "0", "false", "fail", "failed", "negative"}:
            return True
        return t.startswith("no") or "not " in t or "fail" in t

    # Branching DTC: if this session was started from a paused parent and step 1 fails,
    # return to the parent DTC at the step where the user branched.
    if idx == 0:
        sctx = _parse_decision_context(session.get("decision_context"))
        parent_sid = sctx.get("parent_session_id")
        if parent_sid and _user_means_no(answer):
            parent_row = _load_session(parent_sid) or {}
            resume_idx = sctx.get("parent_resume_step")
            if resume_idx is None or resume_idx == "":
                resume_idx = int(parent_row.get("current_step", 0))
            else:
                resume_idx = int(resume_idx)
            ptree = get_decision_tree(parent_row.get("dtc_code", ""))
            psteps = ptree.get("steps", []) if ptree else []
            if 0 <= resume_idx < len(psteps):
                close_session(session_id)
                _update_session(
                    parent_sid,
                    resume_idx,
                    _parse_answers(parent_row.get("answers", "[]")),
                    STATUS_ACTIVE,
                )
                pq = psteps[resume_idx].get("question", "")
                return {
                    "message": (
                        f"Branched diagnostic **{session.get('dtc_code', '')}** — step 1 did not pass.\n\n"
                        f"Returning to **{parent_row.get('dtc_code', '')}** at "
                        f"**step {resume_idx + 1} of {len(psteps)}**:\n\n{pq}\n\n"
                        "Reply **YES** if the check passes | **NO** if it fails | **CANCEL** to stop."
                    ),
                    "status": STATUS_ACTIVE,
                    "step_current": resume_idx + 1,
                    "step_total": len(psteps),
                    "action_taken": "rollback_to_parent",
                }

    # ── INTENT DETECTION ─────────────────────────────────────────────
    intent = _llm_detect_intent(answer, current_step["question"],current_step )

    if intent == "CANCEL":
        close_session(session_id)
        # If this was a switched (child) session, go back to the parent session.
        try:
            parent_info = _resume_parent_if_any(session)
            if parent_info:
                return {
                    "message": (
                        "Diagnostic session cancelled.\n\n"
                        f"Resuming previous diagnostic session **{parent_info['parent_dtc']}** "
                        f"(step {parent_info['parent_step'] + 1}).\n\n"
                        "Reply YES / NO for the previous session’s current step."
                    ),
                    "status": STATUS_ACTIVE,
                    "step_current": parent_info["parent_step"] + 1,
                    "step_total": len(steps),
                    "action_taken": None,
                }
        except Exception as e:
            logger.error("Failed to resume parent on cancel: %s", e, exc_info=True)

        return {
            "message": "Diagnostic session cancelled.",
            "status": STATUS_RESOLVED,
            "step_current": idx + 1,
            "step_total": len(steps),
            "action_taken": None,
        }

    if intent == "UNCLEAR":
        return {
            "message": (
                f"I didn't understand: \"{answer}\"\n\n"
                f"**{current_step['question']}**\n\n"
                "Reply YES / NO / Cancel"
            ),
            "status": STATUS_ACTIVE,
            "step_current": idx + 1,
            "step_total": len(steps),
            "action_taken": None,
        }

    is_yes = (intent == "YES")

    # ── RECORD ANSWER ────────────────────────────────────────────────
    answers.append({
        "step": idx + 1,
        "question": current_step["question"],
        "answer": "YES" if is_yes else "NO",
        "raw": answer,
    })

    # ── ACTION LOGIC ─────────────────────────────────────────────────
    if is_yes:
        action_text = current_step.get("yes_action", "")
    else:
        action_text = current_step.get("no_action", "")

    next_idx = idx + 1

    # ── 🔥 DECISION CONTEXT (KEY FOR YOUR DECISION AGENT) ─────────────
   

    # ── RESOLUTION CONDITION ─────────────────────────────────────────
    if next_idx >= len(steps):
        status = STATUS_RESOLVED if not is_yes else STATUS_ESCALATE

        message = (
            f"Final Step Result:\n\n"
            f"**{current_step['question']}** → {'PASSED' if is_yes else 'FAILED'}\n\n"
            f"Action: {action_text}"
        )

        _update_session(session_id, next_idx, answers, status)

        # If this was a switched (child) session, resume the parent session.
        try:
            parent_info = _resume_parent_if_any(session)
            if parent_info:
                message += (
                    "\n\n"
                    f"Resuming previous diagnostic session **{parent_info['parent_dtc']}** "
                    f"(step {parent_info['parent_step'] + 1})."
                )
        except Exception as e:
            logger.error("Failed to resume parent after final step: %s", e, exc_info=True)

        return {
            "message": message,
            "status": status,
            "step_current": next_idx,
            "step_total": len(steps),
            "action_taken": action_text,
            # 🔥 IMPORTANT
        }

    # ── NEXT STEP ────────────────────────────────────────────────────
    next_step = steps[next_idx]

    message = (
        f"Step {idx + 1}: {'PASSED' if is_yes else 'FAILED'}\n"
        f"Action: {action_text}\n\n"
        f"**Step {next_idx + 1}: {next_step['question']}**\n\n"
        "Reply YES / NO or Cancel"
    )

    _update_session(session_id, next_idx, answers, STATUS_ACTIVE)

    return {
        "message": message,
        "status": STATUS_ACTIVE,
        "step_current": next_idx + 1,
        "step_total": len(steps),
        "action_taken": action_text,
     # 🔥 THIS IS WHAT YOU NEEDED
    }
def get_session(session_id: str) -> dict | None:
    return _load_session(session_id)


def get_active_session_for_conversation(conversation_id: str) -> dict | None:
    resp = (
        db.table("diagnostic_sessions")
        .select("*")
        .eq("conversation_id", conversation_id)
        .eq("status", STATUS_ACTIVE)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    logger.info(
        "get_active_session → conversation_id: %s | results: %d",
        conversation_id,
        len(resp.data),
    )
    return resp.data[0] if resp.data else None


def close_session(session_id: str) -> None:
    db.table("diagnostic_sessions").update({
        "status":     STATUS_RESOLVED,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("session_id", session_id).execute()