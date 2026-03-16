from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from backend.utils.utilities import db, now_iso, to_ist
from dateutil import parser as dtparser
from backend.schemas.conversation_schema import CreateConversationRequest, SendMessageRequest 
from datetime import datetime, timezone
from backend.agents.casual_llm import generate_bot_reply, generate_bot_reply_stream, generate_title
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
    get_active_session_for_conversation,                                           
)                                                                                  

router = APIRouter()

# ── Diagnostic routing helper ─────────────────────────────────────────────────
DTC_PATTERN  = re.compile(r'\b(P[0-9A-Fa-f]{4}(?:-[0-9A-Fa-f]{2})?)\b')         
CANCEL_WORDS = {"cancel", "stop", "exit", "quit", "abort"}                        

async def handle_diagnostic_routing(message: str, conversation_id: str):          
    msg_lower = message.strip().lower()                                            
                                                                                   
    # Cancel intent                                                                
    if any(w in msg_lower for w in CANCEL_WORDS):                                 
        active = get_active_session_for_conversation(conversation_id)              
        if active:                                                                 
            from ingestion.retrieval.session_handler import close_session     
            close_session(active["session_id"])                                    
            return {"response": "Diagnostic session cancelled. How else can I help?"}  
                                                                                   
    # Already in a session — treat message as YES/NO answer                       
    active = get_active_session_for_conversation(conversation_id)                  
    if active:                                                                     
        result = advance_session(active["session_id"], message)                   
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
                                                                                   
    return None   # no diagnostic match — fall through to normal LLM              
# ─────────────────────────────────────────────────────────────────────────────  


# 1. CREATE CONVERSATION
@router.post("/conversations")
def create_conversation(body: CreateConversationRequest):
    ts = now_iso()
    res = db.table("conversations").insert({
        "userid": body.user_id,
        "conversationtitle": "New Conversation",
        "conversationdata": [],
        "updatedat": ts,
    }).execute()

    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create conversation.")

    row = res.data[0]
    return {
        "conversation_id": str(row["conversationid"]),
        "user_id": str(row["userid"]),
        "title": row["conversationtitle"],
        "created_at": to_ist(row["createdat"]),
        "updated_at": to_ist(row.get("updatedat") or row["createdat"]),
    }


def _is_valid_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except (ValueError, TypeError):
        return False


# 2. LIST CONVERSATIONS FOR A USER
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
            "title": row.get("conversationtitle", "New Conversation"),
            "updated_at": to_ist(updated_at),
            "_sort_key": sort_dt,
        })

    conversations.sort(key=lambda x: x["_sort_key"], reverse=True)

    for c in conversations:
        c.pop("_sort_key")

    return {"conversations": conversations}


# 3. GET conversation with full messages
@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    res = db.table("conversations") \
        .select("conversationid, conversationtitle, conversationdata, updatedat, createdat") \
        .eq("conversationid", conversation_id) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    row = res.data[0]
    raw_messages = row.get("conversationdata") or []
    updated_at = row.get("updatedat") or row.get("createdat")

    messages = []
    for m in raw_messages:
        if not isinstance(m, dict):
            continue
        msg = {
            "message_id": m.get("message_id", str(uuid.uuid4())),
            "role": m.get("role", ""),
            "content": m.get("content", ""),
            "created_at": to_ist(m.get("created_at", "")),
        }
        if m.get("role") == "assistant":
            msg["sources"] = m.get("sources", [])
        messages.append(msg)

    return {
        "conversation_id": str(row["conversationid"]),
        "title": row.get("conversationtitle", "New Conversation"),
        "updated_at": to_ist(updated_at),
        "messages": messages,
    }


# 4. DELETE CONVERSATION
@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    db.table("conversations") \
        .delete() \
        .eq("conversationid", conversation_id) \
        .execute()
    return {"success": True}


