# 📖 Bài học: Project Structure — Clean Architecture

> **Task 1.5** — Ngày học: Sep 25, 2026
> Người hướng dẫn: Antigravity AI (Senior Backend Engineer)

---

## 🎯 Mục tiêu bài học

Sau bài này em sẽ hiểu được:
- **Clean Architecture** là gì và tại sao cần áp dụng
- Cách tổ chức thư mục theo 5 layers trong dự án FastAPI thực tế
- **Inward Dependency Rule** — quy tắc phụ thuộc một chiều
- Tại sao cần tách `models/`, `schemas/`, `repositories/`, `api/`
- Vai trò của file `__init__.py` trong Python package
- Tại sao dùng **stub files** thay vì để thư mục trống

---

## 🤔 Phần 1 — Vấn đề: Code không có cấu trúc

### Cách viết code "spaghetti" của người mới

```python
# ❌ CÁCH SAI — tất cả nhồi vào 1 file main.py
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String
import jwt

app = FastAPI()
engine = create_engine("postgresql://...")

class User(Base):           # ← Model DB lẫn lộn với route
    id = Column(Integer)
    email = Column(String)

@app.get("/users")
def get_users(db=Depends(...)):
    # ← Viết SQL query thẳng trong route
    users = db.execute("SELECT * FROM users").fetchall()
    # ← Trả thẳng model DB ra ngoài (lộ data nhạy cảm!)
    return users

@app.post("/users")
def create_user(data: dict):
    token = jwt.decode(...)  # ← Logic JWT lẫn với route handler
    db.execute("INSERT INTO users ...")
```

**Hậu quả của code không có cấu trúc:**

| Vấn đề | Hậu quả |
|--------|---------|
| Mọi thứ trong 1 file | File dài 5000 dòng, không thể đọc |
| Logic lẫn lộn | Bug ở đâu? Không biết tìm chỗ nào |
| Không test được | Route gọi DB trực tiếp → không mock được |
| Không mở rộng được | Thêm feature mới → sợ break feature cũ |

---

## 🏛️ Phần 2 — Clean Architecture là gì?

**Clean Architecture** (Robert C. Martin) là mô hình tổ chức code theo các **vòng tròn đồng tâm**, từ trong ra ngoài:

```
┌─────────────────────────────────────────────┐
│                  API Layer                   │ ← Lớp ngoài cùng
│         (HTTP routes, request/response)      │
│  ┌───────────────────────────────────────┐   │
│  │          Repositories Layer           │   │
│  │      (data access, SQL queries)       │   │
│  │  ┌─────────────────────────────────┐  │   │
│  │  │        Schemas Layer            │  │   │
│  │  │   (Pydantic DTOs, validation)   │  │   │
│  │  │  ┌───────────────────────────┐  │  │   │
│  │  │  │      Models Layer         │  │  │   │
│  │  │  │  (SQLAlchemy entities)    │  │  │   │
│  │  │  │  ┌─────────────────────┐  │  │  │   │
│  │  │  │  │    Core Layer       │  │  │  │   │
│  │  │  │  │ (config, db, auth)  │  │  │  │   │
│  │  │  │  └─────────────────────┘  │  │  │   │
│  │  │  └───────────────────────────┘  │  │   │
│  │  └─────────────────────────────────┘  │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**Quy tắc vàng**: Mũi tên phụ thuộc chỉ được đi **từ ngoài vào trong**.

```
API → Repositories → Schemas → Models → Core
✅ API được phép biết về Repositories
✅ Repositories được phép biết về Models
❌ Models KHÔNG ĐƯỢC biết về API
❌ Core KHÔNG ĐƯỢC biết về bất cứ thứ gì bên ngoài
```

---

## 📂 Phần 3 — 5 Layers trong Cocoloco API

### Layer 1: Core (`app/core/`)

**Là gì**: Nền tảng của toàn bộ hệ thống. Không phụ thuộc vào bất kỳ layer nào khác.

```
app/core/
├── config.py       ← Đọc .env, validate env vars (pydantic-settings)
├── database.py     ← Tạo async engine, AsyncSession, get_db dependency
├── security.py     ← Verify Clerk JWT token (RS256 JWKS)
└── exceptions.py   ← Global error handlers (401, 403, 404, 422)
```

**Nguyên tắc**: Core là thứ duy nhất không import từ các layer khác trong app:
```python
# ✅ Core chỉ dùng thư viện bên ngoài
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine
import jwt

