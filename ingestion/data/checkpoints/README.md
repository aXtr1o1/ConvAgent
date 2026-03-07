# data/checkpoints/

**What is this folder for?**  
**Checkpoint and state files** for the ingestion pipeline: e.g. last run time, last processed document ID, or cursor position. Used so the next run can **resume** instead of re-ingesting everything, and to avoid duplicate writes to Milvus.

**What code should be inside here?**

- No application code—only JSON or other state files written by the pipeline (e.g. `ingestion_state.json` with `last_run`, `last_doc_id`, or list of completed source IDs).
- The ingestion **code** that reads/writes checkpoints lives in `src/main.py` or `src/storage/`; this directory is just the default location for those files.

Typically gitignored. If you document the schema (e.g. for `ingestion_state.json`), you can add a sample or schema file here.
