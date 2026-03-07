# schemas/

**What is this folder for?**  
**Pydantic models** for API request bodies and response bodies. Used by FastAPI for validation, serialization, and OpenAPI docs.
# Example
**What code should be inside here?**

- **`requests.py`** — Incoming payloads, e.g.: `ConversationCreate` (user_id, title?), `ChatRequest` (query, user_id, conversation_id?, top_k?, temperature?), any other request body models. Use `Field()` for descriptions and defaults.
- **`responses.py`** — Response models, e.g.: `ConversationResponse` (conversation_id, title, created_at, updated_at), `MessageResponse` (message_id, role, content, sources?, created_at), `ConversationHistoryResponse` (conversation + messages list), health response (status, version, *_connected flags). Use `Field()` and optional types so frontend contract is clear.

These schemas should match the frontend API spec (see **frontend/digirett-frontend/API-ENDPOINTS-SPEC.md**). Export them from here and import in `api/routes/*.py`.
