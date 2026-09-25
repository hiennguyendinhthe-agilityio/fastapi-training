---
trigger: always_on
---

# Async Concurrency, Performance & Database Rules

These rules dictate asynchronous programming practices, database connection pooling, and performance optimizations for the **FastAPI Practice (Blogging Platform API)**.

## 1. End-to-End Non-Blocking Asynchronous Execution
* **Native `async def` Enforcement**: All API route handlers and repository methods performing I/O operations must be declared with `async def`.
* **Asynchronous Driver**: PostgreSQL operations must exclusively use the high-performance **`asyncpg`** driver via `postgresql+asyncpg://`.
* **Zero Blocking Calls in Event Loop**:
  * NEVER use `time.sleep()` ➡️ use `asyncio.sleep()`.
  * NEVER use synchronous HTTP libraries like `requests` or `urllib3` ➡️ use asynchronous `httpx.AsyncClient`.
  * NEVER perform synchronous file or CPU-bound blocking I/O on the main thread. If synchronous operations are unavoidable, offload them via `anyio.to_thread.run_sync()`.

## 2. Eliminating the N+1 Query Problem in Async ORM
* **No Implicit Lazy Loading**: In SQLAlchemy 2.0 Async, implicit lazy loading is disabled and will immediately crash the request with `sqlalchemy.exc.MissingGreenlet`.
* **Explicit Eager Loading Mandate**:
  * For **Many-to-Many** and **One-to-Many** relationships (e.g., `Post.categories`, `User.posts`), always use **`selectinload()`** to execute an optimized batch query (`WHERE id IN (...)`) avoiding Cartesian product overhead.
  * For **One-to-One** relationships (e.g., `User.profile`), use **`selectinload()`** or **`joinedload()`**.

## 3. Database Session Lifecycle & Pool Safety
* **Scoped Dependency Injection**: Database sessions must be injected via the FastAPI dependency `get_db` ([`app/core/database.py`](file:///Volumes/MacData/fastapi-training/app/core/database.py)).
* **Safe Session Management**:
  * Every session must be isolated per HTTP request using an async context manager.
  * Automatic rollback must trigger upon unhandled exceptions before releasing the connection back to the connection pool.
  * Never share an `AsyncSession` across multiple concurrent background tasks or worker threads.

## 4. Modern Dependency & Virtual Environment Management
* Use **`uv`** for managing dependencies, lockfiles, and environment execution (`uv run`, `uv add`, `uv sync`).

