# src/

**What is this folder for?**  
Core **ingestion application** code: config, main entry point, and the subpackages for scheduling, processing, and storage. This is where the pipeline logic lives (not the collectors, which are in `collectors/`).

**What code should be inside here?**

- **`config.py`** — Load settings from env (e.g. pydantic-settings or dotenv): Milvus host/port/collection, Supabase URL/key, embedding deployment, chunk size, batch size, source API keys, paths for data/checkpoints.
- **`main.py`** — Entry point: initialize config, optionally start scheduler or run a one-shot ingest. Orchestrate: load/schedule job → run collectors → run processors (chunk) → run embedder → run storage (Milvus/Supabase). Log progress and errors.
- **`scheduler/`** — When and how often to run ingestion (cron, interval, or event-triggered). Invokes the pipeline (e.g. calls main ingest function).
- **`processors/`** — Text processing and chunking: clean HTML/text, split into chunks (by token count or semantic boundaries), attach metadata (source, title). Feed into embedder.
- **`storage/`** — Persist chunks and embeddings: insert/upsert into Milvus, optionally write metadata to Supabase. Checkpointing and resume logic can live here or in main.

No HTTP server here—ingestion is typically a CLI script or daemon that runs on a schedule.
