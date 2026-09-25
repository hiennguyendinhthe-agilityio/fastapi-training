# Clean Architecture & Domain Rules

These rules enforce strict architectural boundaries, repository patterns, and domain-driven design for the **FastAPI Practice (Blogging Platform API)** backend.

## 1. Clean Architecture (Layered Architecture)
The codebase strictly adheres to Clean Architecture with well-defined layers:
1. **Core Layer (`app/core/`)**: Foundation configurations (`pydantic-settings`), asynchronous database engine & session factory (`app/core/database.py`), Clerk JWKS security token decoders (`app/core/security.py`), and centralized exception handlers (`app/core/exceptions.py`).
2. **Domain Layer (`app/models/`)**: Enterprise persistence entities defined using SQLAlchemy 2.0 declarative mappings (`User`, `Profile`, `Post`, `Category`, `PostCategoryLink`). Must remain pure and never import from routers or presentation layers.
3. **Repositories & Services Layer (`app/repositories/`, `app/services/`)**: Encapsulates all data access logic, query optimizations, filtering, pagination, and external cloud integrations (Clerk).
4. **Schemas Layer (`app/schemas/`)**: Pydantic v2 DTOs enforcing request validation, response serialization, and standardized API envelopes.
5. **API Layer (`app/api/`)**: Thin HTTP controllers handling dependency injection, routing (`app/api/v1/`), status codes, and presentation logic (`app/api/deps.py`).

## 2. The Inward Dependency Rule
* **Dependencies MUST ONLY point inward**: Outer layers know about inner layers, but inner layers MUST NEVER know about or import from outer layers.
* **No Circular Imports**: Domain models must never import from schemas, services, or routers. Repositories must never import from API routers.

## 3. Strict Separation of Models vs Schemas
* **Never Expose Models Directly**: SQLAlchemy ORM models (`app/models/`) must never be returned directly in API endpoints.
* **DTO Envelopes**: All responses must be validated and serialized through Pydantic schemas (`app/schemas/`) using `model_config = ConfigDict(from_attributes=True)` to prevent sensitive data leakage (mass-assignment vulnerability).
* **Standardized Pagination Envelope**: All collection endpoints must wrap items in a consistent pagination envelope (`page`, `size`, `total`, `items` or `skip`, `limit`, `total`, `items`).

## 4. Repository Pattern Enforcement
* **No Raw Queries in Routers**: API routers must never execute direct SQL queries, raw session operations, or complex filters.
* **Repository Delegation**: All CRUD and query logic must be delegated to dedicated repositories (`UserRepository`, `ProfileRepository`, `PostRepository`, `CategoryRepository`).

## 5. Database Schema & Migration Governance
* **Alembic Version Control**: Never use `Base.metadata.create_all()` in production environments. Every database schema change must be accompanied by an asynchronous revision script in `alembic/versions/`.
* **Idempotent Seeders**: Database seeders (e.g. predefined categories seed) must be strictly idempotent — executing them multiple times must never create duplicate records or crash.
