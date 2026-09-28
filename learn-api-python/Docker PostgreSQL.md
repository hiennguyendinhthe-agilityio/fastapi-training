# 📖 Bài học: Docker — PostgreSQL 16

> **Task 1.4** — Ngày học: Sep 25, 2026
> Người hướng dẫn: Antigravity AI (Senior Backend Engineer)

---

## 🎯 Mục tiêu bài học

Sau bài này em sẽ hiểu được:
- **Docker** là gì và tại sao backend developer cần nó
- **Docker Compose** khác gì Docker thuần túy
- Cách tạo `docker-compose.yml` cho PostgreSQL 16
- Ý nghĩa từng dòng trong file cấu hình
- Cách chẩn đoán và xử lý lỗi **port conflict**
- Tại sao cần **named volume** để persist data
- **Healthcheck** là gì và tại sao quan trọng

---

## 🤔 Phần 1 — Vấn đề: Tại sao cần Docker?

### Cách cũ — Cài PostgreSQL thẳng vào máy

```
Dev A (macOS):  brew install postgresql@16
Dev B (Ubuntu): sudo apt install postgresql-16
Dev C (Windows): tải installer thủ công...

Server (Linux): apt install postgresql-16

Vấn đề:
❌ Mỗi người cài khác nhau → version khác nhau → bug khó tái hiện
❌ Cài thẳng vào máy → khó gỡ, conflict với project khác
❌ "Nó chạy trên máy mình mà!" → câu nói kinh điển của dev 😅
```

### Giải pháp — Docker

**Docker** là công nghệ **container hóa** — đóng gói ứng dụng + toàn bộ dependencies vào một "hộp" (container) cô lập:

```
┌─────────────────────────────────────────────────┐
│                  Máy của em                      │
│                                                  │
│  ┌──────────────────┐   ┌──────────────────────┐ │
│  │   Container 1    │   │    Container 2        │ │
│  │  PostgreSQL 16   │   │  PostgreSQL 15        │ │
│  │  (cocoloco_db)   │   │  (eth_postgres)       │ │
│  │  Port: 5433      │   │  Port: 5432           │ │
│  └──────────────────┘   └──────────────────────┘ │
│                                                  │
│  Hai PostgreSQL chạy song song, không conflict!  │
└─────────────────────────────────────────────────┘
```

**Lợi ích Docker:**

| Vấn đề trước | Giải pháp với Docker |
|-------------|---------------------|
| "Máy mình khác máy server" | Mọi người dùng cùng image → identical environment |
| Cài nhiều version conflict | Mỗi container là môi trường riêng biệt |
| Khó gỡ cài đặt | `docker compose down` → sạch hoàn toàn |
| Setup mất cả ngày | `docker compose up -d` → xong trong 30 giây |

---

## 🐳 Phần 2 — Docker vs Docker Compose

### Docker (thuần)

Chạy từng container một bằng lệnh dài:

```bash
# ❌ Cách này rất dài, khó nhớ, khó share với team
docker run \
  --name cocoloco_db \
  -e POSTGRES_USER=cocoloco \
  -e POSTGRES_PASSWORD=cocoloco123 \
  -e POSTGRES_DB=cocoloco_db \
  -p 5433:5432 \
  -v pgdata:/var/lib/postgresql/data \
  --restart unless-stopped \
  postgres:16-alpine
```

### Docker Compose

Khai báo tất cả trong file `docker-compose.yml` → chạy bằng 1 lệnh ngắn:

```bash
# ✅ Cách này ngắn gọn, dễ đọc, dễ share
docker compose up -d
```

**Docker Compose = "kịch bản" cho Docker** — khai báo một lần, ai cũng có thể chạy giống hệt.

---

## 📄 Phần 3 — Giải thích từng dòng `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16-alpine
```

**`services`**: Danh sách các container cần chạy. Dự án lớn có thể có nhiều service: `db`, `redis`, `api`, `nginx`...

**`db`**: Tên của service này (tên nội bộ trong Docker network).

**`image: postgres:16-alpine`**: Image Docker cần dùng.

```
postgres       → Tên image chính thức trên Docker Hub
:16            → Tag version (PostgreSQL 16)
-alpine        → Variant dùng Alpine Linux (nhỏ gọn ~80MB, thay vì ~400MB)
```

---

```yaml
    container_name: cocoloco_db
