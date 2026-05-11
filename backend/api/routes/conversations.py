from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from backend.utils.utilities import db, now_iso, to_ist
from dateutil import parser as dtparser
from backend.schemas.conversation_schema import CreateConversationRequest, SendMessageRequest
from datetime import datetime, timezone
from backend.agents.casual_llm import generate_title
from backend.agents.agent import (
     dct_code_extraction_agent,
    dct_code_decision_agent,
    reply_agent,
    retrieve_from_milvus,
    casual_agent
)
from pymilvus import Collection
from ingestion.data.ingestion.retreival import connect_milvus
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


@router.post("/messages/{conversation_id}")
def send_message(conversation_id: str, body: SendMessageRequest):
    logger.info("Received message for conversation %s: %s", conversation_id, body.message[:100])
    res = db.table("conversations") \
        .select("conversationtitle, conversationdata") \
        .eq("conversationid", conversation_id) \
        .execute()
    

    if not res.data:
        db.table("conversations").insert({
            "conversationid": conversation_id,
            "conversationtitle": generate_title(body.message),
            "conversationdata": [],
            "updatedat": now_iso(),
        }).execute()
        

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

    llm_history = [{"role": m["role"], "content": m["content"]} for m in history[-5:] if "Priority List" not in m.keys()]

    for i in llm_history:
        print(f"I: {i}")
        if i.get("priority_list"):
            prior_list = i.get("priority_list")
        else:
            prior_list = {}
    logger.info(f"Prior List: {prior_list}")
    extrac_res = dct_code_extraction_agent(
    conversation_history=llm_history,
    message=body.message,
    prior_list=prior_list
)
    logger.info(f"Extraction Result: {extrac_res}")

    if extrac_res["status"] != "success":
        logger.info(f"Extraction Failed: {extrac_res}")
        assistant_reply = casual_agent(llm_history, body.message)
        logger.info(f"Casual Agent Reply: {assistant_reply}")
        sources = []
        db_used = "none"
        assistant_entry = {
        "message_id": str(uuid.uuid4()),
        "role":       "assistant",
        "content":    assistant_reply.get("data", {}).get("response", ""),
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

    else:
        extracted = extrac_res["data"]
        logger.info(f"Extracted: {extracted}")

        if not extracted.get("dtc_codes"):
            assistant_reply = casual_agent(llm_history, body.message)
            sources = []
            db_used = "none"
            

        else:
           
            prior_list = {
                f"dtc{i+1}": dtc
                for i, dtc in enumerate(extracted["dtc_codes"])
            }
            
            history.append({"Priority List": prior_list})
            logger.info(f"History: {history}")

            decision_res = dct_code_decision_agent(
                conversation_history=llm_history,
                message=body.message,
                prior_list=prior_list
            )
            logger.info(f"Decision Result Casual Agent: {decision_res}")
            if decision_res["status"] != "success":
                assistant_reply = {"response": "Alright, I’m not getting a clear direction yet. What exact symptom or code are you seeing?"}    
                sources = []
                db_used = "none"

            else:
                decision_data = decision_res["data"]
                query = decision_data.get("search_query", "") or body.message
                dtc_code = decision_data.get("filters", {}).get("dtc_code", "")
                logger.info(f"Connecting to Milvus")
                logger.info(f"Query: {query}")
                logger.info(f"DTC Code: {dtc_code}")
                
                connect_milvus()
                collection = Collection("dtc_embeddings")

                retrieved_steps = retrieve_from_milvus(
                    collection=collection,
                    query=query,
                    dtc_code=dtc_code,
                    top_k=5
                )
                logger.info(f"Reterived Context: {retrieved_steps}")

                reply_res = reply_agent(
                    conversation_history=llm_history,
                    message=body.message,
                    retrieved_steps=retrieved_steps
                )

                if reply_res["status"] == "success":
                    assistant_reply = reply_res["data"]
                else:
                    assistant_reply = {"response": "Hmm, something’s off. Let’s retry — can you describe the issue again?"}

                sources = [
                    {
                        "dtc_code": r["dtc_code"],
                        "step_number": r["step_number"],
                        "score": r["score"]
                    }
                    for r in retrieved_steps
                ]

                db_used = "milvus"
        

    

    # ── Check active session ──────────────────────────────────────────────
    
    # ── Save and return ───────────────────────────────────────────────────
    assistant_entry = {
        "message_id": str(uuid.uuid4()),
        "role":       "assistant",
        "content":    assistant_reply.get("response", ""),
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
                for m in history[-5:]
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
                supabase_tool=None,
              
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