# 📖 Bài học: App Entrypoint — FastAPI Application Setup

> **Task 1.6** — Ngày học: Sep 25, 2026
> Người hướng dẫn: Antigravity AI (Senior Backend Engineer)

---

## 🎯 Mục tiêu bài học

Sau bài này em sẽ hiểu được:
- `app/main.py` đóng vai trò gì trong toàn bộ FastAPI app
- **Lifespan** là gì và tại sao thay thế `@app.on_event()` cũ
- **CORS Middleware** hoạt động như thế nào và tại sao Flutter cần nó
- Cách viết **Health Check endpoint** chuẩn production
- Cách tổ chức **OpenAPI metadata** (Swagger UI)
- Cách chạy server bằng `uvicorn`

---

## 🤔 Phần 1 — `app/main.py` là trung tâm của mọi thứ

### Hãy hình dung như nhà hàng:

```
app/main.py = Quản lý nhà hàng (Manager)

├── Quyết định giờ mở cửa / đóng cửa (lifespan)
├── Quy định khách từ đâu được phép vào (CORS)
├── Điều phối khách đến quầy nào (router mounting)
└── Đặt biển hiệu, menu (OpenAPI metadata)
```

Khi uvicorn khởi động, nó tìm đến object `app` trong `app/main.py` và:
1. Chạy phần **startup** trong `lifespan`
2. Bắt đầu lắng nghe HTTP requests
3. Route từng request đến handler đúng
4. Khi shutdown, chạy phần **cleanup** trong `lifespan`

---

## ⚡ Phần 2 — Lifespan Context Manager

### Cách cũ (deprecated) — `@app.on_event()`

```python
# ❌ DEPRECATED — không dùng nữa từ FastAPI 0.93+
@app.on_event("startup")
async def startup():
    print("🚀 Starting...")
    # connect to DB...

@app.on_event("shutdown")
async def shutdown():
    print("🛑 Shutting down...")
    # disconnect DB...
```

**Vấn đề**: 2 function riêng rẽ, không share state, khó test.

### Cách mới — `@asynccontextmanager` (Modern FastAPI)

```python
# ✅ CÁCH MỚI — dùng từ FastAPI 0.93+ trở đi
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup (chạy trước khi app nhận request đầu tiên) ──
    print("🚀 Cocoloco API starting up...")
    # Tương lai (Task 2.1): khởi tạo database connection pool
    # Tương lai (Task 3.2): pre-warm JWKS cache

    yield  # ← App chạy ở đây, xử lý requests

    # ── Shutdown (chạy sau khi app từ chối request cuối cùng) ──
    print("🛑 Cocoloco API shutting down...")
    # Tương lai (Task 2.1): đóng database engine gracefully

# Gán lifespan vào app
app = FastAPI(lifespan=lifespan)
```

**Tại sao `yield`?**

`yield` biến function thành **generator**. Code trước `yield` = startup, code sau `yield` = shutdown. Context manager đảm bảo shutdown LUÔN chạy, kể cả khi có exception.

**Ví dụ minh họa:**

```
Timeline:
  t=0s  → uvicorn start → lifespan() được gọi
  t=0s  → STARTUP code chạy (print "🚀...")
  t=0s  → yield → app "mở cửa" nhận requests
  ...
  t=Ns  → uvicorn nhận SIGTERM (Ctrl+C hoặc server restart)
  t=Ns  → app "đóng cửa", từ chối requests mới
  t=Ns  → code SAU yield chạy (print "🛑...")
  t=Ns  → process kết thúc
```

---

## 🌐 Phần 3 — CORS Middleware

### CORS là gì?

**CORS = Cross-Origin Resource Sharing** — cơ chế bảo mật của trình duyệt web.

Khi Flutter Web hoặc web app gọi API từ domain khác:

```
Flutter Web chạy ở: https://app.cocoloco.io   (origin A)
FastAPI chạy ở:     https://api.cocoloco.io   (origin B)

→ Đây là CROSS-ORIGIN request → Browser chặn mặc định!
```

**Flow của CORS:**

