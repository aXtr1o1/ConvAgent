# src/storage/

**What is this folder for?**  
**Persistence** of processed chunks and their embeddings: write to Milvus (vector store) and optionally to Supabase (metadata, document index). Handles connection config, batch insert/upsert, and optionally checkpointing for resume.

**What code should be inside here?**

- **`milvus_store.py`** — Milvus client for ingestion: connect (host, port, collection), create collection/schema if not exists, insert or upsert (id, vector, optional scalar fields like source_url, title). Batch inserts for efficiency. Same collection name and dimension as the backend uses for search.
- **`supabase_store.py`** — Optional: write document/chunk metadata to Supabase (e.g. table of documents with id, source_url, title, chunk_count, updated_at) for debugging, UI, or dedup. Not required if only Milvus is used.

Checkpointing (e.g. last_run timestamp, last_doc_id) can live here or in `main.py` so the next run can resume. No embedding logic—storage receives already-computed vectors from the processors/embedder.
