# Testing, Code Quality & CI Verification Rules

These rules mandate test coverage standards, automated test isolation, and code linting requirements for the **FastAPI Practice (Blogging Platform API)**.

## 1. Test Suite Standards & Coverage Target
* **Testing Framework**: All automated tests are written with **`pytest`**, **`pytest-asyncio`**, and **`pytest-cov`**.
* **Mandatory Coverage Threshold**:
  * Code coverage must **never drop below 85%**.
  * Core modules (`security.py`, `deps.py`, exceptions, models, and repositories) must maintain high coverage (≥90%).
* **Execution Command**: Run test suite using `uv`:
  ```bash
  uv run pytest --cov=app --cov-report=term-missing
  ```

## 2. Test Isolation & In-Memory Database
* **Zero Production DB Contamination**: Tests must NEVER run against or touch the live PostgreSQL database.
* **In-Memory SQLite Async**: The test suite in [`tests/conftest.py`](file:///Volumes/MacData/fastapi-training/tests/conftest.py) must utilize an isolated in-memory engine (`sqlite+aiosqlite:///:memory:`).
* **Dependency Override**:
  * Override the `get_db` dependency via `app.dependency_overrides[get_db]`.
  * Every test case receives a fresh, clean database session that automatically rolls back upon test completion, guaranteeing zero state bleeding between tests.

## 3. Negative Testing Mandate
* **Beyond Happy Path**: Tests must actively verify defensive guardrails. At least 40% of the test suite must cover negative test scenarios:
  * **401 Unauthorized**: Missing headers, malformed tokens, or expired JWTs.
  * **403 Forbidden**: Cross-user post edits/deletions, normal users trying to list users, or deactivated users attempting actions.
  * **404 Not Found**: Non-existent resource lookups (posts, users, categories).
  * **409 Conflict**: Duplicate category slugs or duplicate email collisions.
  * **400 Bad Request**: Administrator self-lock attempts.
  * **422 Unprocessable Entity**: Invalid or empty payload fields.

## 4. Linter & Static Code Quality
* **Ruff Formatting & Linting**: Code style and imports must comply with **Ruff**:
  ```bash
  uv run ruff check app/ tests/
  uv run ruff format --check app/ tests/
  ```
* **Pre-Push Gate**: Never commit or push code that fails either `pytest` or `ruff check`.