```

Đặt tên cố định cho container. Nếu không đặt, Docker tự sinh tên ngẫu nhiên như `fastapi-training-db-1`.

Tên cố định giúp dùng lệnh trực tiếp:
```bash
docker exec cocoloco_db pg_isready   # ✅ Dễ nhớ
docker exec fastapi-training-db-1 pg_isready  # ❌ Khó nhớ
```

---

```yaml
    restart: unless-stopped
```

Chính sách khởi động lại container khi gặp sự cố:

| Giá trị | Ý nghĩa |
|---------|---------|
| `no` | Không bao giờ tự restart |
| `always` | Luôn restart, kể cả khi `docker stop` |
| `unless-stopped` | Restart khi crash, nhưng không restart nếu ta chủ động stop |
| `on-failure` | Chỉ restart khi exit code khác 0 |

→ `unless-stopped` là lựa chọn tốt nhất cho database dev: tự động recover nếu crash, nhưng `docker compose down` vẫn dừng được.

---

```yaml
    environment:
      POSTGRES_USER: cocoloco
      POSTGRES_PASSWORD: cocoloco123
      POSTGRES_DB: cocoloco_db
      PGDATA: /var/lib/postgresql/data/pgdata
```

**Biến môi trường** truyền vào container (giống như `.env` nhưng cho Docker):

| Biến | Tác dụng | Phải khớp với |
|------|----------|---------------|
| `POSTGRES_USER` | Username của PostgreSQL | `DATABASE_URL` trong `.env` |
| `POSTGRES_PASSWORD` | Password | `DATABASE_URL` trong `.env` |
| `POSTGRES_DB` | Tên database tự động tạo khi khởi động | `DATABASE_URL` trong `.env` |
| `PGDATA` | Thư mục lưu data bên trong container | Volume mount bên dưới |

**Nguyên tắc quan trọng**: 3 giá trị `USER`, `PASSWORD`, `DB` trong Docker Compose PHẢI KHỚP CHÍNH XÁC với `DATABASE_URL` trong `.env`:

```
DATABASE_URL = postgresql+asyncpg://cocoloco:cocoloco123@localhost:5433/cocoloco_db
                                    ^^^^^^^^ ^^^^^^^^^^^                ^^^^^^^^^^^
POSTGRES_USER=cocoloco ─────────────────────┘     │                        │
POSTGRES_PASSWORD=cocoloco123 ───────────────────────┘                        │
POSTGRES_DB=cocoloco_db ────────────────────────────────────────────────────────┘
```

---

```yaml
    ports:
      - "5433:5432"
```

**Port mapping** — ánh xạ port từ host (máy em) vào container:

```
Format: "HOST_PORT:CONTAINER_PORT"

5433:5432
│     │
│     └── Port bên trong container (PostgreSQL mặc định luôn là 5432)
└──────── Port em dùng để connect từ máy ngoài (localhost:5433)
```

**Tại sao port 5433 chứ không phải 5432?**

Khi chạy `docker compose up -d` lần đầu, gặp lỗi:
```
Error: Bind for 0.0.0.0:5432 failed: port is already allocated
```

Chẩn đoán bằng lệnh:
```bash
docker ps --filter "publish=5432"
# Kết quả: container eth_postgres đang dùng port 5432
```

→ **Fix**: Đổi host port sang 5433 (container vẫn dùng 5432 nội bộ).

**Bài học**: Khi thấy lỗi port conflict, KHÔNG cần xóa container kia — chỉ cần đổi host port. Đây là cách Docker cho phép nhiều database cùng chạy trên một máy.

---

```yaml
    volumes:
      - pgdata:/var/lib/postgresql/data/pgdata
```

**Volume** là cơ chế lưu dữ liệu **bên ngoài container** để persist qua các lần restart/recreate:

```
Không có volume:
  docker compose down → Container bị xóa → 💀 Mất toàn bộ data!
  docker compose up → Container mới → Database trống rỗng