# 5. SEND MESSAGE + GET LLM REPLY
@router.post("/messages/{conversation_id}")
def send_message(conversation_id: str, body: SendMessageRequest):
    res = db.table("conversations") \
        .select("conversationtitle, conversationdata") \
        .eq("conversationid", conversation_id) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    row = res.data[0]
    current_title = row.get("conversationtitle", "New Conversation")
    history = row.get("conversationdata") or []
    ts = now_iso()

    user_entry = {
        "message_id": str(uuid.uuid4()),
        "role": "user",
        "content": body.message,
        "created_at": ts,
    }
    history.append(user_entry)

    llm_history = [{"role": m["role"], "content": m["content"]} for m in history[:10]]

    # ── Diagnostic check (run in new loop; endpoint runs in thread pool) ───   
    import asyncio
    try:
        diagnostic = asyncio.run(handle_diagnostic_routing(body.message, conversation_id))
    except RuntimeError:
        diagnostic = None
    if diagnostic:                                                              
        assistant_reply = diagnostic["response"]                               
    else:                                                                       
        # Enrich LLM with semantic context                                     
        chunks  = semantic_search(body.message, top_k=4)                       
        context = format_context_for_llm(chunks)                               
        if context:                                                             
            llm_history.insert(0, {"role": "system", "content": context})     
        assistant_reply = generate_bot_reply(llm_history)                      
    # ─────────────────────────────────────────────────────────────────────── 

    assistant_entry = {
        "message_id": str(uuid.uuid4()),
        "role": "assistant",
        "content": assistant_reply,
        "sources": [],
        "created_at": now_iso(),
    }
    history.append(assistant_entry)

    new_title = current_title
    if current_title == "New Conversation":
        new_title = generate_title(body.message)

    db.table("conversations").update({
        "conversationdata": history,
        "conversationtitle": new_title,
        "updatedat": now_iso(),
    }).eq("conversationid", conversation_id).execute()

    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "message_id": m.get("message_id", ""),
                "role": m.get("role", ""),
                "content": m.get("content", ""),
                "created_at": to_ist(m.get("created_at", "")),
                **( {"sources": m.get("sources", [])} if m.get("role") == "assistant" else {} )
            } for m in history
        ]
    }


# 6. WEBSOCKET
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

            row = res.data[0]
            current_title = row.get("conversationtitle", "New Conversation")
            history = row.get("conversationdata") or []
            ts = now_iso()

            user_entry = {
                "message_id": str(uuid.uuid4()),
                "role": "user",
                "content": user_message,
                "sources": [],
                "created_at": ts,
            }
            history.append(user_entry)

            llm_history = [{"role": m["role"], "content": m["content"]} for m in history]

            # ── Diagnostic check ──────────────────────────────────────────   
            diagnostic = await handle_diagnostic_routing(                      
                user_message, conversation_id                                  
            )                                                                  
            if diagnostic:                                                     
                full_reply = diagnostic["response"]                            
                await websocket.send_text(full_reply)                         
                await websocket.send_text("[DONE]")                           
            else:                                                              
                # Enrich LLM with semantic context                             
                chunks  = semantic_search(user_message, top_k=4)              
                context = format_context_for_llm(chunks)                      
                if context:                                                    
                    llm_history.insert(0, {"role": "system", "content": context})  
                                                                               
                # Stream reply — unchanged from your original                  
                full_reply = ""
                for chunk in generate_bot_reply_stream(llm_history):
                    full_reply += chunk
                    await websocket.send_text(chunk)
                await websocket.send_text("[DONE]")
            # ─────────────────────────────────────────────────────────────── 

            assistant_entry = {
                "message_id": str(uuid.uuid4()),
                "role": "assistant",
                "content": full_reply,
                "sources": [],
                "created_at": now_iso(),
            }
            history.append(assistant_entry)

            new_title = current_title
            if current_title == "New Conversation":
                new_title = generate_title(user_message)

            db.table("conversations").update({
                "conversationdata": history,
                "conversationtitle": new_title,
                "updatedat": now_iso(),
            }).eq("conversationid", conversation_id).execute()

    except WebSocketDisconnect:
        print(f"Client disconnected from conversation {conversation_id}")