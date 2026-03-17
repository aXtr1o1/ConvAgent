# tests/

**What is this folder for?**  
**Automated tests** for the ingestion pipeline: collectors, processors (chunker, embedder, text_processor), storage (Milvus, Supabase), scheduler, and end-to-end runs.

**What code should be inside here?**

- **`__init__.py`** — Optional package marker.
- **`conftest.py`** — Pytest fixtures: sample raw documents, sample chunks, mock Milvus/Supabase or test instances, env overrides so tests don’t hit production APIs. Shared test config.
- **`test_collector.py`** — Test Lovdata (and other) collectors: mock HTTP responses, assert normalized document shape (title, content, url). Test pagination and error handling.
- **`test_embedding.py`** — Test embedder: mock embedding API, assert output dimension and batch behavior.
- **`test_*.py`** for processors — Test chunker (chunk sizes, overlap, metadata), text_processor (HTML strip, normalization). Use small fixtures.
- **`test_milvus_store.py`** / **`test_supabase_store.py`** — Test storage: use test Milvus/Supabase or mocks, assert insert/query behavior and idempotency.
- **`test_cron_scheduler.py`** / **`test_trigger_handler.py`** — Test scheduler and trigger handler invoke the pipeline with expected args; use mocks for the actual ingest.
- **`test_health.py`** — If there’s a health or status endpoint for the ingestion service, test it here.

Run with: `pytest tests/ -v`. Keep tests fast and isolated (mocks or test DBs).
