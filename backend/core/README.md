# core/

**What is this folder for?**  
Optional **shared core logic** used across the backend: constants, base classes, or shared domain logic that doesn’t belong in a single service or agent. Can be left empty if you don’t need it.

# Example
**What code should be inside here?**

- **`__init__.py`** — Package marker; can re-export public names.
- **Constants** — e.g. default model names, max lengths, error codes used in multiple places.
- **Base classes or mixins** — if several agents or services share the same interface or helpers.
- **Domain types** — if you want a small shared layer between API schemas and DB (e.g. enums, value objects). Don’t duplicate Pydantic request/response models from `schemas/` here unless they are truly shared and minimal.

If the project stays small, you may not need this folder; services and agents can import from each other or from `utils/`.
