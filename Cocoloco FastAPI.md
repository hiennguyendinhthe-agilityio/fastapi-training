# 📋 Cocoloco FastAPI — Full Task List

> Complete list of tasks from project initialization to final delivery.
> Review and report back if anything is missing.

---

## Phase 1 — Project Setup & Infrastructure

### 1.1 Initialize Project ✅ Done — Sep 24, 2026
- [x] Create `fastapi-training/` directory and initialize git repository
- [x] Initialize project with `uv init` → project name: `cocoloco-api`
- [x] Create virtual environment with `uv venv` → Python 3.13.2
- [x] Configure `pyproject.toml` (name, version, python ≥ 3.12)

### 1.2 Install Dependencies ✅ Done — Sep 24, 2026
- [x] `fastapi[standard]` — v0.141.1 ✅
- [x] `uvicorn` — v0.53.0 ✅
- [x] `sqlalchemy[asyncio]` — v2.0.54 ✅
- [x] `asyncpg` — v0.31.0 ✅
- [x] `alembic` — v1.20.0 ✅
- [x] `pydantic-settings` — v2.15.0 ✅
- [x] `pyjwt[crypto]` + `cryptography` — v2.15.0 / v50.0.1 ✅
- [x] `httpx` — v0.28.1 ✅
- [x] `pytest` + `pytest-asyncio` + `pytest-cov` — v9.1.1 / v1.4.0 / v7.1.0 ✅
- [x] `aiosqlite` — v0.22.1 ✅
- [x] `ruff` — v0.16.8 ✅ (linter)
- [x] `pyright` — v1.1.414 ✅ (type checker)

### 1.3 Environment Configuration ✅ Done — Sep 25, 2026
- [x] Create `.env.example` with: `DATABASE_URL`, `CLERK_JWKS_URL`, `ENVIRONMENT`
- [x] Create `.env` local file (never commit to git)
- [x] Add `.env` to `.gitignore` — ✅ already added in `.gitignore`

### 1.4 Docker — PostgreSQL 16 ✅ Done — Sep 25, 2026
- [x] Create `docker-compose.yml` with `postgres:16` service
- [x] Configure: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- [x] Mount volume to persist data (`pgdata`)
- [x] Verify connection: `docker compose up -d` and ping DB

### 1.5 Project Structure ✅ Done — Sep 25, 2026
- [x] Create full directory tree following Clean Architecture
- [x] Add `__init__.py` to all packages

### 1.6 App Entrypoint ✅ Done — Sep 25, 2026
- [x] Create `app/main.py` — initialize `FastAPI()` with title, version, description
- [x] Configure `lifespan` context manager (startup/shutdown hooks)
- [x] Add CORS middleware (allow Flutter/web frontend to call API)
- [x] Verify server starts: `uv run uvicorn app.main:app --reload`
- [x] Verify `http://localhost:8000/docs` renders Swagger UI

---

## Phase 2 — Database Models & Migrations

### 2.1 Core Database Setup ✅ Done — Sep 28, 2026
- [x] Create `app/core/database.py` — `async_engine`, `AsyncSessionLocal`
- [x] Create `get_db` async dependency (generator, auto-rollback on error)
- [x] Create `app/models/base.py` — `TimestampedBase` with `created_at`, `updated_at`

### 2.2 User Model 🔜 Next
- [ ] Create `app/models/user.py`
- [ ] Define `UserRole` enum: `ADMIN`, `USER`
- [ ] Fields: `id` (UUID PK), `clerk_id` (unique), `email` (unique), `full_name`, `role`, `is_active`
- [ ] Relationship: `orders` → `back_populates`

### 2.3 Product Model
- [ ] Create `app/models/product.py`
- [ ] Define `CategoryType` enum: `coffee`, `pastry`, `bundle`, `seasonal`
- [ ] Fields: `id`, `name`, `description`, `price` (Numeric), `image_url`, `category`, `is_available`

