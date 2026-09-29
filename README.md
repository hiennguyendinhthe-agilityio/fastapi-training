# 🥐 Cocoloco Food & Coffee Ordering API

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0%20Async-red.svg)](https://docs.sqlalchemy.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20(asyncpg)-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Clerk Authentication](https://img.shields.io/badge/Auth-Clerk%20RS256%20JWKS-6C47FF.svg?logo=clerk&logoColor=white)](https://clerk.com)
[![Test Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com/pytest-dev/pytest-cov)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

High-performance, fully asynchronous RESTful backend API for the **Cocoloco Food & Coffee Ordering platform** (AgilityIO). Built from the ground up following **Clean Architecture**, **Domain-Driven Design**, and **Zero Blocking I/O** principles, powering the Cocoloco Flutter mobile app and admin dashboard.

---

## 🏗️ Architecture & System Design

The project enforces a strict **Layered Clean Architecture** where dependencies point exclusively inward:

```
                      +------------------------------------------+
                      |         HTTP Clients (Flutter Mobile)    |
                      +------------------------------------------+
                                           |
                                           v
[Presentation Layer]  +------------------------------------------+
                      |  app/api/v1/ (auth, users, products,     |
                      |               orders, aggregator)        |
                      +------------------------------------------+
                                    |              |
                                    v              v
[Contracts & Core]    +-----------------------+  +---------------+
                      | app/schemas/ (DTOs,   |  | app/core/     |
                      |  Pydantic v2, Params) |  | (Security, DB)|
                      +-----------------------+  +---------------+
                                    |
                                    v
[Data Access Layer]   +------------------------------------------+
                      |  app/repositories/ (Async Repositories,  |
                      |  Eager Loading, Domain Exceptions)       |
                      +------------------------------------------+
                                    |
                                    v
[Domain Entities]     +------------------------------------------+
                      |  app/models/ (SQLAlchemy 2.0 Async,      |
                      |  User, Product, Order, OrderItem)        |
                      +------------------------------------------+
                                    |
                                    v
[Database Engine]     +------------------------------------------+
                      |  PostgreSQL 16 via asyncpg connection    |
                      +------------------------------------------+
```

---

## ✨ Key Enterprise Features

- **End-to-End Async Purity**: 100% non-blocking I/O powered by native `async/await` and the C-accelerated `asyncpg` driver.
- **Clerk RS256 JWKS Authentication**: Stateless JWT verification against Clerk's JSON Web Key Set with LRU-cached public keys, 5-second leeway clock skew tolerance, and strict claim validation (`sub`, `exp`, `nbf`).
- **2-Tier RBAC Guard**: Strict role-based authorization differentiating standard customers (`USER`) and store managers (`ADMIN`).
- **Soft-Disable Active Guard**: Deactivated accounts (`is_active=False`) are blocked with HTTP 403 Forbidden even if their Clerk JWT remains cryptographically valid.
- **Admin Self-Lock Guard**: Administrators are prevented from deactivating their own accounts to eliminate accidental lockout scenarios.
- **Price Sovereignty & Snapshot Invariance**: Product prices are never trusted from client payloads. Unit prices are read directly from the database and snapshotted onto order line items at purchase time, preventing history drift when menu prices change.
- **N+1 Query Elimination**: Deep eager loading via `selectinload(Order.items).joinedload(OrderItem.product)` to eliminate query cascades and prevent async `MissingGreenlet` errors.
- **Standardized Pagination Envelope**: Generic `PageResponse[T]` metadata envelope (`page`, `size`, `total`, `pages`) across all collection endpoints.

---

## 🛠️ Tech Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Language** | Python | `3.12+` / `3.13` | Modern strongly-typed backend runtime |
| **Framework** | FastAPI | `0.115+` | High-performance asynchronous API framework |
| **Package Tool** | uv (Astral) | `0.5+` | Lightning-fast virtualenv and dependency manager |
| **Database** | PostgreSQL | `16-alpine` | ACID relational database |
| **Async Driver** | asyncpg | `0.30+` | High-throughput binary protocol async driver |
| **ORM** | SQLAlchemy | `2.0+ (Async)` | Modern async object-relational mapping |
| **Migrations** | Alembic | `1.14+` | Database versioning and schema migrations |
| **Auth** | Clerk | `RS256 JWKS` | Cloud Identity & Access Management |
| **Validation** | Pydantic | `v2.10+` | Rust-backed request/response data contracts |
| **Testing** | Pytest + pytest-asyncio | `9.1+` | SQLite in-memory isolated automated test suite |
| **Coverage** | pytest-cov | `7.1+` | Code coverage reporting (Current: **99%**) |
| **Linter & Formatter** | Ruff | `0.9+` | Ultra-fast Python linter and code formatter |
| **Type Checker** | Pyright | `1.1+` | Strict static typing analysis |

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- [uv](https://docs.astral.sh/uv/) package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.12 or higher

### 2. Clone & Environment Configuration
```bash
git clone https://gitlab.asoft-python.com/hien.nguyendinhthe/fastapi-training.git
cd fastapi-training

# Copy environment template
cp .env.example .env
```

Ensure `.env` contains valid configuration:
```env
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://cocoloco_user:cocoloco_secret@localhost:5432/cocoloco_db
CLERK_JWKS_URL=https://api.clerk.com/v1/jwks
ALLOWED_ORIGINS=["*"]
```

### 3. Install Dependencies
```bash
uv sync
```

### 4. Start PostgreSQL with Docker
```bash
docker compose up -d
```

### 5. Run Database Migrations & Seed Data
```bash
# Apply all schema migrations
uv run alembic upgrade head

# Seed initial catalog items and admin user (Idempotent)
uv run python -m scripts.seed
```

### 6. Start the API Server
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service is now accessible at:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON Contract**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📡 API Endpoint Reference Matrix

| Group | Method | Endpoint | Auth | RBAC Role | Description |
|---|---|---|---|---|---|
| **Health** | `GET` | `/health` | Public | None | Service liveness probe |
| **Auth** | `POST` | `/api/v1/auth/sync` | Bearer JWT | Any | Upsert authenticated Clerk user to DB |
| **Users** | `GET` | `/api/v1/users/me` | Bearer JWT | Any | Retrieve authenticated profile |
| **Users** | `PUT` | `/api/v1/users/me` | Bearer JWT | Any | Update profile name |
| **Users** | `GET` | `/api/v1/users` | Bearer JWT | `ADMIN` | Paginated listing of all users |
| **Users** | `PATCH` | `/api/v1/users/{id}/status` | Bearer JWT | `ADMIN` | Enable / disable user account |
| **Products** | `GET` | `/api/v1/products` | Public | None | Browse catalog with category filter |
| **Products** | `GET` | `/api/v1/products/{id}` | Public | None | Get product details by UUID |
| **Products** | `POST` | `/api/v1/products` | Bearer JWT | `ADMIN` | Add new menu product |
| **Products** | `PUT` | `/api/v1/products/{id}` | Bearer JWT | `ADMIN` | Update product details / price |
| **Products** | `DELETE`| `/api/v1/products/{id}` | Bearer JWT | `ADMIN` | Delete product (restricted if ordered) |
| **Orders** | `POST` | `/api/v1/orders` | Bearer JWT | Any | Place order with snapshot pricing |
| **Orders** | `GET` | `/api/v1/orders/me` | Bearer JWT | Any | Customer paginated order history |
| **Orders** | `GET` | `/api/v1/orders/{id}` | Bearer JWT | Owner/Admin | View order details (BOLA protected) |
| **Orders** | `GET` | `/api/v1/orders` | Bearer JWT | `ADMIN` | Admin paginated view of all orders |
| **Orders** | `PATCH` | `/api/v1/orders/{id}/status` | Bearer JWT | `ADMIN` | Advance status (CONFIRMED/COMPLETED) |

---

## 🧪 Testing & Code Quality Gate

All automated tests execute against an isolated in-memory SQLite database (`sqlite+aiosqlite:///:memory:`) using `StaticPool`, guaranteeing zero state leakage across test cases and zero contamination of production data.

```bash
# Run all tests
uv run pytest

# Run tests with detailed code coverage report
uv run pytest --cov=app --cov-report=term-missing

# Run Ruff linter & formatting check
uv run ruff check .

# Run Pyright static type checker
uv run pyright
```

### Current Quality Metrics:
- **Total Test Cases**: `174 passed`
- **Execution Time**: `~2.5 seconds`
- **Code Coverage**: **`99%`**
- **Lint Errors**: `0`
- **Type Check Errors**: `0`

---

## 📮 Postman Collection

A complete Postman collection is located at [`postman/Cocoloco_API.postman_collection.json`](postman/Cocoloco_API.postman_collection.json).

### How to use:
1. Import `postman/Cocoloco_API.postman_collection.json` into Postman.
2. Set collection variables:
   - `base_url`: `http://localhost:8000`
   - `user_token`: A valid JWT token from Clerk for a regular user.
   - `admin_token`: A valid JWT token from Clerk for an admin user.
3. Execute requests across the `Auth`, `Users`, `Products`, and `Orders` folders.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
