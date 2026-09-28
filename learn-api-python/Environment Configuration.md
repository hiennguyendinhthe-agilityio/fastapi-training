# 📖 Bài học: Environment Configuration

> **Task 1.3** — Ngày học: Sep 25, 2026
> Người hướng dẫn: Antigravity AI (Senior Backend Engineer)

---

## 🎯 Mục tiêu bài học

Sau bài này em sẽ hiểu được:
- **Environment variable** là gì và tại sao backend cần nó
- Tại sao phải tách `.env.example` và `.env` thành 2 file riêng
- `.gitignore` hoạt động như thế nào và tại sao `.env` phải được ignore
- Cách tổ chức biến môi trường trong dự án thực tế

---

## 🤔 Phần 1 — Environment Variable là gì?

### Vấn đề thực tế

Hãy tưởng tượng em đang viết code kết nối database:

```python
# ❌ CÁCH SAI — hardcode trực tiếp trong code
engine = create_engine("postgresql://admin:SuperSecret123@localhost/mydb")
```

Cách này có **3 vấn đề nghiêm trọng**:

| Vấn đề | Hậu quả |
|--------|---------|
| Password lộ trong code | Ai xem code trên GitHub đều thấy được |
| Khác nhau giữa máy dev và server production | Code sẽ lỗi khi deploy lên server |
| Muốn đổi password phải sửa code | Nguy hiểm, dễ quên commit |

### Giải pháp — Environment Variables

**Environment variable** (biến môi trường) là các giá trị được lưu **bên ngoài code**, trong môi trường chạy của ứng dụng:

```
┌─────────────────────────────────┐
│         Môi trường hệ thống      │
│                                 │
│  DATABASE_URL = "postgresql://…"│  ← Lưu ở đây
│  CLERK_JWKS_URL = "https://…"   │
│  ENVIRONMENT = "development"    │
│                                 │
└──────────────┬──────────────────┘
               │ đọc vào lúc chạy
               ▼
        ┌─────────────┐
        │  FastAPI app │
        └─────────────┘
```

Code của em chỉ đọc tên biến, không quan tâm giá trị thật:

```python
# ✅ CÁCH ĐÚNG — đọc từ environment
import os
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

## 📄 Phần 2 — File `.env` là gì?

Việc set từng environment variable thủ công rất bất tiện. Người ta sáng tạo ra file `.env` — một file text đơn giản chứa tất cả biến môi trường:

```
# File .env
DATABASE_URL=postgresql+asyncpg://cocoloco:cocoloco123@localhost:5432/cocoloco_db
CLERK_JWKS_URL=https://xxx.clerk.accounts.dev/.well-known/jwks.json
ENVIRONMENT=development
```

**Cú pháp của file `.env`:**
```
TÊN_BIẾN=giá_trị
# Dòng bắt đầu bằng # là comment
```

Thư viện **`pydantic-settings`** (đã cài ở task 1.2) sẽ tự động đọc file `.env` này và nạp vào ứng dụng FastAPI.

---

## 🔒 Phần 3 — Tại sao `.env` KHÔNG được commit lên Git?

### File `.env` của chúng ta chứa gì?

```
DATABASE_URL=postgresql+asyncpg://cocoloco:cocoloco123@localhost:5432/cocoloco_db
                                           ^^^^^^^^^^^
                                           Đây là PASSWORD thật của database!
```

Nếu commit file này lên GitHub/GitLab:

```
🌐 GitHub (public) → Ai cũng thấy → Hacker lấy password → Xâm nhập database → 💀
```

### Minh chứng thực tế

Đây là một trong những lỗi bảo mật phổ biến nhất:
- Hàng nghìn developer mỗi năm vô tình push `.env` lên GitHub
- Bot tự động scan GitHub 24/7 tìm các file `.env`
- Trong vòng vài phút sau khi push, hacker đã có thể exploit

### Giải pháp — `.gitignore`

File `.gitignore` nói với Git: **"Hãy bỏ qua những file này, đừng track chúng"**

```gitignore
# File .gitignore của chúng ta
.env          ← Git sẽ không bao giờ thấy file này
.env.local
.env.*.local
```

Kết quả khi chạy `git status`:
```
Untracked files:
  .env.example    ← ✅ Git thấy (sẽ commit)
  
(Không thấy .env) ← ✅ Git hoàn toàn bỏ qua
```

---

## 📋 Phần 4 — File `.env.example` là gì và tại sao cần nó?

### Vấn đề mới phát sinh

Nếu `.env` bị ignore → không commit → **đồng nghiệp khi clone project về không biết cần khai báo những biến gì!**

```
Developer mới clone project:
  $ git clone https://github.com/team/cocoloco-api
  $ uv run uvicorn app.main:app
  
  ❌ ERROR: DATABASE_URL is not set!
  
  Developer mới: "Ủa... cần set cái gì vậy???"
