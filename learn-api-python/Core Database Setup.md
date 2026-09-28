# 📖 Bài học: Core Database Setup — Asynchronous SQLAlchemy 2.0 & Session Lifecycle

> **Task 2.1** — Ngày học: Sep 28, 2026  
> Người hướng dẫn: Antigravity AI (Senior Backend Engineer & Architect)

---

## 🎯 Mục tiêu bài học

Sau bài học chuyên sâu này, em sẽ nắm vững:
1. **Bản chất của Async I/O trong Database**: Vì sao backend hiện đại bắt buộc phải dùng driver bất đồng bộ (`asyncpg`) thay vì driver đồng bộ (`psycopg2`).
2. **Cơ chế Connection Pooling**: Engine, Pool Size, Max Overflow và Pool Pre-ping hoạt động như thế nào dưới nền.
3. **Session Lifecycle & Dependency Injection**: Vòng đời của một database session trong FastAPI từ khi request đến cho tới khi kết thúc, tại sao phải dùng `AsyncGenerator` với `yield`.
4. **Cơ chế Auto-Rollback phòng vệ**: Cách cô lập giao dịch, tự động hoàn tác (rollback) khi xảy ra ngoại lệ để bảo vệ tính toàn vẹn dữ liệu.
5. **SQLAlchemy 2.0 Declarative Mapping**: Khái niệm `DeclarativeBase`, `Mapped`, `mapped_column`, và cách xây dựng model mẫu trừu tượng `TimestampedBase` với UTC timezone.
6. **Kinh nghiệm Debug thực chiến**: Xử lý lỗi cross-event-loop của asyncpg trong Pytest, cơ chế ném ngoại lệ vào generator (`athrow`), và cách mock an toàn các thuộc tính read-only của SQLAlchemy `AsyncEngine`.

---

## 🤔 Phần 1 — Vấn đề cốt lõi: Tại sao phải dùng Asynchronous Database?

### 1.1 Kịch bản nghẽn cổ chai kinh điển (Blocking I/O)

Hãy tưởng tượng một quán cà phê Cocoloco chỉ có **1 nhân viên phục vụ duy nhất** (tương tự như **Python Event Loop** chỉ chạy trên 1 Single Thread):

```
[Khách gọi món] ──► [Nhân viên nhận đơn] ──► [Vào bếp chờ pha chế 5 giây] ──► [Giao khách]
```

* **Nếu phục vụ theo kiểu Đồng bộ (Synchronous - Blocking):**  
  Khi khách A gọi Cappuccino, nhân viên nhận đơn rồi **đứng bất động trong bếp suốt 5 giây** chờ máy pha cà phê xong mới mang ra. Trong suốt 5 giây đó:
  - Khách B muốn vào order? ❌ Bị chặn ngoài cửa.
  - Khách C muốn thanh toán? ❌ Không ai phục vụ.
  - Cả quán bị "đóng băng" chỉ vì 1 câu lệnh chờ I/O!

* **Nếu phục vụ theo kiểu Bất đồng bộ (Asynchronous - Non-blocking):**  
  Nhân viên gửi đơn vào bếp (bấm nút máy pha cà phê) kèm câu lệnh `await`. Sau đó nhân viên **quay ngoắt ra quầy ngay lập tức** để đón khách B, lấy tiền khách C. Khi máy pha cà phê kêu "ting ting", nhân viên quay lại lấy ly giao cho khách A.  
  👉 Năng suất của quán tăng vọt từ 12 khách/phút lên **hàng nghìn khách/phút**!

```
Event Loop (Single Thread):
  t0: Nhận Request A ──► Gửi SQL query tới PostgreSQL (await execute())
  t1: Nhận Request B trong lúc DB đang xử lý Query A! ──► Gửi SQL query B
  t2: PostgreSQL trả về data của Request A ──► Xử lý & trả response A
  t3: PostgreSQL trả về data của Request B ──► Xử lý & trả response B
```

### 1.2 Bảng so sánh Sync vs Async Database trong Python

| Tiêu chí | Driver Đồng bộ (`psycopg2`) | Driver Bất đồng bộ (`asyncpg`) |
| :--- | :--- | :--- |
| **Giao thức mạng** | Chặn Thread gọi lệnh (Thread-blocking) | Dùng socket async không chặn Event Loop |
| **Tận dụng CPU** | Phải spawn nhiều Thread/Process (tốn RAM) | 1 Event Loop có thể gánh hàng nghìn query cùng lúc |
| **Tốc độ xử lý** | Trung bình | Gấp 3 - 5 lần so với psycopg2 truyền thống |
| **SQLAlchemy Driver URL** | `postgresql://user:pass@host/db` | `postgresql+asyncpg://user:pass@host/db` |

