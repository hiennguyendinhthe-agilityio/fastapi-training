# 📖 Bài học: Install Dependencies

> **Task 1.2** — Ngày học: Sep 25, 2026
> Người hướng dẫn: Antigravity AI (Senior Backend Engineer)

---

## 🎯 Mục tiêu bài học

Sau bài này em sẽ hiểu được:
- **Dependency** là gì và tại sao dự án cần chúng
- Tại sao dùng **`uv`** thay vì `pip` truyền thống
- Phân biệt **production dependencies** và **dev dependencies**
- Cấu trúc file `pyproject.toml` — tiêu chuẩn hiện đại của Python
- Vai trò cụ thể của từng thư viện trong Cocoloco API

---

## 🤔 Phần 1 — Dependency là gì?

### Định nghĩa đơn giản

**Dependency** (phụ thuộc) là những thư viện/package bên ngoài mà dự án của em **cần phải có** để hoạt động.

Hãy hình dung như đầu bếp làm món ăn:
```
Món ăn (Cocoloco API)
├── Cần: FastAPI       → như "nồi inox tốt"
├── Cần: SQLAlchemy    → như "dao bếp chuyên nghiệp"
├── Cần: asyncpg       → như "bếp gas công nghiệp"
└── Cần: PyJWT         → như "két sắt bảo mật"
```

Không có những "dụng cụ" này, em phải tự code từ đầu — mất hàng năm!

---

## 🛠️ Phần 2 — Tại sao dùng `uv` thay vì `pip`?

### Công cụ quản lý package trong Python

| Công cụ | Tốc độ | Lock file | Venv tích hợp | Được dùng |
|---------|--------|-----------|---------------|-----------|
| `pip` | Chậm | ❌ Không | ❌ Không | Cũ, legacy |
| `poetry` | Trung bình | ✅ Có | ✅ Có | Phổ biến |
| `uv` ⭐ | **Nhanh gấp 10-100x** | ✅ Có | ✅ Có | **Chuẩn mới 2024+** |

### Lý do chọn `uv`

`uv` được viết bằng **Rust** (ngôn ngữ cực nhanh), trong khi `pip` viết bằng Python:

```bash
# Cài 100 packages:
pip install ...   → ~60 giây
uv add ...        → ~2 giây  ← 30x nhanh hơn!
```

**Các lệnh `uv` đã dùng trong task 1.2:**

```bash
# Thêm production dependency
uv add fastapi[standard]
uv add sqlalchemy[asyncio]
uv add asyncpg
...

# Thêm dev dependency (chỉ dùng khi phát triển, không ship lên server)
uv add --dev pytest pytest-asyncio pytest-cov
uv add --dev ruff pyright
```

---

## 📄 Phần 3 — File `pyproject.toml` là gì?

### Tiêu chuẩn hiện đại của Python

`pyproject.toml` là file **cấu hình trung tâm** của một dự án Python hiện đại (PEP 517/518/621). Nó thay thế `setup.py`, `requirements.txt`, `setup.cfg` cũ.

```toml
[project]
name = "cocoloco-api"
version = "0.1.0"
description = "FastAPI backend for the Cocoloco food & coffee ordering platform"
requires-python = ">=3.12"

dependencies = [
    # Production — cần để chạy app
    "fastapi[standard]>=0.115.0",
    "sqlalchemy[asyncio]>=2.0.0",
    ...
]

[dependency-groups]
dev = [
    # Dev only — chỉ dùng khi phát triển
    "pytest>=8.3.0",
    "ruff>=0.6.0",
    ...
]
```

### Ký hiệu version constraint

```toml
"fastapi[standard]>=0.115.0"
│        │           │
│        │           └── Phiên bản tối thiểu (minimum version)
│        └────────────── Optional extras (tính năng mở rộng)
└─────────────────────── Tên package
```

