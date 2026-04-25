from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from backend.utils.utilities import db, now_iso, to_ist
from dateutil import parser as dtparser
from backend.schemas.conversation_schema import CreateConversationRequest, SendMessageRequest
from datetime import datetime, timezone
from backend.agents.casual_llm import generate_title
from backend.agents.agent import (
    run_decision_agent,
    run_casual_agent,
    run_casual_agent_stream,
    run_reply_agent,
    run_reply_agent_stream,
)
import json

import uuid
import re

from ingestion.retrieval.retriever import (
    semantic_search,
    format_context_for_llm,
    get_dtc_metadata,
)
from ingestion.retrieval.session_handler import (
    start_session,
    advance_session,
    close_session,
    pause_session,
    get_active_session_for_conversation,
    _resume_parent_if_any
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()

# ── Diagnostic routing helper ─────────────────────────────────────────────────
DTC_PATTERN = re.compile(r'\b(P[0-9A-Fa-f]{4}(?:-[0-9A-Fa-f]{2})?)\b')


async def handle_diagnostic_routing(message: str, conversation_id: str):
    """
    Routes message to the appropriate handler.
    Cancel detection is now handled by LLM intent detector
    inside session_handler.advance_session() — no hardcoded words here.
    """

    # Already in a session — LLM handles YES / NO / CANCEL / UNCLEAR
    active = get_active_session_for_conversation(conversation_id)
    
    if active:
        result = advance_session(active["session_id"], message)
        
        print("Appended decision context to conversation history in DB.")
        return {"response": result["message"]}

    # New DTC detected in message
    match = DTC_PATTERN.search(message)
    if match:
        dtc_code = match.group(1).upper()
        meta = get_dtc_metadata(dtc_code)
        if meta:
            result = start_session(conversation_id, dtc_code)
            if "error" not in result:
                return {"response": result["message"]}

    return None


# ── Tool functions passed to Decision Agent ───────────────────────────────────

def _make_supabase_tool(conversation_id: str):
    """
    Returns a synchronous supabase tool function bound to this conversation.

    handle_diagnostic_routing is async, but run_decision_agent is called from
    a sync FastAPI endpoint (already inside a threadpool thread). We cannot use
    asyncio.run() here because there is already a running event loop in that
    thread context, which raises RuntimeError.

    Solution: call the underlying sync functions directly instead of going
    through the async wrapper. handle_diagnostic_routing does nothing async
    itself — its body is entirely sync Supabase SDK calls.
    """
    def supabase_tool(message: str, intent: str = None, dtc_code: str = None, parent_bool: bool = False):
        try:
            # Replicate handle_diagnostic_routing inline (sync — no await needed)
            active = get_active_session_for_conversation(conversation_id)
            if parent_bool:
                if active:
                    close_session(active["session_id"])
                print("Resuming parent session")
                parent_info = _resume_parent_if_any(active)
                if parent_info:
                    return {"response": parent_info["parent_dtc"]},[]
                else:
                    return {"response": "Could not resume parent session."},[]
                    
            if intent=="cancel":
                if active:
                    close_session(active["session_id"])
                    return {"response": "Diagnostic session cancelled."},[]
                return {"response": "No active diagnostic session to cancel."},[]
            if intent == "start_session" and dtc_code:
                # Switching DTC should behave like a decision tree:
                # try starting the new DTC first; if it fails, keep the previous session.
                prev_session_id = active["session_id"] if active else None
                result = start_session(conversation_id, dtc_code, parent_session_id=prev_session_id)
                print(f"Result: {result}")

                if not result:
                    return {"response": "Could not start a new diagnostic session. Continuing previous session if available."}, []

                # If knowledge base has no tree for the new DTC, do NOT close the previous session.
                if result.get("error"):
                    return {
                        "response": (
                            f"{result['error']}\n\n"
                            "Continuing your previous diagnostic session. Reply YES/NO for the current step."
                        )
                    }, []

                # New session started successfully → now close the previous session.
                if prev_session_id:
                    # Do NOT resolve it; pause it so we can resume later.
                    pause_session(prev_session_id)

                return {"response": result.get("message", "Started new diagnostic session.")}, []
            if intent == "continue_session":
                if not active:
                    return {"response": "No active session to continue."}   
                result = advance_session(active["session_id"], message)
                
                return {"response": result["message"]},[]
            
            return None
        except Exception as e:
            logger.error("supabase_tool error: %s", e, exc_info=True)
            return None
    return supabase_tool



# ── 1. CREATE CONVERSATION ────────────────────────────────────────────────────
@router.post("/conversations")
def create_conversation(body: CreateConversationRequest):
    ts = now_iso()
    res = db.table("conversations").insert({
        "userid":            body.user_id,
        "conversationtitle": "New Conversation",
        "conversationdata":  [],
        "updatedat":         ts,
    }).execute()

    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create conversation.")

    row = res.data[0]
    return {
        "conversation_id": str(row["conversationid"]),
        "user_id":         str(row["userid"]),
        "title":           row["conversationtitle"],
        "created_at":      to_ist(row["createdat"]),
        "updated_at":      to_ist(row.get("updatedat") or row["createdat"]),
    }


def _is_valid_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except (ValueError, TypeError):
        return False


# ── 2. LIST CONVERSATIONS ─────────────────────────────────────────────────────
@router.get("/conversations/user/{user_id}")
def list_conversations(user_id: str):
    if not _is_valid_uuid(user_id):
        return {"conversations": []}
    try:
        res = db.table("conversations") \
            .select("conversationid, conversationtitle, updatedat, createdat") \
            .eq("userid", user_id) \
            .execute()
    except Exception as e:
        err_msg = str(e).lower()
        if "uuid" in err_msg or "invalid" in err_msg:
            return {"conversations": []}
        raise HTTPException(status_code=500, detail="Failed to load conversations.")

    conversations = []
    for row in res.data:
        updated_at = row.get("updatedat") or row.get("createdat")
        try:
            sort_dt = dtparser.parse(str(updated_at))
            if sort_dt.tzinfo is None:
                sort_dt = sort_dt.replace(tzinfo=timezone.utc)
        except Exception:
            sort_dt = datetime.min.replace(tzinfo=timezone.utc)

        conversations.append({
            "conversation_id": str(row["conversationid"]),
            "title":           row.get("conversationtitle", "New Conversation"),
            "updated_at":      to_ist(updated_at),
            "_sort_key":       sort_dt,
        })

    conversations.sort(key=lambda x: x["_sort_key"], reverse=True)
    for c in conversations:
        c.pop("_sort_key")

    return {"conversations": conversations}


# ── 3. GET CONVERSATION ───────────────────────────────────────────────────────
@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    res = db.table("conversations") \
        .select("conversationid, conversationtitle, conversationdata, updatedat, createdat") \
        .eq("conversationid", conversation_id) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    row          = res.data[0]
    raw_messages = row.get("conversationdata") or []
    updated_at   = row.get("updatedat") or row.get("createdat")

    messages = []
    for m in raw_messages:
        if not isinstance(m, dict):
            continue
        msg = {
            "message_id": m.get("message_id", str(uuid.uuid4())),
            "role":       m.get("role", ""),
            "content":    m.get("content", ""),
            "created_at": to_ist(m.get("created_at", "")),
            "db_used":    m.get("db_used", ""),
        }
        if m.get("role") == "assistant":
            msg["sources"] = m.get("sources", [])
        messages.append(msg)

    return {
        "conversation_id": str(row["conversationid"]),
        "title":           row.get("conversationtitle", "New Conversation"),
        "updated_at":      to_ist(updated_at),
        "messages":        messages,
    }


# ── 4. DELETE CONVERSATION ────────────────────────────────────────────────────
@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    db.table("conversations") \
        .delete() \
        .eq("conversationid", conversation_id) \
        .execute()
    return {"success": True}


# ── 5. SEND MESSAGE + GET LLM REPLY ──────────────────────────────────────────
@router.post("/messages/{conversation_id}")
def send_message(conversation_id: str, body: SendMessageRequest):
    logger.info("Received message for conversation %s: %s", conversation_id, body.message[:100])
    res = db.table("conversations") \
        .select("conversationtitle, conversationdata") \
        .eq("conversationid", conversation_id) \
        .execute()
    

    if not res.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    row           = res.data[0]
    current_title = row.get("conversationtitle", "New Conversation")
    history       = row.get("conversationdata") or []
    ts            = now_iso()

    user_entry = {
        "message_id": str(uuid.uuid4()),
        "role":       "user",
        "content":    body.message,
        "created_at": ts,
    }
    history.append(user_entry)

    llm_history = [
        {"role": m["role"], "content": m["content"]}
        for m in history[:10]
    ]

    # ── Check active session ──────────────────────────────────────────────
    active_session = get_active_session_for_conversation(conversation_id)
    logger.info(
        "Active session check — conversation_id: %s | found: %s | session: %s",
        conversation_id,
        bool(active_session),
        active_session.get("session_id") if active_session else "None",
    )
    # ── AGENT 1: Decision + Tool Call ─────────────────────────────────────
    decision_result = run_decision_agent(
        message=body.message,
        has_active_session=bool(active_session),
        conversation_history=llm_history,
        conversation_id=conversation_id,
        supabase_tool=_make_supabase_tool(conversation_id),
       
    )
    

    print(f"LLM History for reply agent: {llm_history}")
    print(f"Decision agent results: {decision_result}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🤖 DECISION AGENT OUTPUT")
    logger.info("Route      : %s", decision_result.get("route"))
    logger.info("Tool       : %s", decision_result.get("tool"))
    logger.info("DB Used    : %s", decision_result.get("db_used"))
    logger.info("Confidence : %s", decision_result.get("confidence"))
    logger.info("Reason     : %s", decision_result.get("reason"))

    route       = decision_result["route"]
    raw_context = decision_result["raw_context"]
    source_type = decision_result["source_type"]
    db_used     = decision_result["db_used"]
    sources     = decision_result["sources"]

    if db_used == "supabase":
        logger.info("🗄️ SUPABASE HIT — diagnostic flow used")

    # ── AGENT 2: Casual — ONLY when route is genuinely casual ────────────
    # Never invoke the casual agent during an active diagnostic session
    # or when the decision agent already retrieved diagnostic data.
    if route == "casual":
        logger.info("💬 CASUAL AGENT TRIGGERED")
        raw_context = run_casual_agent(llm_history)
        source_type = "casual"
        db_used     = "llm_only"

    # ── AGENT 3: Reply formatter ──────────────────────────────────────────
    assistant_reply = run_reply_agent(
        raw_context=raw_context,
        user_message=body.message,
        conversation_history=llm_history,
        source_type=source_type,
    )

    # ── Save and return ───────────────────────────────────────────────────
    assistant_entry = {
        "message_id": str(uuid.uuid4()),
        "role":       "assistant",
        "content":    assistant_reply,
        "sources":    sources,
        "db_used":    db_used,
        "created_at": now_iso(),
    }
    history.append(assistant_entry)

    new_title = current_title
    if current_title == "New Conversation":
        new_title = generate_title(body.message)

    db.table("conversations").update({
        "conversationdata":  history,
        "conversationtitle": new_title,
        "updatedat":         now_iso(),
    }).eq("conversationid", conversation_id).execute()

    logger.info("✅ FINAL RESPONSE GENERATED | db_used=%s", db_used)
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "message_id": m.get("message_id", ""),
                "role":       m.get("role", ""),
                "content":    m.get("content", ""),
                "created_at": to_ist(m.get("created_at", "")),
                "db_used":    m.get("db_used", ""),
                **( {"sources": m.get("sources", [])} if m.get("role") == "assistant" else {} )
            } for m in history
        ]
    }