# ❌ Core KHÔNG ĐƯỢC import từ app/models, app/api, app/repositories
from app.models.user import User  # → VI PHẠM!
```

---

### Layer 2: Models (`app/models/`)

**Là gì**: Các SQLAlchemy ORM class — ánh xạ trực tiếp với bảng trong PostgreSQL.

```
app/models/
├── base.py      ← TimestampedBase (created_at, updated_at tự động)
├── user.py      ← class User + enum UserRole(ADMIN, USER)
├── product.py   ← class Product + enum CategoryType
└── order.py     ← class Order + class OrderItem + enum OrderStatus
```

**Quan trọng**: Model là "bản đồ" của database, KHÔNG phải thứ trả về cho client:
```python
# ❌ KHÔNG BAO GIỜ return model trực tiếp
@app.get("/users/{id}")
async def get_user(id: str, db: AsyncSession):
    user = await db.get(User, id)
    return user  # ← LỘ hết mọi field, kể cả data nhạy cảm!

# ✅ LUÔN convert qua Schema trước khi trả về
@app.get("/users/{id}", response_model=UserResponse)
async def get_user(id: str, db: AsyncSession):
    user = await db.get(User, id)
    return UserResponse.model_validate(user)  # ← Chỉ expose field được chọn
```

---

### Layer 3: Schemas (`app/schemas/`)

**Là gì**: Pydantic v2 classes — định nghĩa hình dạng của request/response data.

```
app/schemas/
├── pagination.py   ← PageResponse[T] — generic envelope cho tất cả list endpoints
├── user.py         ← UserResponse, UserUpdateRequest, UserStatusRequest
├── product.py      ← ProductResponse, ProductCreateRequest, ProductUpdateRequest
└── order.py        ← OrderCreateRequest, OrderResponse, OrderItemInput
```

**Tại sao cần Schema riêng biệt với Model?**

```
Model (SQLAlchemy)          Schema (Pydantic)
┌────────────────┐          ┌──────────────────────┐
│ User           │          │ UserResponse         │
│ ├── id         │    →     │ ├── id               │
│ ├── clerk_id   │  convert │ ├── email            │
│ ├── email      │          │ ├── full_name         │
│ ├── full_name  │          │ ├── role             │
│ ├── role       │          │ └── created_at        │
│ ├── is_active  │          │                      │
│ └── hashed_pw  │ ← KHÔNG  │ (hashed_pw bị ẩn!)  │
└────────────────┘   expose └──────────────────────┘
```

Schema kiểm soát **chính xác** field nào được client thấy.

---

### Layer 4: Repositories (`app/repositories/`)

**Là gì**: Lớp trung gian duy nhất được phép nói chuyện với database.

```
app/repositories/
├── user_repo.py      ← get_by_id, get_by_clerk_id, upsert, update, set_status, get_all
├── product_repo.py   ← get_all (có filter + pagination), get_by_id, create, update, delete
└── order_repo.py     ← create (atomic), get_by_user, get_by_id, get_all, update_status
```

**Nguyên tắc Repository Pattern**:
```python
# ❌ KHÔNG ĐƯỢC — Route handler tự viết query
@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.is_active == True).offset(0).limit(10)
    )  # ← Logic query nằm trong route → không test được độc lập!
    return result.scalars().all()

# ✅ ĐÚNG — Route delegate cho Repository
@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    return await user_repo.get_all(db, page=1, size=10)
    # ← Route không biết query chạy như thế nào!