| Ký hiệu | Ý nghĩa | Ví dụ |
|---------|---------|-------|
| `>=1.0` | Từ 1.0 trở lên | ✅ 1.0, 1.5, 2.0 |
| `==1.0` | Chính xác 1.0 | ❌ 0.9, 1.1 |
| `~=1.0` | 1.0.x (patch only) | ✅ 1.0.1 ❌ 1.1 |
| `>=1.0,<2.0` | Từ 1.0 đến dưới 2.0 | ✅ 1.9 ❌ 2.0 |

---

## 📦 Phần 4 — Production Dependencies (Giải thích chi tiết)

Đây là các thư viện được khai báo trong `[project] > dependencies` — **bắt buộc** phải có khi chạy app.

---

### 🔷 `fastapi[standard]>=0.115.0`

**FastAPI** là web framework chính của toàn bộ project.

```python
from fastapi import FastAPI

app = FastAPI(title="Cocoloco API")

@app.get("/products")
async def get_products():
    return [{"name": "Cappuccino", "price": 3.00}]
```

**Tại sao `[standard]`?**

Dấu `[standard]` là **optional extras** — cài thêm các package liên quan:
```
fastapi[standard] = fastapi + uvicorn + pydantic + python-multipart + email-validator
                               ↑ Chạy server   ↑ Validate data    ↑ Validate email
```

**Tại sao FastAPI thay vì Django/Flask?**

| | Flask | Django | **FastAPI** |
|-|-------|--------|-------------|
| Async | ❌ | ❌ (partial) | ✅ Native |
| Auto docs (Swagger) | ❌ | ❌ | ✅ Tự động |
| Type hints + validation | ❌ | ❌ | ✅ Pydantic |
| Performance | Thấp | Trung bình | **Cao nhất** |

---

### 🔷 `uvicorn[standard]>=0.30.0`

**Uvicorn** là **ASGI server** — thứ thực sự "chạy" ứng dụng FastAPI và lắng nghe HTTP requests.

```
Browser / Flutter App
       │  HTTP Request
       ▼
┌──────────────┐
│   Uvicorn    │  ← Server, lắng nghe port 8000
│  (ASGI server)│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   FastAPI    │  ← Framework xử lý logic
└──────────────┘
```

**Cách chạy:**
```bash
uv run uvicorn app.main:app --reload
#              │             │
#              │             └── --reload: tự restart khi code thay đổi
#              └── module app/main.py, object tên "app"
```

**ASGI vs WSGI là gì?**
- **WSGI** (Flask, Django cũ) → synchronous, xử lý 1 request tại một thời điểm
- **ASGI** (FastAPI, Starlette) → asynchronous, xử lý nhiều request đồng thời → **nhanh hơn nhiều**

---

### 🔷 `sqlalchemy[asyncio]>=2.0.0`

**SQLAlchemy** là **ORM** (Object-Relational Mapper) — cho phép tương tác với database bằng Python code thay vì SQL thuần.

**Không có SQLAlchemy:**
```python
# Phải tự viết SQL thủ công
cursor.execute("SELECT * FROM products WHERE id = %s AND is_available = TRUE", (product_id,))
row = cursor.fetchone()
product = {"id": row[0], "name": row[1], "price": row[2]}
```

**Có SQLAlchemy:**
```python
# Pythonic, dễ đọc, an toàn
product = await db.get(Product, product_id)
```

**Tại sao `[asyncio]`?**

Cài thêm `greenlet` — package nền giúp SQLAlchemy hoạt động đúng trong môi trường async (bắt buộc với asyncpg).

**SQLAlchemy 2.0 vs 1.x:**

```python
# SQLAlchemy 1.x (cũ) — Legacy style
session.query(User).filter(User.id == user_id).first()

# SQLAlchemy 2.0 (mới) — Modern style ← Chúng ta dùng cái này
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()
```

---

### 🔷 `asyncpg>=0.29.0`

**asyncpg** là **database driver** — lớp thấp nhất kết nối trực tiếp với PostgreSQL.

