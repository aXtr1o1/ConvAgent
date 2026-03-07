# Ingestion

**What is this folder for?**  
The **data ingestion pipeline** for the Digirett RAG system. It collects legal content (e.g. from Lovdata or other sources), processes and chunks it, generates embeddings, and writes to Milvus (and optionally Supabase) so the backend can search it when answering user questions.

**What code should be inside here?**

- **`src/main.py`** — Entry point: parse CLI or config, run the pipeline once or on a schedule (e.g. call scheduler or run one-shot ingest).
- **`src/config.py`** — Settings from env: Milvus/Supabase/Redis URLs, embedding model, collection name, chunk size, batch size, API keys for data sources.
- **`src/scheduler/`** — Cron or trigger-based scheduling so ingestion runs periodically (e.g. daily) or on webhook/event.
- **`src/processors/`** — Text cleaning, chunking (by size or semantic boundaries), and optional normalization. Output: list of text chunks with metadata (source URL, title).
- **`src/storage/`** — Write chunks and embeddings to Milvus (vector store) and optionally metadata to Supabase. Handle idempotency and checkpoints.
- **`collectors/`** — Data source adapters: e.g. Lovdata collector (fetch from API or scrape), normalize to a common document format (title, content, url, date).
- **`data/`** — Local cache or checkpoint dir (e.g. raw fetched files, ingestion_state.json) so runs can resume. Usually gitignored except example files.
- **`tests/`** — Pytest tests for collectors, processors, storage, scheduler, and end-to-end pipeline.

Dependencies are in the repo root or a local requirements file. The backend reads from the same Milvus collection this pipeline writes to.
