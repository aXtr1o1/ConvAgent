# collectors/

**What is this folder for?**  
**Data source adapters**: fetch raw legal content from external systems (e.g. Lovdata API, other APIs, or scrapers) and normalize it into a common document format so the rest of the pipeline (processors, storage) can work with it.

**What code should be inside here?**

- **`lovdata_collector.py`** — Lovdata-specific collector: call Lovdata API or parse Lovdata pages, handle pagination/auth if needed, normalize each item to a common shape (e.g. `{ "title": "...", "content": "...", "url": "...", "date": "..." }`). Yield or return a list of documents. Handle rate limits and errors.

Other collectors (e.g. `eurolex_collector.py`, `generic_api_collector.py`) can be added with the same interface: output a list of document dicts with at least title, content, and ideally url/source_id so chunks can be traced back. No chunking or embedding here—only fetching and normalizing.