```
FastAPI (business logic)
    │
SQLAlchemy (ORM, query builder)
    │
asyncpg (driver) ← Giao tiếp trực tiếp với PostgreSQL
    │
PostgreSQL (database)
```

**Tại sao asyncpg chứ không phải psycopg2?**

| | psycopg2 | **asyncpg** |
|-|----------|-------------|
| I/O model | Synchronous (blocking) | **Asynchronous (non-blocking)** |
| Phù hợp với | Flask, Django | **FastAPI, async** |
| Performance | Trung bình | **Nhanh nhất hiện tại** |

Rule trong `.agents/rules/02-async-concurrency.md`:
> "PostgreSQL operations must exclusively use the **asyncpg** driver via `postgresql+asyncpg://`"

---

### 🔷 `alembic>=1.13.0`

**Alembic** là công cụ **database migration** — quản lý lịch sử thay đổi schema database.

**Vấn đề không có Alembic:**
```
Tuần 1: Tạo bảng users với 5 cột
Tuần 2: Thêm cột "phone_number"
→ Làm thế nào để cập nhật database của đồng nghiệp?
→ Server production thì sao?
→ Nếu cần rollback (hoàn tác) thì làm gì?
```

**Với Alembic:**
```bash
# Tạo migration file tự động từ model thay đổi
alembic revision --autogenerate -m "add phone_number to users"

# Áp dụng lên database
alembic upgrade head

# Hoàn tác nếu có lỗi
alembic downgrade -1
```

Alembic tạo ra các file migration trong thư mục `alembic/versions/`:
```
alembic/versions/
├── 001_init_users_products_orders.py   ← Migration đầu tiên
├── 002_add_phone_number_to_users.py    ← Migration tuần 2
└── 003_add_index_on_email.py           ← Migration tuần 3
```

Mỗi file là một "bước" trong lịch sử database — có thể forward hoặc backward.

---

### 🔷 `pydantic-settings>=2.4.0`

**pydantic-settings** giúp đọc file `.env` và validate các biến môi trường bằng Pydantic.

```python
# Task 3.1 sẽ viết file này
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str           # Tự đọc DATABASE_URL từ .env
    clerk_jwks_url: str         # Tự đọc CLERK_JWKS_URL từ .env
    environment: str = "development"  # Có default value

    class Config:
        env_file = ".env"       # Chỉ định file .env cần đọc

settings = Settings()           # Tự động load!
print(settings.database_url)    # → "postgresql+asyncpg://..."
```

**Pydantic-settings làm 3 việc:**
1. **Đọc** giá trị từ `.env`
2. **Validate** đúng kiểu dữ liệu (str, int, bool...)
3. **Báo lỗi** rõ ràng nếu biến bắt buộc bị thiếu

---

### 🔷 `pyjwt[crypto]>=2.9.0`

**PyJWT** dùng để decode và verify **JWT token** do Clerk phát hành.

**JWT (JSON Web Token) là gì?**

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyIsImVtYWlsIjoiaGllbkBleGFtcGxlLmNvbSJ9.SIGNATURE
│                                      │                                                                    │
└── Header (thuật toán: RS256)         └── Payload (data: user_id, email...)                               └── Chữ ký số
```

Base64 decode payload ra:
```json
{
  "sub": "user_clerk_123",
  "email": "hien@example.com",
  "exp": 1727234567
}
```

**`[crypto]` extras** = cài thêm `cryptography` library — cần thiết để verify chữ ký **RS256** (asymmetric cryptography) mà Clerk dùng.

**Tại sao RS256 chứ không phải HS256?**

| | HS256 | RS256 |
|-|-------|-------|
| Key | 1 secret key duy nhất | Private key + Public key |
| Ai verify được? | Ai biết secret | **Ai cũng có thể** (dùng public key) |
| Phù hợp | Internal services | **Third-party auth (Clerk)** |

---

### 🔷 `httpx>=0.27.0`

**httpx** là HTTP client async — dùng để gọi HTTP request **từ FastAPI sang các service khác**.

**Tại sao không dùng `requests`?**

```python
# ❌ requests — synchronous, block event loop!
import requests
response = requests.get("https://clerk.com/jwks")  # BLOCK! Không dùng được!

