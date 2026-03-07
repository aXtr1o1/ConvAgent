# tests/

**What is this folder for?**  
**Automated tests** for the backend: API endpoint tests, service tests, and any shared test fixtures or clients.
# Example
**What code should be inside here?**

- **`__init__.py`** — Optional package marker for the test package.
- **`conftest.py`** — Pytest fixtures: test client (e.g. `TestClient(app)`), test DB/cache clients or mocks, env overrides so tests don’t hit real Azure/Milvus/Supabase unless needed.
- **`test_api.py`** — End-to-end or integration tests: health returns 200; create conversation returns conversation_id; list conversations; get conversation with messages; delete conversation; WebSocket chat sends query and receives token/complete events. Use the test client and optionally a test database.
- **`test_suite.py`** or **`test_services.py`** — Unit or integration tests for services (e.g. RAG service, conversation service) and agents, with mocked LLM/DB if needed.

Run with: `pytest tests/ -v` (from backend or repo root). Keep tests independent and repeatable (e.g. use test DB or mocks).