```

**Lợi ích**: Test repository độc lập mà không cần HTTP request.

---

### Layer 5: API (`app/api/`)

**Là gì**: Lớp ngoài cùng — xử lý HTTP, injection dependency, status codes.

```
app/api/
├── deps.py          ← get_current_user(), require_admin() — shared dependencies
└── v1/
    ├── api.py       ← Aggregator: include tất cả routers vào /api/v1
    ├── auth.py      ← POST /auth/sync
    ├── users.py     ← /users/me, /users, /users/{id}/status
    ├── products.py  ← /products, /products/{id}
    └── orders.py    ← /orders, /orders/me, /orders/{id}
```

**Tại sao versioning (`v1/`)?**

```
/api/v1/users  ← Version hiện tại
/api/v2/users  ← Tương lai, breaking changes, không ảnh hưởng client cũ
```

Versioning cho phép rollout dần dần mà không break client cũ (Flutter app đang dùng v1).

---

## 📦 Phần 4 — `__init__.py` là gì?

### Python Package vs Directory

```
Thư mục thông thường:     Python Package:
app/                      app/
├── core/                 ├── core/
│   └── config.py         │   ├── __init__.py   ← CÁI NÀY!
│                         │   └── config.py
```

File `__init__.py` (dù rỗng) nói với Python: **"Đây là một package, cho phép import từ đây"**

```python
# Nếu KHÔNG có __init__.py:
from app.core.config import Settings  # ❌ ModuleNotFoundError!

# Nếu CÓ __init__.py:
from app.core.config import Settings  # ✅ Hoạt động!
```

### Nội dung `__init__.py`

Trong project này, các `__init__.py` có **docstring mô tả layer**:

```python
# app/core/__init__.py
"""Core layer: configuration, database engine, security, exceptions."""
```

Lý do: Khi team mở file trong IDE, nhìn vào docstring biết ngay layer này chứa gì, không cần đọc code.

---

## 🗂️ Phần 5 — Stub Files là gì và tại sao dùng?

### Vấn đề nếu chỉ tạo thư mục trống

```
app/
├── core/
│   └── __init__.py    ← Trống rỗng, không biết sẽ có file gì
├── models/
│   └── __init__.py    ← Tương tự
└── ...
```

Developer mới clone về: *"Mình cần tạo file nào? Đặt tên gì? Ở đâu?"*

### Giải pháp — Stub Files

**Stub file** = file Python hợp lệ, chứa docstring mô tả **sẽ implement gì** và **ở task nào**:

```python
# app/core/config.py (stub)
"""
app/core/config.py
Pydantic Settings — loads .env and validates all environment variables.
Implemented in: Task 3.1
"""
```

**Lợi ích của stub files:**

| | Thư mục trống | Stub files |
|-|---------------|------------|
| Developer biết cần tạo file gì? | ❌ Không | ✅ Có |
| Import không bị lỗi ngay? | ❌ Lỗi nếu import file chưa tồn tại | ✅ File tồn tại, import OK |
| Roadmap rõ ràng? | ❌ Không | ✅ Mỗi stub có "Implemented in: Task X.Y" |
| IDE autocomplete? | ❌ Không | ✅ Có (file đã tồn tại) |

---

## 🔍 Phần 6 — Inward Dependency Rule (Chi tiết)

Đây là quy tắc quan trọng nhất trong Clean Architecture:

```
✅ Chiều PHỤ THUỘC hợp lệ:

app/api/v1/users.py   →   app/repositories/user_repo.py   →   app/models/user.py
     │                              │                                 │
  (outer)                        (middle)                          (inner)
  Biết về                        Biết về                          Không biết
  Repo                           Model                             về ai cả
```

```
❌ VI PHẠM — Dependency đi ngược ra ngoài:

app/models/user.py   imports   app/api/v1/users.py
     │                                 │
  (inner)                           (outer)
  KHÔNG ĐƯỢC biết về outer layers!
