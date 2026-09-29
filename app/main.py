"""
app/main.py
FastAPI application entrypoint — lifespan, CORS middleware, router mounting.

Startup/shutdown lifecycle:
  - lifespan() logs startup and shutdown events.
  - Verifies database connection on startup and disposes connection pool on shutdown.

CORS:
  - Allows Flutter mobile & web frontends to call the API from any origin
    during development. Tighten in production via ALLOWED_ORIGINS env var.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.database import async_engine
from app.core.exceptions import setup_exception_handlers

# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown hooks
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Runs code before the first request (startup) and after the last one (shutdown).
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    print("🚀 Cocoloco API starting up...")
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection established.")
    except Exception as exc:
        print(f"⚠️  Database connection check failed: {exc}")

    yield  # ← Application runs here (handles requests)

    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("🛑 Cocoloco API shutting down...")
    await async_engine.dispose()
    print("🔌 Database engine connection pool disposed.")


# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Cocoloco API",
    summary="Async REST API for Cocoloco food & coffee ordering platform.",
    description="""
## 🥐 Cocoloco Food & Coffee Ordering API

Built with FastAPI, SQLAlchemy 2.0 (Async), PostgreSQL 16, and Clerk.

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
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

setup_exception_handlers(app)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Returns HTTP 200 when the service is running."""
    return JSONResponse(content={"status": "ok", "service": "cocoloco-api"})


# ---------------------------------------------------------------------------
# API v1 routers
# auth router is live now (Task 3.5).
# Remaining routers (users, products, orders) will be aggregated in Task 6.4.
# ---------------------------------------------------------------------------

from app.api.v1.auth import router as auth_router  # noqa: E402
from app.api.v1.products import router as products_router  # noqa: E402
from app.api.v1.users import router as users_router  # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