---

## 🏗️ Phần 2 — Kiến trúc Database Core (`app/core/database.py`)

File [`app/core/database.py`](file:///Volumes/MacData/fastapi-training/app/core/database.py) chịu trách nhiệm khởi tạo kết nối vật lý tới PostgreSQL và phân phối session cho từng API request.

```
                  ┌──────────────────────────────────────────────┐
                  │            DATABASE_URL (.env)               │
                  │ postgresql+asyncpg://cocoloco:...@localhost  │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │                 async_engine                 │
                  │  - QueuePool (pool_size=10, max_overflow=20) │
                  │  - pool_pre_ping=True                        │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │              AsyncSessionLocal               │
                  │   async_sessionmaker(expire_on_commit=False) │
                  └──────────────────────┬───────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
               HTTP Request 1 (get_db)         HTTP Request 2 (get_db)
               ┌─────────────────────┐         ┌─────────────────────┐
               │    AsyncSession     │         │    AsyncSession     │
               │  - commit / rollback│         │  - commit / rollback│
               │  - auto close()     │         │  - auto close()     │
               └─────────────────────┘         └─────────────────────┘
```

### 2.1 Chi tiết các tham số quan trọng của `async_engine`

1. **`pool_size=10`**:  
   Số lượng kết nối TCP cố định luôn được duy trì sẵn trong hồ bơi (connection pool). Khi app khởi động, pool giữ sẵn các connection này để tái sử dụng, không cần tốn chi phí 3-way handshake mở TCP mới cho mỗi request.
2. **`max_overflow=20`**:  
   Khi lượng truy cập tăng đột biến vượt quá 10 kết nối, engine được phép tạo thêm tối đa 20 kết nối tạm thời. Sau khi dùng xong, các kết nối vượt ngưỡng này sẽ tự động đóng lại. Tổng số kết nối tối đa = $10 + 20 = 30$.
3. **`pool_pre_ping=True`**:  
   Trước khi giao connection cho session, engine sẽ chạy một truy vấn kiểm tra siêu nhẹ (`ping` hoặc `SELECT 1`). Nếu connection đó đã bị PostgreSQL ngắt do timeout mạng, engine sẽ chủ động loại bỏ connection chết và cấp connection mới. Nhờ đó, ứng dụng **không bao giờ bị lỗi `ConnectionResetError`**.
4. **`normalize_database_url(url)`**:  
   Hàm tiện ích tự động chuẩn hóa URL. Nếu người dùng hoặc môi trường deploy (như Heroku/Railway) cung cấp tiền tố chuẩn `postgresql://`, hàm sẽ tự động đổi thành `postgresql+asyncpg://` để kích hoạt driver async.

### 2.2 Vòng đời của Database Session (`get_db`)

Trong FastAPI, chúng ta sử dụng cơ chế **Dependency Injection** kết hợp với **Async Generator**:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

#### Từng bước diễn ra khi một HTTP request tới:
1. **Khởi tạo**: FastAPI gọi `get_db()`. Lệnh `async with AsyncSessionLocal() as session` mượn 1 connection từ pool và mở một transaction scope.
2. **Bàn giao (`yield session`)**: Generator tạm dừng tại lệnh `yield` và trao quyền điều khiển cùng biến `session` cho Route Handler (hoặc Repository).
3. **Thực thi nghiệp vụ**: Route Handler đọc/ghi dữ liệu.
4. **Trường hợp thành công**: Route Handler chạy xong và trả về kết quả 200 OK. Generator tiếp tục chạy phần code sau `yield`, nhảy vào `finally:` để gọi `await session.close()`, trả connection sạch về pool.
5. **Trường hợp thất bại (Có lỗi ném ra)**: Nếu trong quá trình xử lý xảy ra bất kỳ lỗi gì (Pydantic validation fail, logic error, chia cho 0, database error...), ngoại lệ được truyền ngược lại vào generator. Khối `except Exception:` ngay lập tức bắt lấy và thực hiện `await session.rollback()`. Toàn bộ thay đổi chưa hoàn tất bị hủy bỏ, bảo vệ database không bị rác (dirty state). Sau đó `raise` lại lỗi để FastAPI Exception Handler trả response lỗi (400, 422, 500) tương ứng.

---

## 🏛️ Phần 3 — Mô hình thực thể mẫu (`app/models/base.py`)

Trong SQLAlchemy 2.0, cú pháp khai báo model đã được hiện đại hóa với Type Hints đầy đủ, loại bỏ hoàn toàn các kiểu dữ liệu mơ hồ của phiên bản 1.4 cũ.

### 3.1 Cấu trúc của `Base` và `TimestampedBase`

```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Lớp cơ sở gốc, nắm giữ Base.metadata để Alembic tạo migration."""
    def __repr__(self) -> str:
        attrs = [
            f"{key}={value!r}"
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        ]
        return f"{self.__class__.__name__}({', '.join(attrs)})"

class TimestampedBase(Base):
    """Model trừu tượng cung cấp 2 cột thời gian chuẩn UTC."""
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### 3.2 Tại sao thiết kế như vậy?

1. **`__abstract__ = True`**:  
   Nói với SQLAlchemy rằng: *"Đây chỉ là bản thiết kế chung (template), đừng cố tạo ra bảng `timestamped_base` trong cơ sở dữ liệu!"*. Khi các model sau này kế thừa nó (`User`, `Product`), SQLAlchemy mới gom các cột này vào bảng con tương ứng.
2. **`DateTime(timezone=True)`**:  
   Trong PostgreSQL, kiểu này chuyển hóa thành `TIMESTAMPTZ` (Timestamp with Time Zone). Dữ liệu luôn được chuẩn hóa về **UTC**, tránh hoàn toàn thảm họa lệch múi giờ khi khách hàng ở Việt Nam (GMT+7) đặt hàng với server đặt tại Mỹ (GMT-5).
3. **`server_default=func.now()`**:  
   Thời gian tạo bản ghi được lấy từ chính đồng hồ của máy chủ database (`CURRENT_TIMESTAMP`), không phụ thuộc vào đồng hồ của ứng dụng Python.
4. **`onupdate=func.now()`**:  
   Bất cứ khi nào bản ghi được cập nhật (`UPDATE`), SQLAlchemy sẽ tự động làm mới giá trị của cột `updated_at`.
5. **Hàm `__repr__` thông minh**:  
   Khi `print(user)`, thay vì in ra dòng chữ khó hiểu `<User object at 0x1034f>`, hàm `__repr__` trên sẽ in ra: `User(id=1, email='customer@cocoloco.com', full_name='Nguyen Van A')`. Đặc biệt, nó lọc bỏ các biến private `_` để không vô tình kích hoạt truy vấn lười (Lazy loading) gây crash greenlet trong môi trường async.

---

## 🔄 Phần 4 — Tích hợp Lifespan trong `app/main.py`

Chúng ta cập nhật hàm `lifespan` trong [`app/main.py`](file:///Volumes/MacData/fastapi-training/app/main.py) để quản lý trọn vẹn sự sống của kết nối Database:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── 1. Startup: Kiểm tra kết nối tới DB ──
    print("🚀 Cocoloco API starting up...")
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection established.")
    except Exception as exc:
        print(f"⚠️  Database connection check failed: {exc}")

    yield  # ── Ứng dụng chạy và phục vụ HTTP requests ──

    # ── 2. Shutdown: Giải phóng tài nguyên an toàn ──
    print("🛑 Cocoloco API shutting down...")
    await async_engine.dispose()
    print("🔌 Database engine connection pool disposed.")
```

**Lợi ích**:
* Khi ứng dụng bật lên, nếu Docker PostgreSQL chưa sẵn sàng hoặc sai password trong `.env`, hệ thống sẽ cảnh báo ngay lập tức.
* Khi ứng dụng tắt (Ctrl+C hoặc reload), `async_engine.dispose()` sẽ đóng sạch sẽ tất cả 10-30 kết nối TCP đang mở tới PostgreSQL, ngăn ngừa tình trạng cạn kiệt connection trên Database server (PostgreSQL connection leak).

---

## 🛠️ Phần 5 — Những bài học thực chiến & Debugging (Pitfalls & Debugging)

Trong quá trình triển khai và viết unit test cho Task 2.1, chúng ta đã phát hiện và xử lý **3 vấn đề kỹ thuật sâu sắc**:

### ⚠️ Lỗi 1: `RuntimeError: Task got Future attached to a different loop`
* **Hiện tượng**: Khi chạy Pytest, test case đầu tiên pass nhưng sang test case thứ hai gọi `async_engine` thì asyncpg ném lỗi xung đột event loop.
* **Nguyên nhân**: Theo mặc định, `pytest-asyncio` tạo ra một Event Loop mới cho mỗi test function (`function-scoped loop`). Trong khi đó, `async_engine` toàn cục của chúng ta giữ một connection pool kết nối tới PostgreSQL thật. Khi test 1 xong, loop 1 bị đóng; test 2 chạy trên loop 2 nhưng connection của asyncpg lại trỏ về loop 1 đã chết!
* **Giải pháp chuẩn Senior (Rule 04)**:  
  Không bao giờ để unit test đụng vào database PostgreSQL thật! Trong [`tests/conftest.py`](file:///Volumes/MacData/fastapi-training/tests/conftest.py), chúng ta thiết lập database in-memory với SQLite async:
  ```python
  from sqlalchemy.pool import StaticPool

  test_engine = create_async_engine(
      "sqlite+aiosqlite:///:memory:",
      connect_args={"check_same_thread": False},
      poolclass=StaticPool,
  )
  ```
  `StaticPool` đảm bảo mọi kết nối trong test đều trỏ về cùng một vùng nhớ RAM, hoàn toàn độc lập và không bao giờ xung đột event loop.

### ⚠️ Lỗi 2: Tại sao `mock_session.rollback()` không được gọi khi dùng `async for`?
* **Hiện tượng**: Viết test giả lập exception:
  ```python
  async for _ in get_db():
      raise RuntimeError("Lỗi")
  ```
  Test báo fail vì `rollback` không hề được gọi!
* **Bản chất Generator trong Python**: Khi ta `raise` một exception bên ngoài vòng lặp `async for`, Python sẽ ngắt vòng lặp từ phía ngoài và gọi hàm `generator.aclose()`. Lệnh `aclose()` sẽ ném ngoại lệ kiểu `GeneratorExit` (thuộc `BaseException`, không thuộc `Exception`) vào vị trí `yield`. Do đó khối `except Exception:` trong `get_db` không được kích hoạt!
* **Cách FastAPI hoạt động thực tế**: Khi route handler trong FastAPI gặp lỗi, FastAPI dùng phương thức `await gen.athrow(exception)` để chủ động ném exception thẳng vào điểm `yield`.  
  👉 Vì vậy, trong test ta phải mô phỏng chính xác hành vi của FastAPI:
  ```python
  db_gen = get_db()
  session = await anext(db_gen)
  with pytest.raises(RuntimeError):
      await db_gen.athrow(RuntimeError("Simulated database failure"))
  mock_session.rollback.assert_awaited_once()
  ```

### ⚠️ Lỗi 3: `AttributeError: 'AsyncEngine' object attribute 'connect' is read-only`
* **Hiện tượng**: Dùng `patch("app.main.async_engine.connect")` bị báo lỗi thuộc tính read-only.
* **Nguyên nhân**: Đối tượng `AsyncEngine` của SQLAlchemy được xây dựng dựa trên C-extension và descriptor slots, không cho phép gán đè trực tiếp thuộc tính `connect` bằng `setattr`.
* **Giải pháp**: Patch trực tiếp biến `app.main.async_engine` ở cấp module bằng một mock engine hoàn chỉnh thay vì can thiệp vào thuộc tính con.

---

## 🗺️ Phần 6 — Bản đồ kiến trúc: Task 2.1 kết nối với tương lai ra sao?

```
┌────────────────────────────────────────────────────────┐
│             Task 2.1: Core Database Setup              │
│       (async_engine, get_db, TimestampedBase)          │
└───────────────────────────┬────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│  Task 2.2: User Model │       │Task 2.3: Product Model│
│ Kế thừa               │       │ Kế thừa               │
│ TimestampedBase       │       │ TimestampedBase       │
└───────────┬───────────┘       └───────────┬───────────┘
            │                               │
            └───────────────┬───────────────┘
                            ▼
┌───────────────────────────────────────────────────────┐
│          Task 2.4: Order & OrderItem Models           │
│  Quan hệ: User ──< Orders ──< OrderItems >── Product  │
└───────────────────────────┬───────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────┐
│        Task 2.5: Alembic Setup & Migrations           │
│   Đọc Base.metadata để tự động sinh file migration    │
└───────────────────────────────────────────────────────┘
```

---

## 🌟 5 Nguyên tắc vàng em phải luôn ghi nhớ (Golden Rules)

1. **Tuyệt đối không dùng thư viện I/O đồng bộ trong luồng async**: Luôn dùng driver `asyncpg` (`postgresql+asyncpg://`) để bảo vệ Event Loop.
2. **Session là duy nhất cho mỗi Request (Per-Request Scope)**: Không bao giờ dùng chung một `AsyncSession` giữa các request hoặc background tasks độc lập.
3. **Mọi bảng nghiệp vụ cốt lõi đều cần Timestamp**: Kế thừa `TimestampedBase` để luôn có dấu vết kiểm toán (`created_at`, `updated_at`) theo chuẩn UTC.
4. **Phòng thủ đa tầng với Auto-Rollback**: Luôn bọc vòng đời của session trong `try...except...finally` để hoàn tác dữ liệu khi có lỗi xảy ra.
5. **Cách ly hoàn toàn Unit Test**: Unit test phải chạy trên SQLite Async in-memory (`StaticPool`), tuyệt đối không được ghi dữ liệu vào database PostgreSQL thật.
