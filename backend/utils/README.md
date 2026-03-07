# utils/



**What is this folder for?**  
**Shared utilities** used across the backend: logging, helpers, constants. No business logic and no route definitions.

# Example
**What code should be inside here?**

- **`logger.py`** — Setup for Python logging: format, level, optional file handler. Expose a `setup_logger(name, level)` or similar used by `main.py` and other modules so log output is consistent (e.g. level, timestamp, module name).

Other helpers (e.g. date formatting, safe JSON parse, retry decorators) can go here if they are generic and used in more than one place.
