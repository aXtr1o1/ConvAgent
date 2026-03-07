# src/scheduler/

**What is this folder for?**  
**Scheduling** of the ingestion pipeline: run it on a cron schedule (e.g. daily), at a fixed interval, or when triggered by an event (webhook, queue, file drop). Decides *when* to run; the actual ingest logic is in main/processors/storage.

**What code should be inside here?**

- **`__init__.py`** — Package marker; can expose `Scheduler` or `run_scheduled`.
- **`cron_scheduler.py`** — Use APScheduler (or similar) to register cron jobs (e.g. "0 2 * * *" for 2 AM daily). On tick, call the main ingest function or trigger the pipeline. Handle timezone and logging.
- **`trigger_handler.py`** — If ingestion can be triggered by HTTP webhook, queue message, or file event: parse the trigger, validate, and invoke the same ingest entry point so one code path runs the pipeline. Optional: rate limit or idempotency key.

No business logic for chunking or embedding—only "when to run" and "call the pipeline."
