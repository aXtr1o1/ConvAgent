# api/routes/

**What is this folder for?**  
One file per **route group**: health, conversations, messages, chat (including WebSocket). Each file defines FastAPI route handlers that the main app mounts under `/api/v1`.
# Example
**What code should be inside here?**

- **`health.py`** — `GET /health` (and optionally `/ready`). Returns status of Milvus, Redis, Supabase, LLM. Uses shared clients injected from `main.py`.
- **`conversations.py`** — `POST /conversations` (create), `GET /conversations/user/{user_id}` (list), `GET /conversations/{id}` (get one with messages), `DELETE /conversations/{id}`. Uses conversation_service and message_service.
- **`messages.py`** — `GET /messages/{conversation_id}` to list messages for a conversation. Uses message_service.
- **`chat.py`** — WebSocket ` /chat/ws`: accept connection, receive JSON `{ query, user_id, conversation_id?, ... }`, stream back events (`token`, `sources`, `complete`, `error`). Optional REST `POST /chat/stream` for SSE. Uses rag_service, conversation_service, message_service, llm_service.

All routes use Pydantic schemas from `schemas/` for request/response bodies. Rate limiting (e.g. SlowAPI) can be applied per route.
