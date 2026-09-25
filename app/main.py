"""
app/main.py
FastAPI application entrypoint — lifespan, CORS middleware, router mounting.

Startup/shutdown lifecycle:
  - lifespan() logs startup and shutdown events.
  - Database engine and connection pool will be initialized here in Task 2.1.

CORS:
  - Allows Flutter mobile & web frontends to call the API from any origin
    during development. Tighten in production via ALLOWED_ORIGINS env var.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Runs code before the first request (startup) and after the last one
    (shutdown). This is the modern FastAPI replacement for @app.on_event().

    Future tasks will add:
      - Task 2.1: async database engine initialization
      - Task 3.2: pre-warming the JWKS client cache
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    print("🚀 Cocoloco API starting up...")

    yield  # ← Application runs here (handles requests)

    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("🛑 Cocoloco API shutting down...")


# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Cocoloco API",
    summary="High-performance async REST API for the Cocoloco food & coffee ordering platform.",
    description="""
## 🥐 Cocoloco Food & Coffee Ordering API

Built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL 16**, and **Clerk Authentication**.

### Features
- 🔐 **Clerk RS256 JWT Authentication** — secure, stateless token verification
- 👥 **2-Tier RBAC** — `ADMIN` and `USER` roles with fine-grained guards
- 🛍️ **Product Catalog** — browse, filter by category, full CRUD for admins
- 📦 **Order Management** — place orders, track history, admin status updates
- 📄 **Pagination** — all list endpoints support `page` / `size` parameters

### Tech Stack
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115+ |
| ORM | SQLAlchemy 2.0 Async |
| Database | PostgreSQL 16 (asyncpg) |
| Auth | Clerk (RS256 JWKS) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
    """,
    version="0.1.0",
    contact={
        "name": "AgilityIO Backend Team",
        "email": "hien.nguyendinhthe@agility.io",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
    # Swagger UI and ReDoc are enabled in development.
    # Set to None in production via ENVIRONMENT check (Task 3.1).
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    # Allow all origins in development — restrict in production.
    # Example production value: ["https://app.cocoloco.io", "https://admin.cocoloco.io"]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, PATCH, DELETE, OPTIONS
    allow_headers=["*"],   # Authorization, Content-Type, etc.
)


# ---------------------------------------------------------------------------
# Health check — used by Docker, load balancers, and CI pipelines
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    response_description="Service is alive",
)
async def health_check() -> JSONResponse:
    """
    Returns HTTP 200 when the service is running.
    Does NOT check database connectivity — that will be added in Task 2.1.
    """
    return JSONResponse(content={"status": "ok", "service": "cocoloco-api"})


# ---------------------------------------------------------------------------
# API v1 routers — mounted in Task 6.4 when all routers are implemented
# ---------------------------------------------------------------------------
# from app.api.v1.api import api_router
# app.include_router(api_router, prefix="/api/v1")