```

### Giải pháp — `.env.example`

File `.env.example` là một **bản template công khai** — chứa đầy đủ tên biến nhưng **không có giá trị thật** (hoặc chỉ có giá trị ví dụ):

```
# File .env.example — COMMIT lên git, ai cũng thấy
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/cocoloco_db
                                           ^^^^^^^^
                                           Giá trị ví dụ, không phải thật
CLERK_JWKS_URL=https://<your-clerk-frontend-api>/.well-known/jwks.json
ENVIRONMENT=development
```

### Quy trình làm việc chuẩn trong team

```
1. Dev A tạo .env.example → commit lên git
2. Dev B clone project về:
   $ cp .env.example .env        ← Copy template
   $ nano .env                   ← Điền giá trị thật của mình vào
   $ uv run uvicorn app.main:app ← Chạy được ngay!
```

### So sánh 2 file

|                   | `.env.example`         | `.env`                  |
|-------------------|------------------------|-------------------------|
| **Mục đích**      | Template hướng dẫn     | Chứa giá trị thật       |
| **Nội dung**      | KEY = giá trị ví dụ    | KEY = secret thật       |
| **Commit git?**   | ✅ Có                  | ❌ Không bao giờ        |
| **Ai thấy?**      | Mọi người trong team   | Chỉ mình em             |

---

## 🔍 Phần 5 — Giải thích từng biến môi trường

### `ENVIRONMENT`

```
ENVIRONMENT=development
```

**Tác dụng:** Cho ứng dụng biết đang chạy ở đâu

| Giá trị       | Môi trường            | Đặc điểm                              |
|---------------|-----------------------|---------------------------------------|
| `development` | Máy dev của em        | Bật debug mode, log chi tiết          |
| `staging`     | Server test           | Giống production nhưng để QA test     |
| `production`  | Server thật           | Tắt debug, bật bảo mật tối đa         |

Code FastAPI sau này sẽ dùng để quyết định hành vi:
```python
if settings.ENVIRONMENT == "production":
    # Tắt Swagger UI (docs) ở production vì lý do bảo mật
    app = FastAPI(docs_url=None, redoc_url=None)
```

---

### `DATABASE_URL`

```
DATABASE_URL=postgresql+asyncpg://cocoloco:cocoloco123@localhost:5432/cocoloco_db
```

Đây là **connection string** — một URL chứa tất cả thông tin để kết nối database. Hãy phân tích từng phần:

```
postgresql+asyncpg://cocoloco:cocoloco123@localhost:5432/cocoloco_db
│            │        │        │            │        │    │
│            │        │        │            │        │    └── Tên database
│            │        │        │            │        └─────── Port
│            │        │        │            └──────────────── Host (máy chủ DB)
│            │        │        └───────────────────────────── Password
│            │        └────────────────────────────────────── Username
│            └─────────────────────────────────────────────── Driver (asyncpg)
└──────────────────────────────────────────────────────────── Loại database
```

**Tại sao dùng `postgresql+asyncpg` chứ không phải `postgresql`?**

Theo rule `02-async-concurrency.md` trong `.agents/rules/`:
> "PostgreSQL operations must exclusively use the high-performance **asyncpg** driver"

- `postgresql` (psycopg2) → **synchronous** → block event loop → chậm
- `postgresql+asyncpg` → **asynchronous** → không block → nhanh hơn nhiều lần

---

### `CLERK_JWKS_URL`

```
CLERK_JWKS_URL=https://<your-clerk-frontend-api>/.well-known/jwks.json
```

**Clerk** là dịch vụ authentication (xác thực người dùng) mà Cocoloco API sử dụng.

Khi người dùng đăng nhập vào app Flutter:
```
Flutter App → Clerk → Clerk cấp JWT Token → Flutter gửi token này kèm theo mọi API request
```

FastAPI cần **xác minh** token này có hợp lệ không. Để xác minh, FastAPI cần biết **public key** của Clerk — đây chính là JWKS URL:

```
JWKS = JSON Web Key Set
     = Bộ public key của Clerk
     = Dùng để verify chữ ký của JWT token