Có volume (pgdata):
  docker compose down → Container bị xóa
  docker compose up  → Container mới ← GẮN lại volume pgdata → Data vẫn còn! ✅
```

```
Máy em (host)                Container
┌──────────────┐              ┌─────────────────────────────┐
│              │              │                             │
│  pgdata      │◄────────────►│ /var/lib/postgresql/data/   │
│  (named vol) │   mount      │       pgdata/               │
│              │              │                             │
└──────────────┘              └─────────────────────────────┘
```

**Named volume vs Bind mount:**

| | Named Volume (`pgdata:/path`) | Bind Mount (`./data:/path`) |
|-|-------------------------------|------------------------------|
| Quản lý bởi | Docker | Em tự quản lý |
| Vị trí | Docker quản lý nội bộ | Thư mục cụ thể trên máy |
| Hiệu năng | Tốt hơn trên macOS | Chậm hơn trên macOS |
| Dùng cho | Database data | Config files, source code |

→ Dùng **Named Volume** cho database data là best practice.

---

```yaml
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cocoloco -d cocoloco_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
```

**Healthcheck** — Docker tự động kiểm tra container có "khỏe mạnh" không:

```
Lý do cần healthcheck:
Container "Started" ≠ PostgreSQL "Ready"

Timeline:
0s  → Container started
1s  → PostgreSQL process khởi động
3s  → PostgreSQL loading config files
5s  → PostgreSQL initializing databases
8s  → ✅ PostgreSQL READY to accept connections

Nếu FastAPI kết nối lúc 2s → ❌ Connection refused!
Nếu FastAPI đợi healthcheck "healthy" → ✅ Kết nối thành công!
```

| Config | Ý nghĩa |
|--------|---------|
| `test` | Lệnh kiểm tra. `pg_isready` = tool built-in của PostgreSQL |
| `interval: 10s` | Kiểm tra mỗi 10 giây |
| `timeout: 5s` | Nếu lệnh không trả lời trong 5s → coi là fail |
| `retries: 5` | Sau 5 lần fail liên tiếp → container "unhealthy" |
| `start_period: 10s` | Chờ 10s đầu không tính vào retries (cho DB có thời gian init) |

Trạng thái healthcheck trong `docker compose ps`:
```
STATUS
Up 18 seconds (health: starting)  ← Đang trong start_period
Up 30 seconds (healthy)           ← ✅ Sẵn sàng!
Up 5 minutes  (unhealthy)         ← ❌ Có vấn đề
```

---

```yaml
volumes:
  pgdata:
    driver: local
```

**Khai báo named volume** ở cấp top-level — bắt buộc phải có nếu dùng named volume trong services.

`driver: local` = Docker tự quản lý trên disk của máy.

---

## 🔍 Phần 4 — Các lệnh Docker cần biết

```bash
# Khởi động tất cả services (background mode)
docker compose up -d

# Xem trạng thái containers
docker compose ps

# Xem logs realtime
docker compose logs -f db

# Dừng containers (giữ nguyên data)
docker compose down

# Dừng containers VÀ xóa volumes (mất hết data!)
docker compose down -v

# Kết nối trực tiếp vào PostgreSQL bên trong container
docker exec -it cocoloco_db psql -U cocoloco -d cocoloco_db

# Kiểm tra DB có sẵn sàng nhận connections chưa
docker exec cocoloco_db pg_isready -U cocoloco -d cocoloco_db
```

---

## 🐍 Phần 5 — Verify kết nối bằng Python/asyncpg

Sau khi container healthy, verify end-to-end bằng asyncpg:

```python
import asyncio, asyncpg

async def ping():
    conn = await asyncpg.connect(
        "postgresql://cocoloco:cocoloco123@localhost:5433/cocoloco_db"
    )
    version = await conn.fetchval("SELECT version()")
    await conn.close()
    print(f"✅ Connected: {version}")

