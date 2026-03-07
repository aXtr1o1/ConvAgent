# api/

**What is this folder for?**  
Holds the **HTTP and WebSocket route definitions** for the backend. All URL endpoints under `/api/v1` are defined here (health, conversations, messages, chat).

# Example
**What code should be inside here?**

- **`__init__.py`** — Package marker; can re-export routers for `main.py`.
- **`routes/`** — One module per route group (e.g. `health.py`, `conversations.py`, `messages.py`, `chat.py`). Each module defines an `APIRouter`, registers handlers (GET/POST/DELETE or WebSocket), and uses services injected from `main.py` (e.g. conversation_service, message_service, rag_service). No business logic here—only request/response handling and calling services.