### 2.4 Order & OrderItem Models
- [ ] Create `app/models/order.py`
- [ ] Define `OrderStatus` enum: `PENDING`, `CONFIRMED`, `COMPLETED`, `CANCELLED`
- [ ] `Order` fields: `id`, `user_id` (FK → users.id), `status`, `total_amount`, `ordered_at`
- [ ] `OrderItem` fields: `id`, `order_id` (FK), `product_id` (FK), `quantity`, `unit_price`
- [ ] Relationships: `Order.items` (`selectinload`), `Order.user` (`joinedload`)

### 2.5 Alembic Setup & Migrations
- [ ] Run `alembic init alembic`
- [ ] Configure `alembic/env.py`: async engine + import all models
- [ ] Generate first migration: `alembic revision --autogenerate -m "init: users, products, orders"`
- [ ] Apply migration: `alembic upgrade head`
- [ ] Verify all tables are created in PostgreSQL

### 2.6 Seed Data
- [ ] Create seed script with Cocoloco products:
  - Cappuccino — `$3.00` — `coffee`
  - Croissant — `$3.00` — `pastry`
  - Breakfast Bundle — `$12.00` — `bundle`
  - Latte Art Pour — `$4.00` — `coffee`
  - Fresh Pasta — `$8.00` — `seasonal`
  - Fruit Market Bowl — `$6.00` — `seasonal`
- [ ] Run seed script and verify data in DB

---

## Phase 3 — Authentication & RBAC

### 3.1 Pydantic Settings
- [ ] Create `app/core/config.py` with `class Settings(BaseSettings)`
- [ ] Load from `.env`: `DATABASE_URL`, `CLERK_JWKS_URL`, `ENVIRONMENT`
- [ ] Singleton pattern: `get_settings()` with `@lru_cache`

### 3.2 Clerk JWKS Verification
- [ ] Create `app/core/security.py`
- [ ] `fetch_jwks_client()` — create `PyJWKClient` with LRU cache (5-min TTL)
- [ ] `verify_clerk_token(token) -> dict` — decode & verify RS256 JWT
- [ ] Handle errors: `ExpiredSignatureError`, `InvalidTokenError`, missing `sub` claim
- [ ] Unit test: valid token → decoded payload; invalid token → `HTTPException 401`

### 3.3 Global Exception Handlers
- [ ] Create `app/core/exceptions.py`
- [ ] `401 Unauthorized` handler — token missing or invalid
- [ ] `403 Forbidden` handler — insufficient permissions or account disabled
- [ ] `404 Not Found` handler — resource does not exist
- [ ] `422 Unprocessable Entity` handler — Pydantic validation error
- [ ] Register all handlers in `app/main.py`

### 3.4 Dependency Injection
- [ ] Create `app/api/deps.py`
- [ ] `get_current_user(token, db)`:
  - Extract Bearer token from `Authorization` header
  - Verify with `verify_clerk_token()`
  - Fetch `User` from DB by `clerk_id`
  - Check `is_active` → raise `403` if account is disabled
- [ ] `require_admin(current_user)` → raise `403` if role ≠ `ADMIN`

### 3.5 Auth Sync Endpoint
- [ ] Create `app/api/v1/auth.py`
- [ ] `POST /api/v1/auth/sync` — upsert user into local DB after Clerk login
- [ ] Return `UserResponse`
- [ ] Test: valid token → user created; second call → updated, no duplicate

---

## Phase 4 — Users API

### 4.1 Pydantic Schemas
- [ ] Create `app/schemas/pagination.py` — generic `PageResponse[T]` model
- [ ] Create `app/schemas/user.py`:
  - `UserResponse` (id, email, full_name, role, is_active, created_at)
  - `UserUpdateRequest` (full_name: optional str)
  - `UserStatusRequest` (is_active: bool)

### 4.2 Repository
- [ ] Create `app/repositories/user_repo.py`:
  - `get_by_id(db, user_id) -> User | None`
  - `get_by_clerk_id(db, clerk_id) -> User | None`
  - `upsert(db, clerk_id, email, full_name) -> User`
  - `update(db, user, data: UserUpdateRequest) -> User`
  - `set_status(db, user, is_active: bool) -> User`
  - `get_all(db, page, size) -> PageResponse[UserResponse]`