```

**Kiểm tra vi phạm trong code:**

```bash
# Nếu thấy dòng này trong models/ → VI PHẠM!
grep -r "from app.api" app/models/
grep -r "from app.repositories" app/core/

# Những import này là hợp lệ:
# app/api/ → import từ app/repositories/ ✅
# app/repositories/ → import từ app/models/ ✅
# app/models/ → import từ app/core/ ✅ (chỉ Base)
# app/core/ → KHÔNG import từ app/ ✅
```

---

## 🗺️ Phần 7 — Cấu trúc hoàn chỉnh sau Task 1.5

```
fastapi-training/
├── .env                          ← 🔒 Secrets (gitignored)
├── .env.example                  ← 📋 Template
├── .gitignore
├── docker-compose.yml            ← 🐳 PostgreSQL 16
├── pyproject.toml                ← 📦 Dependencies + tool configs
│
├── app/                          ← 🏗️ Application package
│   ├── __init__.py
│   ├── main.py                   ← Entrypoint (Task 1.6)
│   │
│   ├── core/                     ─── Layer 1: Foundation
│   │   ├── __init__.py
│   │   ├── config.py             ← Task 3.1
│   │   ├── database.py           ← Task 2.1
│   │   ├── security.py           ← Task 3.2
│   │   └── exceptions.py         ← Task 3.3
│   │
│   ├── models/                   ─── Layer 2: Domain Entities
│   │   ├── __init__.py
│   │   ├── base.py               ← Task 2.1
│   │   ├── user.py               ← Task 2.2
│   │   ├── product.py            ← Task 2.3
│   │   └── order.py              ← Task 2.4
│   │
│   ├── schemas/                  ─── Layer 3: Pydantic DTOs
│   │   ├── __init__.py
│   │   ├── pagination.py         ← Task 4.1
│   │   ├── user.py               ← Task 4.1
│   │   ├── product.py            ← Task 5.1
│   │   └── order.py              ← Task 6.1
│   │
│   ├── repositories/             ─── Layer 4: Data Access
│   │   ├── __init__.py
│   │   ├── user_repo.py          ← Task 4.2
│   │   ├── product_repo.py       ← Task 5.2
│   │   └── order_repo.py         ← Task 6.2
│   │
│   └── api/                      ─── Layer 5: HTTP Controllers
│       ├── __init__.py
│       ├── deps.py               ← Task 3.4
│       └── v1/
│           ├── __init__.py
│           ├── api.py            ← Task 6.4
│           ├── auth.py           ← Task 3.5
│           ├── users.py          ← Task 4.3
│           ├── products.py       ← Task 5.3
│           └── orders.py         ← Task 6.3
│
├── tests/                        ← 🧪 Test suite
│   ├── __init__.py
│   ├── conftest.py               ← Task 7.1
│   ├── api/                      ← Integration tests
│   │   └── __init__.py
│   └── repositories/             ← Unit tests
│       └── __init__.py
│
└── alembic/versions/             ← 📋 DB migration history
```

---

## ✅ Tóm tắt — Golden Rules

> 💡 **Rule #1**: Dependency chỉ đi từ ngoài vào trong — outer biết inner, inner KHÔNG biết outer
>
> 💡 **Rule #2**: Model (SQLAlchemy) KHÔNG BAO GIỜ được return trực tiếp từ API — luôn convert qua Schema
>
> 💡 **Rule #3**: Route handler KHÔNG ĐƯỢC viết SQL query trực tiếp — phải delegate cho Repository
>
> 💡 **Rule #4**: `__init__.py` biến thư mục thành Python package — thiếu nó thì `import` sẽ lỗi
>
> 💡 **Rule #5**: Stub files = roadmap rõ ràng — developer biết file nào cần implement, ở task nào

---

*📌 Bài tiếp theo: **Task 1.6 — App Entrypoint** → Viết `app/main.py` thật sự, khởi động FastAPI server và truy cập Swagger UI!*