```

Luồng xác thực:
```
1. Flutter gửi: Authorization: Bearer eyJhbGciOiJS...
2. FastAPI gọi CLERK_JWKS_URL → lấy public key
3. FastAPI dùng public key verify chữ ký token
4. Token hợp lệ → cho phép truy cập
5. Token không hợp lệ → 401 Unauthorized
```

---

## 📂 Phần 6 — Cấu trúc file sau task 1.3

```
fastapi-training/
├── .env                  ← 🔒 Secrets thật, KHÔNG commit (gitignored)
├── .env.example          ← 📋 Template công khai, COMMIT lên git
├── .gitignore            ← 📜 Quy tắc bảo vệ, liệt kê những gì cần ignore
└── ...
```

---

## 🔧 Phần 7 — Tại sao phải fix `.gitignore` cho `.agents/`?

Trong quá trình làm task này, chúng ta phát hiện ra một vấn đề ngoài ý muốn:

```gitignore
# .gitignore ban đầu có dòng:
*.md          ← Block TẤT CẢ file .md, kể cả .agents/AGENTS.md !
!README.md    ← Chỉ whitelist mỗi README.md
```

Điều này vô tình khiến các file quan trọng trong `.agents/` bị bỏ qua bởi git!

**Lệnh chẩn đoán đã dùng:**
```bash
$ git check-ignore -v .agents/AGENTS.md
.gitignore:55:*.md    .agents/AGENTS.md   ← Dòng 55, rule *.md đang block
```

**Fix bằng cách thêm exception (dấu `!`):**
```gitignore
*.md
!README.md
!.agents/**/*.md    ← Whitelist mọi .md trong .agents/ (bất kỳ độ sâu nào)
!.agents/*.md       ← Whitelist .md ngay trong .agents/
```

**Giải thích cú pháp `.gitignore`:**
- `*.md` → ignore tất cả file có đuôi `.md`
- `!README.md` → ngoại trừ `README.md`
- `!.agents/**/*.md` → ngoại trừ mọi `.md` trong bất kỳ thư mục con nào của `.agents/`
- `**` → glob pattern, khớp với bất kỳ số lượng thư mục con nào

---

## 📝 Phần 8 — Quy trình Git của task này

Chúng ta thực hiện **2 commit riêng biệt** — đây là nguyên tắc **"atomic commit"** (mỗi commit chỉ làm một việc):

```bash
# Commit 1 — chỉ cho .env.example
git commit -m "chore: add .env.example with DATABASE_URL, CLERK_JWKS_URL, ENVIRONMENT"

# Commit 2 — .gitignore fix + toàn bộ .agents/
git commit -m "chore(agents): add task tracking protocol and whitelist .agents/ markdown in gitignore"
```

**Tại sao dùng prefix `chore:`?**

Theo [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix   | Ý nghĩa                                           |
|----------|---------------------------------------------------|
| `feat:`  | Tính năng mới cho người dùng                      |
| `fix:`   | Sửa bug                                           |
| `chore:` | Công việc bảo trì, cấu hình (không ảnh hưởng app) |
| `docs:`  | Chỉ thay đổi tài liệu                             |
| `test:`  | Thêm hoặc sửa test                                |

`chore(agents):` → `chore` là loại commit, `agents` là scope (phạm vi bị ảnh hưởng)

---

## 🗺️ Phần 9 — Task 1.3 trong bức tranh toàn cục

Nhìn lại toàn bộ Phase 1 và thấy task 1.3 phục vụ cho điều gì:

```
Phase 1 — Project Setup & Infrastructure
│
├── 1.1 Initialize Project ✅     → Tạo repo, uv init, .venv
├── 1.2 Install Dependencies ✅   → fastapi, sqlalchemy, asyncpg...
├── 1.3 Environment Config ✅     → .env, .env.example  ← Đang ở đây
├── 1.4 Docker — PostgreSQL 16 🔜 → Tạo database thật để kết nối
│
Phase 2 — Database Models
│
├── 2.1 Core Database Setup       → database.py đọc DATABASE_URL ← dùng biến từ 1.3
│
Phase 3 — Authentication
│
├── 3.1 Pydantic Settings         → config.py load .env ← dùng toàn bộ file từ 1.3
├── 3.2 Clerk JWKS Verification   → security.py dùng CLERK_JWKS_URL ← từ 1.3
```

**Task 1.3 là nền tảng** — những biến vừa khai báo sẽ được tất cả các task sau sử dụng!

---

## ✅ Tóm tắt — 4 Rule vàng cần nhớ

> 💡 **Rule #1**: Secrets (password, API key, token) → KHÔNG BAO GIỜ hardcode trong code
>
> 💡 **Rule #2**: `.env` chứa secrets → KHÔNG BAO GIỜ commit lên git
>
> 💡 **Rule #3**: `.env.example` là template công khai → LUÔN commit để team biết cần khai báo gì
>
> 💡 **Rule #4**: Dùng `git check-ignore -v <file>` để chẩn đoán tại sao một file bị/không bị ignore

---

*📌 Bài tiếp theo: **Task 1.4 — Docker PostgreSQL 16** → Tạo database thật để `DATABASE_URL` có thể kết nối được!*