### 4.3 Router & Endpoints
- [ ] Create `app/api/v1/users.py`
- [ ] `GET /api/v1/users/me` — get own profile
- [ ] `PUT /api/v1/users/me` — update own `full_name`
- [ ] `GET /api/v1/users` — Admin only: list all users (paginated)
- [ ] `PATCH /api/v1/users/{id}/status` — Admin only: enable/disable user account
  - Guard: admin cannot disable themselves → `403`

---

## Phase 5 — Products API

### 5.1 Pydantic Schemas
- [ ] Create `app/schemas/product.py`:
  - `ProductResponse` (id, name, description, price, image_url, category, is_available)
  - `ProductCreateRequest` (name, description, price, image_url, category, is_available)
  - `ProductUpdateRequest` (all fields optional)

### 5.2 Repository
- [ ] Create `app/repositories/product_repo.py`:
  - `get_all(db, page, size, category=None) -> PageResponse[ProductResponse]`
  - `get_by_id(db, product_id) -> Product | None`
  - `create(db, data: ProductCreateRequest) -> Product`
  - `update(db, product, data: ProductUpdateRequest) -> Product`
  - `delete(db, product) -> None`

### 5.3 Router & Endpoints
- [ ] Create `app/api/v1/products.py`
- [ ] `GET /api/v1/products` — Browse products (paginated, `?category=coffee` filter)
- [ ] `GET /api/v1/products/{id}` — Product detail
- [ ] `POST /api/v1/products` — Admin only: create product
- [ ] `PUT /api/v1/products/{id}` — Admin only: update product
- [ ] `DELETE /api/v1/products/{id}` — Admin only: delete product

---

## Phase 6 — Orders API

### 6.1 Pydantic Schemas
- [ ] Create `app/schemas/order.py`:
  - `OrderItemInput` (product_id: UUID, quantity: int ≥ 1)
  - `OrderCreateRequest` (items: list[OrderItemInput], min 1 item)
  - `OrderItemResponse` (product_name, quantity, unit_price, subtotal)
  - `OrderResponse` (id, status, total_amount, items, ordered_at)
  - `OrderStatusRequest` (status: OrderStatus)

### 6.2 Repository
- [ ] Create `app/repositories/order_repo.py`:
  - `create(db, user_id, items: list[OrderItemInput]) -> Order`:
    - Validate all products exist and are `is_available`
    - Snapshot `unit_price` from current `product.price`
    - Calculate `total_amount` = sum(quantity × unit_price) server-side
    - Create `Order` + all `OrderItem` records atomically
  - `get_by_user(db, user_id, page, size) -> PageResponse[OrderResponse]`
  - `get_by_id(db, order_id) -> Order | None` (eager load items + products)
  - `get_all(db, page, size) -> PageResponse[OrderResponse]`
  - `update_status(db, order, status) -> Order`

### 6.3 Router & Endpoints
- [ ] Create `app/api/v1/orders.py`
- [ ] `POST /api/v1/orders` — Place a new order
- [ ] `GET /api/v1/orders/me` — My order history (paginated)
- [ ] `GET /api/v1/orders/{id}` — Order detail (own or admin)
- [ ] `GET /api/v1/orders` — Admin only: all orders (paginated)
- [ ] `PATCH /api/v1/orders/{id}/status` — Admin only: update order status

### 6.4 Router Aggregator
- [ ] Create `app/api/v1/api.py` — include all routers under prefix `/api/v1`
- [ ] Mount into `app/main.py`
- [ ] Verify all endpoints appear correctly on Swagger UI

---

## Phase 7 — Testing & Quality

### 7.1 Test Infrastructure
- [ ] Create `tests/conftest.py`:
  - Override `get_db` with SQLite in-memory async engine
  - Auto-create / drop tables per test session
  - `fake_user` fixture (USER role, is_active=True)
  - `fake_admin` fixture (ADMIN role, is_active=True)
  - `override_get_current_user(user)` helper for dependency injection
- [ ] Create shared fixtures: `test_product`, `test_order`

### 7.2 Auth Tests (`tests/api/test_auth.py`)
- [ ] `POST /auth/sync` — creates new user successfully
- [ ] `POST /auth/sync` — called again → updates user, no duplicate created
- [ ] Missing token → `401`
- [ ] Invalid token → `401`
- [ ] Disabled user → `403`

