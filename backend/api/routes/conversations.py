from fastapi import APIRouter, HTTPException
from backend.agents.casual_llm import generate_bot_reply, generate_title
from backend.utils.utilities import db, now_iso, to_ist
from dateutil import parser as dtparser
from backend.schemas.conversation_schema import CreateConversationRequest, SendMessageRequest 
from datetime import datetime, timezone
from dateutil import parser as dtparser
import uuid

router = APIRouter()

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


# 2. LIST CONVERSATIONS FOR A USER
@router.get("/conversations/user/{user_id}")
def list_conversations(user_id: str):
    res = db.table("conversations") \
        .select("conversationid, conversationtitle, updatedat, createdat") \
        .eq("userid", user_id) \
        .execute()

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

    # Sort by parsed datetime, not string
    conversations.sort(key=lambda x: x["_sort_key"], reverse=True)

    # Remove the internal sort key before returning
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
        messages.append({
            "message_id": m.get("message_id", str(uuid.uuid4())),
            "role": m.get("role", ""),
            "content": m.get("content", ""),
            "sources": m.get("sources", []),
            "created_at": to_ist(m.get("created_at", "")),
        })

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
        "sources": [],
        "created_at": ts,
    }
    history.append(user_entry)

    llm_history = [{"role": m["role"], "content": m["content"]} for m in history]
    assistant_reply = generate_bot_reply(llm_history)

    assistant_entry = {
        "message_id": str(uuid.uuid4()),
        "role": "assistant",
        "content": assistant_reply,
        "sources": [],
        "created_at": now_iso(),
    }
    history.append(assistant_entry)

    # Keep retrying title until user says something meaningful
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
            {"role": m["role"], "content": m["content"]} for m in history
        ]
    }