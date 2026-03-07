# data/

**What is this folder for?**  
**Local data and working files** used by the ingestion pipeline: raw fetched content, cache, or checkpoint files so runs can resume. This folder is typically **gitignored** (except this README or example files) so large or sensitive data isn’t committed.

**What code should be inside here?**

- No application code—only data files produced or consumed by the pipeline.
- **`checkpoints/`** — Checkpoint or state files (e.g. `ingestion_state.json`, last_run timestamp, last document ID) so the next run can skip already-ingested content or resume from a failure.
- Optional: **`raw/`** or **`cache/`** — Cached API responses or downloaded files if you want to avoid re-fetching on every run.

Keep this directory in .gitignore except for README or sample checkpoint schema if you want to document the format.
