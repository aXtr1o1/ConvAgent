# telemetry/

**What is this folder for?**  
**Observability**: OpenTelemetry tracing for the backend so you can measure API and LLM latency, and trace requests across the RAG pipeline.
# Example
**What code should be inside here?**

- **`tracing.py`** — Initialize OpenTelemetry: set up TracerProvider, export (e.g. OTLP or console), instrument FastAPI so each request gets a span. Optionally instrument LLM/embedding calls. Called once at app startup from `main.py` (before creating the FastAPI app). No route handlers—only setup code.

If you add metrics or logging, they can live here or in `utils/`.
