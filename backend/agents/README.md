# agents/

**What is this folder for?**  
**RAG (Retrieval-Augmented Generation) agents** used inside the RAG pipeline. Each agent has a single responsibility: classify intent, load memory, retrieve chunks, reason over the query, validate sources, generate the answer, or orchestrate the flow.

# Example

**What code should be inside here?**

- **`intent_agent.py`** — Classifies whether the user query is “legal” (needs RAG) or “casual” (general chat). Calls LLM or rules; returns intent label.
- **`memory_agent.py`** — Loads recent conversation history (from Redis or Supabase) for context. Returns list of prior messages.
- **`retriever_agent.py`** — Takes query (and optionally query expansion); uses embedding_service + Milvus to search; returns top-k chunks with scores and metadata (e.g. URL).
- **`query_reasoning_agent.py`** — Optional: rewrites or expands the user query for better retrieval (e.g. multi-hop reasoning).
- **`source_validation_agent.py`** — Validates or filters retrieved chunks (e.g. relevance score threshold, dedup). May retry retrieval if needed.
- **`generator_agent.py`** — Builds the prompt from query + retrieved sources + conversation history; calls LLM; returns generated answer (and optionally structured citations).
- **`orchestrator_agent.py`** — Coordinates the pipeline: intent → memory → (optional reasoning) → retriever → (optional validation) → generator. Returns final answer and sources.

Agents receive clients/services via constructor (e.g. llm_service, milvus_client, redis_client, supabase_client, embedding_service). They do not define HTTP routes.
