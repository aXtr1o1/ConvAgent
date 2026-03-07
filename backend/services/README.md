# services/

**What is this folder for?**  
**Business logic layer**: RAG pipeline, conversation CRUD, message persistence, LLM calls, and embeddings. Routes call services; services use db clients and agents. No HTTP here—only Python functions/classes.
# Example
**What code should be inside here?**

- **`rag_service.py`** — Main RAG flow: accept query + conversation_id + user_id; load memory (memory_agent); optionally run query_reasoning_agent; run retriever_agent; optionally source_validation_agent; run generator_agent (orchestrator). Stream events: `sources`, `token`, `complete` (with metadata: conversation_id, message_id, full_answer). Handle cache (Redis) and persist messages/conversations via conversation_service and message_service.
- **`conversation_service.py`** — Create conversation (user_id, title?), list by user_id, get by id (with messages), delete by id. Uses supabase_client (and optionally redis for list cache).
- **`message_service.py`** — Save message (conversation_id, role, content, sources?), get messages by conversation_id, normalize sources for storage. Uses supabase_client and optionally redis.
- **`llm_service.py`** — Wrapper for Azure/OpenAI: chat completion (streaming and non-streaming), title generation, scoring or classification if needed. Uses config for endpoint, key, deployment, temperature.
- **`embedding_service.py`** — Turn text into embedding vector (e.g. Azure OpenAI embeddings). Used by retriever_agent and ingestion. Uses config for embedding deployment and version.

Services are instantiated in `main.py` lifespan and injected into route modules via `set_services()` or similar.