asyncio.run(ping())
# ✅ Connected: PostgreSQL 16.15 on aarch64-unknown-linux-musl...
```

**Tại sao verify bằng Python?**

- `docker compose ps` chỉ cho biết container đang chạy
- `pg_isready` chỉ kiểm tra PostgreSQL process
- **asyncpg test** = kiểm tra toàn bộ luồng: Python → asyncpg driver → Docker network → PostgreSQL → query → response

Đây là cách duy nhất đảm bảo `DATABASE_URL` trong `.env` hoạt động đúng.

---

## ⚠️ Phần 6 — Lỗi gặp phải và cách xử lý

### Lỗi 1: Docker daemon chưa chạy

```
Error: failed to connect to the docker API at unix:///Users/.../.docker/run/docker.sock
```

**Nguyên nhân**: Docker Desktop chưa mở.

**Fix**:
```bash
open -a Docker   # Mở Docker Desktop
# Đợi 20-30 giây cho daemon khởi động
docker info      # Kiểm tra daemon đã sẵn sàng
```

---

### Lỗi 2: Port conflict

```
Error: Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Nguyên nhân**: Port 5432 đang bị container khác chiếm.

**Chẩn đoán**:
```bash
# Tìm container đang dùng port 5432
docker ps --filter "publish=5432"
# → eth_postgres đang chiếm port 5432

# Hoặc tìm process native đang dùng port
lsof -ti :5432
```

**Fix**: Đổi host port trong `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"   # 5432 → 5433 cho host port
```

Và cập nhật `DATABASE_URL` trong `.env`:
```
DATABASE_URL=postgresql+asyncpg://cocoloco:cocoloco123@localhost:5433/cocoloco_db
                                                                  ^^^^
                                                                  Phải khớp
```

---

## 🗺️ Phần 7 — Task 1.4 trong bức tranh toàn cục

```
Phase 1 — Project Setup
│
├── 1.3 Environment Config ✅  → DATABASE_URL khai báo thông tin kết nối
│                                "postgresql+asyncpg://...@localhost:5433/cocoloco_db"
│
├── 1.4 Docker PostgreSQL ✅   → Tạo database thật khớp với DATABASE_URL ← Đang ở đây
│
├── 1.5 Project Structure 🔜   → Tạo thư mục app/
│
Phase 2 — Database Models
│
├── 2.1 Core Database Setup    → database.py đọc DATABASE_URL → kết nối vào container này
├── 2.5 Alembic Migrations     → Tạo bảng trong cocoloco_db
├── 2.6 Seed Data              → Nhập dữ liệu vào cocoloco_db
```

**Kết quả sau task 1.4:**

```
localhost:5433 (host) → Container cocoloco_db → PostgreSQL 16
                         ├── Database: cocoloco_db
                         ├── User: cocoloco
                         └── Volume: pgdata (persistent)
```

Từ task 2.1 trở đi, SQLAlchemy + asyncpg sẽ kết nối vào đây để tạo tables và thao tác dữ liệu.

---

## ✅ Tóm tắt — Golden Rules

> 💡 **Rule #1**: Docker giúp mọi người trong team dùng cùng một môi trường — "works on my machine" không còn là vấn đề nữa
>
> 💡 **Rule #2**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` trong Docker PHẢI KHỚP với `DATABASE_URL` trong `.env`
>
> 💡 **Rule #3**: Luôn dùng **Named Volume** cho database data — không dùng bind mount, không để data trong container
>
> 💡 **Rule #4**: Khi gặp port conflict → KHÔNG xóa container kia → chỉ đổi host port (e.g. 5432 → 5433)
>
> 💡 **Rule #5**: Verify kết nối end-to-end bằng Python/asyncpg — đừng chỉ tin vào `docker compose ps`

---

## 📋 Cheat Sheet — Lệnh hay dùng

```bash
# Khởi động
docker compose up -d

# Trạng thái
docker compose ps

# Logs
docker compose logs -f db

# Kết nối vào PostgreSQL shell
docker exec -it cocoloco_db psql -U cocoloco -d cocoloco_db

# Dừng (giữ data)
docker compose down

# Reset hoàn toàn (mất data)
docker compose down -v

# Kiểm tra port conflict
docker ps --filter "publish=5432"
lsof -ti :5432
```

---

*📌 Bài tiếp theo: **Task 1.5 — Project Structure** → Tạo toàn bộ thư mục theo Clean Architecture để chuẩn bị viết code thật sự!*
