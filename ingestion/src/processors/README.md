# src/processors/

**What is this folder for?**  
**Text processing and chunking**: take raw documents (HTML, XML, or plain text) from collectors, clean and normalize them, then split into chunks suitable for embedding and retrieval. Output is a list of chunks with metadata (source URL, title) ready for the embedder and storage.

**What code should be inside here?**

- **`text_processor.py`** — Clean and normalize: strip HTML tags, decode entities, normalize whitespace, optional language detection. Input: raw string or document dict. Output: plain text (and maybe title, url) for chunking.
- **`chunker.py`** — Split long text into chunks: by character/token limit, by paragraph/section, or semantic (e.g. sentence boundaries). Preserve metadata per chunk (source_id, url, title). Optionally overlap chunks for better retrieval. Output: list of `{ "text": "...", "metadata": { ... } }`.
- **`embedder.py`** — Call the embedding API (e.g. Azure OpenAI embeddings) for each chunk or batch of chunks. Input: list of text chunks. Output: list of (chunk, vector) or (id, vector, metadata) for storage. Uses same embedding model/dimension as the backend so search works.

Processors are stateless and testable with sample inputs. They don’t connect to Milvus/Supabase—that’s in `storage/`.