# ── 6. WEBSOCKET ──────────────────────────────────────────────────────────────
@router.websocket("/ws/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    try:
        while True:
            user_message = await websocket.receive_text()

            res = db.table("conversations") \
                .select("conversationtitle, conversationdata") \
                .eq("conversationid", conversation_id) \
                .execute()

            if not res.data:
                await websocket.send_text("Conversation not found.")
                break

            row           = res.data[0]
            current_title = row.get("conversationtitle", "New Conversation")
            history       = row.get("conversationdata") or []
            ts            = now_iso()

            user_entry = {
                "message_id": str(uuid.uuid4()),
                "role":       "user",
                "content":    user_message,
                "sources":    [],
                "created_at": ts,
            }
            history.append(user_entry)

            llm_history = [
                {"role": m["role"], "content": m["content"]}
                for m in history
            ]

            # ── Check active session ──────────────────────────────────────
            active_session = get_active_session_for_conversation(conversation_id)
            logger.info(
                "WS Active session check — conversation_id: %s | found: %s | session: %s",
                conversation_id,
                bool(active_session),
                active_session.get("session_id") if active_session else "None"
            )
            # ── AGENT 1: Decision + Tool Call ─────────────────────────────
            decision_result = run_decision_agent(
                message=user_message,
                has_active_session=bool(active_session),
                conversation_history=llm_history,
                supabase_tool=_make_supabase_tool(conversation_id),
              
            )

            route       = decision_result["route"]
            raw_context = decision_result["raw_context"]
            source_type = decision_result["source_type"]
            db_used     = decision_result["db_used"]
            sources     = decision_result["sources"]

            # ── AGENT 2: Casual ───────────────────────────────────────────
            if route == "casual":
                raw_context = run_casual_agent(llm_history)
                source_type = "casual"
                db_used     = "llm_only"

            # ── AGENT 3: Reply — stream to frontend ───────────────────────
            full_reply = ""
            for chunk in run_reply_agent_stream(
                raw_context=raw_context,
                user_message=user_message,
                source_type=source_type,
                conversation_history=llm_history,
            ):
                full_reply += chunk
                await websocket.send_text(chunk)
            await websocket.send_text("[DONE]")

            # ── Save to DB ────────────────────────────────────────────────
            assistant_entry = {
                "message_id": str(uuid.uuid4()),
                "role":       "assistant",
                "content":    full_reply,
                "sources":    sources,
                "db_used":    db_used,
                "created_at": now_iso(),
            }
            history.append(assistant_entry)

            new_title = current_title
            if current_title == "New Conversation":
                new_title = generate_title(user_message)

            db.table("conversations").update({
                "conversationdata":  history,
                "conversationtitle": new_title,
                "updatedat":         now_iso(),
            }).eq("conversationid", conversation_id).execute()

    except WebSocketDisconnect:
        print(f"Client disconnected from conversation {conversation_id}")