# ✅ httpx — async, không block!
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get("https://clerk.com/jwks")  # Non-blocking ✅
```

Rule trong `.agents/rules/02-async-concurrency.md`:
> "NEVER use synchronous HTTP libraries like `requests` or `urllib3` → use asynchronous `httpx.AsyncClient`"

**Dùng ở đâu trong Cocoloco API?**
- Task 3.2: Fetch JWKS public key từ Clerk endpoint để verify token

---

## 🧪 Phần 5 — Dev Dependencies (Chỉ dùng khi phát triển)

Khai báo trong `[dependency-groups] > dev` — **KHÔNG** được cài lên production server.

---

### 🔶 `pytest>=8.3.0`

**Pytest** là framework viết và chạy unit test/integration test.

```python
# tests/api/test_products.py
def test_get_products_returns_200(client):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    assert len(response.json()) > 0
```

```bash
# Chạy tất cả tests
uv run pytest
```

---

### 🔶 `pytest-asyncio>=0.24.0`

Pytest mặc định không hỗ trợ async. **pytest-asyncio** thêm khả năng test hàm `async def`:

```python
# ✅ Nhờ pytest-asyncio, test này chạy được
@pytest.mark.asyncio
async def test_create_order(async_client):
    response = await async_client.post("/api/v1/orders", json={...})
    assert response.status_code == 201
```

Config trong `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"   ← Tự động nhận diện async test, không cần decorator
```

---

### 🔶 `pytest-cov>=5.0.0`

**pytest-cov** đo **code coverage** — tỷ lệ % code được test:

```bash
uv run pytest --cov=app --cov-report=term-missing

# Kết quả:
# Name                    Stmts   Miss  Cover
# ----------------------------------------
# app/api/v1/products.py     45      3    93%
# app/repositories/...       38      0   100%
# TOTAL                     234     12    95%  ← ≥ 85% theo rule
```

Rule trong `.agents/rules/04-testing-quality.md`:
> "Maintain code coverage ≥ **85%**"

---

### 🔶 `aiosqlite>=0.20.0`

**aiosqlite** là async driver cho **SQLite** — database nhẹ, không cần cài đặt.

**Tại sao cần khi đã có asyncpg (PostgreSQL)?**

```
Development / CI testing:
  ├── asyncpg + PostgreSQL → Dùng khi chạy app thật
  └── aiosqlite + SQLite   → Dùng khi chạy tests (nhanh, không cần Docker!)
```

```python
# tests/conftest.py — Task 7.1 sẽ viết
@pytest.fixture
async def db():
    # Dùng SQLite in-memory thay vì PostgreSQL
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # Mỗi test có database riêng, sạch sẽ, độc lập
```

---

### 🔶 `ruff>=0.6.0`

**Ruff** là **linter** — công cụ phân tích code tìm lỗi style, bad practices, bugs tiềm ẩn.

```bash
uv run ruff check app/

# Nếu có vấn đề:
# app/api/v1/products.py:15:5: E501 Line too long (92 > 88 characters)
# app/models/user.py:8:1: F401 'os' imported but unused
```

Config trong `pyproject.toml`:
```toml
[tool.ruff]
line-length = 88       ← Giới hạn độ dài dòng
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]  ← Bật các nhóm rule
# E = pycodestyle errors
# F = pyflakes (unused imports, undefined names)
# I = isort (sắp xếp imports)
# UP = pyupgrade (dùng syntax Python mới hơn)
```

---

### 🔶 `pyright>=1.1.0`

**Pyright** là **static type checker** — kiểm tra kiểu dữ liệu mà không cần chạy code.

```python
# Ví dụ lỗi Pyright bắt được:
async def get_user(user_id: str) -> User:
    user = await db.get(User, user_id)
    return user.email  # ❌ Pyright báo lỗi: return type phải là User, không phải str!