```
Browser                                 FastAPI
   │                                       │
   │──── OPTIONS /api/v1/products ────────►│  ← "Preflight" request
   │     Origin: https://app.cocoloco.io   │
   │                                       │
   │◄─── 200 OK ───────────────────────────│
   │     Access-Control-Allow-Origin: *    │  ← FastAPI trả lời: "OK, cho phép"
   │     Access-Control-Allow-Methods: *   │
   │                                       │
   │──── GET /api/v1/products ────────────►│  ← Request thật
   │                                       │
   │◄─── 200 OK + data ────────────────────│
```

**Code CORS trong Cocoloco API:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Development: cho phép mọi origin
    allow_credentials=True,     # Cho phép gửi cookies/auth headers
    allow_methods=["*"],        # GET, POST, PUT, PATCH, DELETE, OPTIONS
    allow_headers=["*"],        # Authorization, Content-Type, ...
)
```

**`allow_origins=["*"]` có nghĩa là gì?**

`*` = wildcard = cho phép mọi domain gọi API. Phù hợp cho **development**.

**Production sẽ restrict lại:**

```python
# Production — chỉ cho phép domain cụ thể
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.cocoloco.io",      # Flutter Web production
        "https://admin.cocoloco.io",    # Admin panel
    ],
    ...
)
```

**Flutter mobile (Android/iOS) có cần CORS không?**

KHÔNG — CORS chỉ là giới hạn của **trình duyệt web**. Flutter mobile app gọi API trực tiếp không qua browser → không bị CORS block. Tuy nhiên, vẫn cần cấu hình CORS để hỗ trợ web version của Flutter app.

---

## 📋 Phần 4 — OpenAPI Metadata (Swagger UI)

FastAPI tự động tạo Swagger UI từ metadata của `FastAPI()`:

```python
app = FastAPI(
    title="Cocoloco API",          # Tên hiển thị trên Swagger
    summary="High-performance...", # Mô tả ngắn (1 dòng)
    description="""...""",         # Mô tả dài, hỗ trợ Markdown
    version="0.1.0",               # Phiên bản API
    contact={...},                 # Thông tin liên hệ
    license_info={...},            # License
    docs_url="/docs",              # URL Swagger UI
    redoc_url="/redoc",            # URL ReDoc (alternative docs)
    openapi_url="/openapi.json",   # URL OpenAPI schema JSON
)
```

**3 URLs quan trọng:**

| URL | Mô tả |
|-----|-------|
| `/docs` | Swagger UI — interactive, test API trực tiếp |
| `/redoc` | ReDoc — đẹp hơn, dễ đọc hơn nhưng không interactive |
| `/openapi.json` | Raw JSON schema — dùng để generate client code |

**Tại sao `docs_url=None` trong production?**

```python
# Production — tắt docs để tránh lộ thông tin API
if settings.ENVIRONMENT == "production":
    app = FastAPI(docs_url=None, redoc_url=None)
```

Attacker có thể dùng Swagger UI để khám phá API và tìm lỗ hổng.

---

## 🏥 Phần 5 — Health Check Endpoint

```python
@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
)
async def health_check() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "service": "cocoloco-api"})
```

**Tại sao cần health check?**

```
Docker / Kubernetes:
  → Định kỳ gọi /health
  → Nếu 200 OK → container "healthy" → giữ lại
  → Nếu không phản hồi → container "unhealthy" → restart!

Load Balancer (nginx/ALB):
  → Gọi /health trước khi route traffic
  → Server chưa ready → không route request đến

CI/CD Pipeline:
  → Sau khi deploy: curl /health
  → 200 OK → deploy thành công!
  → Không phản hồi → rollback!
```

**Kết quả:**

```json
{
  "status": "ok",
  "service": "cocoloco-api"
}
```

---

## 🚀 Phần 6 — Chạy Server với Uvicorn

### Lệnh cơ bản:

```bash
# Development — với hot reload
uv run uvicorn app.main:app --reload
#              │    │    │     │
#              │    │    │     └── Tự restart khi code thay đổi
#              │    │    └──────── Object "app" trong module
#              │    └───────────── Module app/main.py
#              └────────────────── Package "app"

# Chỉ định port (mặc định 8000)
uv run uvicorn app.main:app --reload --port 8080

