---
name: run-tests
description: >-
  Use this skill when you need to verify Python backend code changes, ensure no regressions have occurred, or when you are explicitly asked to run unit/integration tests and check code coverage. It guides the agent through executing Pytest, analyzing coverage reports, and debugging common async testing pitfalls.
---

# Run and Analyze Tests Skill (Python FastAPI)

This skill provides a standard runbook for executing and troubleshooting automated tests in the **FastAPI Practice API** project.

## Execution Steps

### 1. Run the Test Suite with Coverage
Use the `run_command` tool to execute Pytest using `uv`:
```bash
uv run pytest --cov=app --cov-report=term-missing
```
- Wait for completion synchronously (e.g. `WaitMsBeforeAsync=10000`).
- Ensure all test cases pass (100% green).
- Verify the total coverage meets or exceeds the mandatory **85%** threshold.

### 2. Analyze the Output
* **Success (Exit Code 0)**: All tests passed with zero regressions. You may proceed with confidence.
* **Failure (Exit Code 1+)**: Investigate the failed assertions or errors.

### 3. Common Troubleshooting Scenarios

#### Scenario A: `MissingGreenlet: greenlet_spawn has not been called`
* **Cause**: SQLAlchemy ORM relationship attribute accessed lazily in an async context without eager loading.
* **Fix**: Update the repository query using `options(selectinload(Model.relationship))` so that related entities are pre-fetched during the query.

#### Scenario B: `RuntimeError: Task attached to a different loop`
* **Cause**: Event loop mismatch between test fixtures and asynchronous database engine.
* **Fix**: Ensure `pytest.ini` has `asyncio_mode = auto` and fixtures in `tests/conftest.py` yield a clean async session per test.

#### Scenario C: `IntegrityError: UNIQUE constraint failed`
* **Cause**: A test case failed to clean up inserted records or generated a colliding duplicate email/slug.
* **Fix**: Use `uuid.uuid4()` for unique test identifiers and verify the session rollback fixture in `conftest.py`.

#### Scenario D: `Coverage Threshold Dropped Below 85%`
* **Cause**: New business logic branches or error handlers were added without corresponding unit tests.
* **Fix**: Inspect the `Missing` column in the coverage table and write targeted test cases for uncovered branches in `tests/api/`.

### 4. Code Quality & Linting Verification
Before concluding any testing task, execute the Ruff linter:
```bash
uv run ruff check app/ tests/
```
Fix any formatting or unused import issues via `uv run ruff check --fix app/ tests/`.