```

```bash
uv run pyright app/

# Nếu có lỗi:
# app/repositories/user_repo.py:45: error: Return type "str" is not assignable to "User"
```

Config trong `pyproject.toml`:
```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"  ← basic | standard | strict
```

---

## 🗺️ Phần 6 — Dependency Map: Ai dùng thư viện nào?

```
Cocoloco API Architecture
│
├── 🌐 HTTP Layer
│   ├── uvicorn          → Chạy ASGI server, nhận HTTP requests
│   └── fastapi          → Route, middleware, dependency injection
│
├── 🗄️ Database Layer
│   ├── sqlalchemy       → ORM, query builder
│   ├── asyncpg          → Driver kết nối PostgreSQL (async)
│   └── alembic          → Migration, quản lý schema history
│
├── ⚙️ Configuration Layer
│   └── pydantic-settings → Load .env, validate config
│
├── 🔐 Security Layer
│   ├── pyjwt[crypto]    → Decode & verify Clerk JWT (RS256)
│   └── httpx            → Fetch JWKS public key từ Clerk
│
└── 🧪 Testing & Quality (dev only)
    ├── pytest           → Test runner
    ├── pytest-asyncio   → Support async tests
    ├── pytest-cov       → Code coverage measurement
    ├── aiosqlite        → SQLite driver cho test in-memory
    ├── ruff             → Linter (code style)
    └── pyright          → Type checker (static analysis)
```

---

## 📝 Phần 7 — Production vs Dev — Phân biệt khi deploy

```toml
[project]
dependencies = [...]        # ← Được cài lên server production

[dependency-groups]
dev = [...]                 # ← CHỈ cài trên máy dev, KHÔNG lên production
```

**Khi deploy lên server production:**
```bash
# Chỉ cài production deps, bỏ qua dev deps
uv sync --no-dev

# Khi dev trên máy local, cài tất cả
uv sync  # hoặc uv sync --dev
```

**Tại sao phân tách?**
- Server production không cần pytest, ruff, pyright
- Giảm dung lượng image Docker
- Giảm attack surface (ít package hơn = ít lỗ hổng bảo mật hơn)

---

## ✅ Tóm tắt — Những gì cần nhớ

> 💡 **`uv`** thay thế `pip` — nhanh gấp 10-100x, có lock file, quản lý venv
>
> 💡 **`pyproject.toml`** = file cấu hình trung tâm — thay thế `requirements.txt` cũ
>
> 💡 **Production deps** = những gì app cần để chạy (fastapi, sqlalchemy, asyncpg...)
>
> 💡 **Dev deps** = công cụ phát triển (pytest, ruff, pyright...) — không lên production
>
> 💡 **Luôn dùng `asyncpg`** cho PostgreSQL — đây là quy tắc bất di bất dịch trong project này

---

## 🔗 Mối liên hệ với các task khác

| Thư viện | Được dùng thật sự ở task |
|----------|--------------------------|
| `pydantic-settings` | Task 3.1 — `app/core/config.py` |
| `sqlalchemy` + `asyncpg` | Task 2.1 — `app/core/database.py` |
| `alembic` | Task 2.5 — Database migrations |
| `pyjwt` + `httpx` | Task 3.2 — `app/core/security.py` |
| `pytest` + `pytest-asyncio` | Task 7.1 — `tests/conftest.py` |
| `ruff` + `pyright` | Task 7.6 — Code quality gate |

---

*📌 Bài tiếp theo: **Task 1.3 — Environment Configuration** → Tạo `.env` và `.env.example` để các thư viện trên (đặc biệt `pydantic-settings`) có dữ liệu để đọc!*