### 7.3 User Tests (`tests/api/test_users.py`)
- [ ] `GET /users/me` — happy path, returns correct user
- [ ] `PUT /users/me` — updates `full_name` successfully
- [ ] `GET /users` — USER role → `403`
- [ ] `GET /users` — ADMIN → returns paginated list
- [ ] `PATCH /users/{id}/status` — admin disables another user successfully
- [ ] `PATCH /users/{id}/status` — admin disables themselves → `403`
- [ ] `PATCH /users/{id}/status` — user not found → `404`

### 7.4 Product Tests (`tests/api/test_products.py`)
- [ ] `GET /products` — browse all, paginated
- [ ] `GET /products?category=coffee` — filter returns correct results
- [ ] `GET /products/{id}` — detail returned successfully
- [ ] `GET /products/{id}` — does not exist → `404`
- [ ] `POST /products` — ADMIN creates successfully
- [ ] `POST /products` — USER role → `403`
- [ ] `PUT /products/{id}` — ADMIN updates successfully
- [ ] `PUT /products/{id}` — does not exist → `404`
- [ ] `DELETE /products/{id}` — ADMIN deletes successfully
- [ ] `DELETE /products/{id}` — USER role → `403`

### 7.5 Order Tests (`tests/api/test_orders.py`)
- [ ] `POST /orders` — places order successfully, `total_amount` calculated correctly
- [ ] `POST /orders` — `unit_price` is snapshotted (unchanged when product price updates)
- [ ] `POST /orders` — product does not exist → `404`
- [ ] `POST /orders` — product `is_available=False` → `422`
- [ ] `POST /orders` — `quantity < 1` → `422`
- [ ] `GET /orders/me` — returns only current user's orders
- [ ] `GET /orders/{id}` — user views their own order successfully
- [ ] `GET /orders/{id}` — user views another user's order → `403`
- [ ] `GET /orders` — USER role → `403`
- [ ] `GET /orders` — ADMIN sees all orders (paginated)
- [ ] `PATCH /orders/{id}/status` — ADMIN updates status successfully
- [ ] `PATCH /orders/{id}/status` — USER role → `403`

### 7.6 Coverage & Code Quality
- [ ] Run `uv run pytest --cov=app --cov-report=term-missing`
- [ ] Ensure coverage ≥ **85%**
- [ ] Run `ruff check app/` — no linting errors
- [ ] Run `pyright app/` — no type errors

---

## Phase 8 — Documentation & Final Review

### 8.1 Postman Collection
- [ ] Create collection `Cocoloco API`
- [ ] Environment variables: `base_url=http://localhost:8000`, `user_token`, `admin_token`
- [ ] Add requests for all endpoints (auth, users, products, orders)
- [ ] Run all requests successfully with correct response format

### 8.2 OpenAPI / Swagger Review
- [ ] All endpoints have `summary` and `tags`
- [ ] Tags grouped correctly: `auth` · `users` · `products` · `orders`
- [ ] All response schemas display correctly

### 8.3 README
- [ ] Project description: Cocoloco API overview
- [ ] Installation & local development guide
- [ ] Migration + seed data instructions
- [ ] Running tests + viewing coverage report
- [ ] Endpoint reference table

### 8.4 Git & Submit
- [ ] Commit all code with conventional commit messages
- [ ] Push to GitLab (`main` branch)
- [ ] Push to GitHub

---

## 📊 Summary

| Phase | Tasks | Estimate |
|:---|:---:|:---|
| Phase 1 — Setup & Infrastructure | 19 | 2 days |
| Phase 2 — Database Models & Migrations | 18 | 2 days |
| Phase 3 — Authentication & RBAC | 16 | 2 days |
| Phase 4 — Users API | 11 | 1 day |
| Phase 5 — Products API | 11 | 1.5 days |
| Phase 6 — Orders API | 15 | 2 days |
| Phase 7 — Testing & Quality | 28 | 2.5 days |
| Phase 8 — Documentation & Final Review | 10 | 1 day |
| **Total** | **128 tasks** | **~14 days** |
