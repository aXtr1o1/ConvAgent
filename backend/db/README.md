# db/

**What is this folder for?**  
**Database and cache clients** used by the backend: Milvus (vector search), Redis (cache/session), Supabase (PostgreSQL for conversations and messages). Each client encapsulates connection, config, and cleanup.

# Example
**What code should be inside here?**

- **`__init__.py`** — Package marker; can expose `get_milvus()`, `get_redis()`, `get_supabase()` singletons or factories.
- **`milvus_client.py`** — Milvus client wrapper: connect (host, port, collection_name), search by vector (return top-k IDs and scores), close. Uses pymilvus. Used by retriever_agent / RAG service.
- **`redis_client.py`** — Redis connection: connect (host, port, db, password), get/set with optional TTL (e.g. cache, conversation context), close. Used for caching and session/context.
- **`supabase_client.py`** — Supabase client: connect (url, key), CRUD for conversations and messages (create, get by id, list by user_id, delete), normalize and store message sources. Used by conversation_service and message_service.

Config (hosts, ports, keys) comes from `config.py` (env), not hardcoded. Clients are initialized in `main.py` lifespan and passed into services.