# Cho phép kết nối từ máy khác trong mạng LAN
uv run uvicorn app.main:app --reload --host 0.0.0.0
```

### Output khi chạy thành công:

```
INFO:     Will watch for changes in these directories: ['/Volumes/MacData/fastapi-training']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [28130] using WatchFiles
INFO:     Started server process [28132]
INFO:     Waiting for application startup.
🚀 Cocoloco API starting up...         ← Lifespan startup chạy!
INFO:     Application startup complete.
```

### Kết quả verify:

```bash
# Health check
curl http://localhost:8000/health
→ {"status": "ok", "service": "cocoloco-api"}

# Swagger UI
curl -o /dev/null -w "%{http_code}" http://localhost:8000/docs
→ 200

# OpenAPI schema
curl http://localhost:8000/openapi.json
→ {"openapi": "3.1.0", "info": {"title": "Cocoloco API", "version": "0.1.0"}, ...}
```

---

## 📐 Phần 7 — Kiến trúc của `app/main.py`

```
app/main.py
│
├── asynccontextmanager lifespan()      ← Startup/shutdown hooks
│   ├── STARTUP: connect DB, warm cache (future tasks)
│   └── SHUTDOWN: graceful cleanup
│
├── FastAPI(lifespan=lifespan)          ← Tạo app instance
│   ├── title, description, version     ← Swagger metadata
│   └── docs_url, redoc_url             ← Documentation URLs
│
├── app.add_middleware(CORSMiddleware)  ← CORS cho Flutter/Web
│   ├── allow_origins=["*"]            ← Dev: mọi domain
│   └── allow_methods/headers=["*"]
│
├── @app.get("/health")                 ← Health check
│
└── app.include_router(...)             ← Mount API routers (Task 6.4)
    # Hiện tại đang được comment out
    # Sẽ bỏ comment sau khi implement xong tất cả routers
```

---

## 🗺️ Phần 8 — Task 1.6 trong bức tranh toàn cục

```
Phase 1 hoàn thành! ✅
│
├── 1.1 Init Project         ✅  → uv, git, pyproject.toml
├── 1.2 Install Dependencies ✅  → fastapi, sqlalchemy, asyncpg...
├── 1.3 Environment Config   ✅  → .env, .env.example
├── 1.4 Docker PostgreSQL    ✅  → Container cocoloco_db:5433
├── 1.5 Project Structure    ✅  → 5 Clean Architecture layers
└── 1.6 App Entrypoint       ✅  → main.py, lifespan, CORS, /health

Phase 2 bắt đầu! 🔜
│
└── 2.1 Core Database Setup  → database.py sẽ kết nối với Docker PostgreSQL
                               và get_db dependency sẽ được inject vào routes
```

**`app/main.py` sẽ được mở rộng theo từng phase:**

```python
# Sau Task 2.1 — lifespan sẽ có thêm:
async with lifespan(app):
    await engine.begin()  # Khởi tạo connection pool
    yield
    await engine.dispose()  # Graceful shutdown pool

# Sau Task 3.3 — main.py sẽ có thêm:
app.add_exception_handler(HTTPException, http_exception_handler)

# Sau Task 6.4 — bỏ comment:
app.include_router(api_router, prefix="/api/v1")
```

---

## ✅ Tóm tắt — Golden Rules

> 💡 **Rule #1**: Dùng `@asynccontextmanager lifespan()` — KHÔNG dùng `@app.on_event()` (deprecated)
>
> 💡 **Rule #2**: CORS `allow_origins=["*"]` chỉ dùng trong development — production PHẢI restrict lại theo domain cụ thể
>
> 💡 **Rule #3**: Luôn có `/health` endpoint — Docker, Kubernetes, và load balancer đều cần nó
>
> 💡 **Rule #4**: Tắt `/docs` và `/redoc` trong production (`docs_url=None`) để tránh lộ API schema
>
> 💡 **Rule #5**: `uv run uvicorn app.main:app --reload` cho dev — `--reload` giúp server tự restart khi sửa code

---

*📌 Bài tiếp theo: **Task 2.1 — Core Database Setup** → Kết nối FastAPI với PostgreSQL qua async SQLAlchemy engine và tạo `get_db` dependency!*
