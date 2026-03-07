# Backend

**What is this folder for?**  
This is the **Digirett backend** (Lovdata RAG API). It serves the REST and WebSocket endpoints that the frontend calls: conversations, messages, streaming chat, health check. It runs the RAG pipeline (retrieve legal content from the vector DB, generate answers with the LLM, return sources).

# Example
**What code should be inside here?**

- **`main.py`** — FastAPI app creation, CORS, lifespan (connect to Milvus, Redis, Supabase), router includes. Entry point: `uvicorn main:app`.
- **`config.py`** — Pydantic settings loaded from `.env` (API, Azure OpenAI, Milvus, Supabase, Redis, RAG settings, rate limits).
- **`api/`** — HTTP and WebSocket route modules (health, conversations, messages, chat).
- **`services/`** — Business logic: RAG pipeline, conversation CRUD, message persistence, LLM and embedding calls.
- **`agents/`** — RAG agents: intent, memory, retriever, query-reasoning, source-validation, generator, orchestrator.
- **`db/`** — Clients for Milvus, Redis, Supabase (connect, query, close).
- **`schemas/`** — Pydantic request/response models for the API.
- **`telemetry/`** — OpenTelemetry tracing (API + LLM latency).
- **`utils/`** — Logging and other helpers.
- **`tests/`** — Pytest tests for API and services.
- **`core/`** — Optional shared core logic used across the app.

See the repo root **requirements.txt** for Python dependencies. Frontend contract: **frontend/digirett-frontend/API-ENDPOINTS-SPEC.md**.
