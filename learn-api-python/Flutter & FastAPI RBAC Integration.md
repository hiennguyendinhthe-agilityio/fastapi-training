# 📱 ↔ ⚙️ Tài liệu Kiến trúc: Tích hợp Frontend Flutter & Backend FastAPI (Authentication & RBAC)

> **Dự án**: Cocoloco Food Ordering System (AgilityIO)  
> **Tài liệu tham khảo kiến trúc**: Dành cho cả Backend Engineer (FastAPI) và Mobile Engineer (Flutter)  
> **Tác giả**: Antigravity AI & Senior Engineering Team  
> **Ngày lập**: 25/09/2026  

---

## 🎯 1. Mục đích của tài liệu

Tài liệu này được biên soạn để làm **kim chỉ nam kiến trúc (Architectural Blueprint)** kết nối đồng bộ giữa **Mobile App (Flutter)** và **API Server (FastAPI)** xoay quanh hai bài toán cốt lõi:
1. **Authentication (Xác thực danh tính)**: Người dùng là ai? (Guest vãng lai, Khách hàng đăng nhập, hay Quản trị viên).
2. **Authorization & RBAC (Phân quyền truy cập)**: Người dùng này được phép làm những hành động gì trên hệ thống?

Tài liệu này giúp team phát triển (hoặc chính em khi chuyển sang code Flutter) nắm rõ quy ước, định dạng dữ liệu, luồng nghiệp vụ thực tế và không bị bỡ ngỡ giữa lý thuyết và triển khai code.

---

## 🏛️ 2. Bức tranh tổng thể: Kiến trúc 3 Trụ cột (The Big Picture)

Hệ thống Cocoloco vận hành dựa trên 3 thành phần độc lập nhưng gắn kết chặt chẽ:

```
┌──────────────────────────┐         1. Đăng nhập / Lấy Token          ┌──────────────────────────┐
│                          │ ────────────────────────────────────────> │                          │
│   FLUTTER MOBILE APP     │ <──────────────────────────────────────── │      CLERK AUTH0/IDP     │
│       (Frontend)         │         2. Trả JWT Token (Role Claim)     │  (Identity & User Mgmt)  │
└──────────────────────────┘                                           └──────────────────────────┘
             │                                                                      ▲
             │                                                                      │
             │ 3. Gọi API kèm Header                                                │ 4. Tải Public Keys (JWKS)
             │    Authorization: Bearer <JWT>                                       │    (Chỉ tải 1 lần & Cache)
             ▼                                                                      │
┌───────────────────────────────────────────────────────────────────────────────────┴──────┐
│                               FASTAPI REST BACKEND (Resource Server)                     │
│                                                                                          │
│  [API Endpoint] ──> [JWT RS256 Verification] ──> [RBAC Guard] ──> [Database Postgres]   │
│                          (Dùng JWKS Cache)      (Check Role)      (SQLAlchemy Async)     │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Phân công trách nhiệm rõ ràng:
1. **Clerk (Identity Provider)**: 
   - Chịu trách nhiệm bảo mật danh tính, quản lý mật khẩu, OTP, Social Login (Google, Apple).
   - Cấp phát **JSON Web Token (JWT)** có chữ ký số điện tử thuật toán **RS256**.
   - Lưu trữ metadata quyền hạn (`role: "admin"` hoặc `role: "user"`).

2. **FastAPI (Resource Server / Backend)**:
   - **Người gác cổng tối cao**: Không bao giờ tin tưởng trực tiếp dữ liệu từ Client gửi lên.
   - Tự động xác thực chữ ký của Token qua **Clerk JWKS** (Public Key) lưu trong cache bộ nhớ (In-memory LRU Cache) mà không cần gọi network sang Clerk mỗi lần.
   - Đảm bảo thực thi logic nghiệp vụ và chặn các truy cập trái phép bằng HTTP Code `401 Unauthorized` hoặc `403 Forbidden`.

3. **Flutter (Client / Frontend)**:
   - Chịu trách nhiệm mang lại trải nghiệm mượt mà, trực quan (UX/UI).
   - Quản lý trạng thái phiên làm việc (Session state).
   - Tự động gắn Token vào mọi request mạng.
   - Ẩn/hiện các nút bấm, màn hình tùy theo quyền của người dùng để tránh trải nghiệm bị gián đoạn.

---

## 🎭 3. Ba Kịch bản Thực tế trên Cocoloco Mobile App

Để dễ hình dung hệ thống vận hành thế nào trong đời thực, chúng ta xét 3 đối tượng người dùng cụ thể:

```
                  ┌──────────────────────────────────────────────┐
                  │          NGƯỜI DÙNG VÀO APP COCOLOCO         │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
                 ▼                                               ▼
         [ CHƯA ĐĂNG NHẬP ]                              [ ĐÃ ĐĂNG NHẬP ]
           (Khách vãng lai)                                      │
                 │                               ┌───────────────┴───────────────┐
                 │                               │                               │
                 ▼                               ▼                               ▼
       • Xem Menu đồ uống               [ Role: USER ]                  [ Role: ADMIN ]
       • Chọn món & Thêm vào Giỏ        (Khách đặt hàng)                (Chủ quán / Staff)
       • Bấm Thanh toán: Bắt Đăng nhập          │                               │
                                                ▼                               ▼
                                      • Xem giỏ & Checkout            • Quản lý món (Thêm/Sửa)
                                      • Xem lịch sử đơn của mình      • Xem toàn bộ đơn quán
                                      • Quản lý trang cá nhân         • Đổi trạng thái đơn hàng
```

### Kịch bản 1: Khách vãng lai (Guest - Chưa đăng nhập)
* **Trải nghiệm trên Flutter**:
  - Khách tải app về máy, mở app lên là thấy ngay danh sách đồ uống (Cà phê cốt dừa, Trà nhiệt đới...) với giá tiền và hình ảnh đẹp mắt.
  - Khách thoải mái bấm chọn: size ly, mức đường, đá và bấm **"Thêm vào giỏ hàng"**.
  - **Dữ liệu giỏ hàng lúc này nằm ở đâu?** Nằm hoàn toàn ở bộ nhớ Local của app Flutter (Local State / SQLite / Hive / SharedPreferences). **Chưa cần gửi gì lên Backend.**
* **Điểm chạm (Touchpoint)**:
  - Khi khách vào tab Giỏ hàng và nhấn nút **"Tiến hành Đặt hàng (Checkout)"**:
  - App Flutter kiểm tra thấy chưa có Token hợp lệ → Bật màn hình hoặc BottomSheet: *"Vui lòng đăng nhập để Cocoloco chuẩn bị món và tích điểm cho bạn nhé!"*.
* **Tương ứng Backend FastAPI**:
  - `GET /api/v1/products`: Endpoint **PUBLIC** (không cần gắn Header `Authorization`). Bất kỳ ai gọi cũng trả về danh sách đồ uống.
  - `POST /api/v1/orders`: Endpoint **PROTECTED** (yêu cầu Token). Nếu khách cố tình gọi mà không có Token → Server trả ngay về `401 Unauthorized`.

---

### Kịch bản 2: Khách hàng thân thiết (Role: `USER`)
* **Trải nghiệm trên Flutter**:
  - Khách chọn "Đăng nhập với Google" hoặc nhập SĐT lấy OTP thông qua giao diện của Clerk.
  - Sau khi đăng nhập thành công:
    - Flutter nhận JWT Token và lưu vào bộ nhớ an toàn (`flutter_secure_storage`).
    - Giỏ hàng đã chọn lúc nãy vẫn giữ nguyên (không bị mất).
    - Khách ấn lại nút **"Đặt hàng"**: App gửi `POST /api/v1/orders` kèm theo Token.
  - Trên màn hình Profile: Khách xem được mục **"Lịch sử đơn hàng"** (`GET /api/v1/orders/me`).
* **Quy tắc phân quyền (Authorization)**:
  - Khách **chỉ xem và quản lý được đơn hàng của chính mình**.
  - Nếu khách dùng Postman cố tình gọi `GET /api/v1/orders/{id_của_người_khác}` → Backend kiểm tra thấy `order.user_id != current_user.id` → Trả ngay `403 Forbidden` (Bạn không có quyền xem đơn hàng của người khác).
  - Khách **không thấy** và **không thể gọi** các tính năng như "Thêm món mới vào thực đơn", "Xóa món".

---

### Kịch bản 3: Quản trị viên / Chủ quán (Role: `ADMIN`)
* **Trải nghiệm trên Flutter**:
  - Tài khoản Admin đăng nhập qua app.
  - App Flutter giải mã Token hoặc gọi `GET /api/v1/users/me` thấy trường `role == "ADMIN"`.
  - **Giao diện tự động thay đổi (Conditional Rendering)**:
    - Trong tab Profile hoặc thanh Navigation xuất hiện thêm một mục đặc biệt: **"Quản lý cửa hàng (Admin Hub)"**.
    - Vào mục này, Admin có các chức năng:
      - Quản lý thực đơn: Nút bấm "Thêm món mới", chỉnh sửa giá cà phê, bật/tắt trạng thái "Hết món" (`is_available = false`).
      - Quản lý đơn hàng: Màn hình Real-time hiển thị tất cả đơn khách đang đặt trong ngày (`GET /api/v1/admin/orders`).
      - Nút chuyển trạng thái đơn: `PENDING` (Chờ làm) ➔ `CONFIRMED` (Đang pha chế) ➔ `COMPLETED` (Đã giao khách).
* **Quy tắc phân quyền Backend (FastAPI Guard)**:
  - Backend sử dụng Dependency `require_role(["ADMIN"])`.
  - Nếu một User thường gọi lén vào `POST /api/v1/products` → Bị chặn đứng với mã lỗi `403 Forbidden` kèm thông điệp: `"Insufficient permissions: ADMIN role required"`.

---

## 🛠️ 4. Hướng dẫn cấu hình Role Admin trên Clerk Dashboard

Để một tài khoản biến thành `ADMIN`, chúng ta thao tác trên giao diện web của **Clerk Dashboard** theo các bước chuẩn:

### Bước 1: Gán quyền cho User cụ thể
1. Truy cập vào **Clerk Dashboard** (https://dashboard.clerk.com).
2. Vào mục **Users** ở thanh menu bên trái.
3. Tìm và click vào User muốn cấp quyền Admin (ví dụ: email `hien.admin@cocoloco.vn`).
4. Kéo xuống phần **Metadata** ➔ tìm ô **Public Metadata** ➔ Nhấn **Edit**.
5. Nhập JSON phân quyền:
   ```json
   {
     "role": "admin"
   }
   ```
6. Nhấn **Save**.

> **💡 Tại sao chọn `public_metadata` mà không chọn `private_metadata`?**
> - `private_metadata`: Chỉ backend Clerk xem được, không gắn được vào JWT token gửi về Client.
> - `public_metadata`: Được phép cấu hình để nhúng trực tiếp vào Payload của JWT Token. Nhờ đó, cả Mobile App và FastAPI đều đọc được quyền này ngay lập tức.

---

### Bước 2: Nhúng Role vào JWT Token (Clerk JWT Template)
Mặc định, JWT Token của Clerk chỉ chứa các thông tin cơ bản (`sub`, `iss`, `exp`). Để Token có chứa trường `role`, ta làm như sau:

1. Trên Clerk Dashboard, vào menu **Configure** ➔ **JWT Templates**.
2. Chọn **New Template** (hoặc chọn template mặc định `cocoloco-jwt`).
3. Trong phần Claims (JSON Editor), cấu hình thêm trường `role`:
   ```json
   {
     "role": "{{user.public_metadata.role}}",
     "email": "{{user.primary_email_address}}"
   }
   ```
4. Lưu template lại.

### Kết quả Payload JWT khi FastAPI nhận được:
```json
{
  "sub": "user_2testClerkUserId12345",
  "email": "hien.admin@cocoloco.vn",
  "role": "admin",
  "exp": 1727265600,
  "iss": "https://clerk.cocoloco.vn"
}
```

---

## 🛡️ 5. Ma trận Phân quyền API Endpoints (RBAC Matrix)

Dưới đây là thiết kế chuẩn xác cho tất cả các Endpoints trong hệ thống Cocoloco:

| Endpoint | Method | Quyền yêu cầu (Role) | Mô tả nghiệp vụ | Xử lý nếu sai quyền |
|---|---|---|---|---|
| `/health` | `GET` | **Public** | Kiểm tra trạng thái server | Ai cũng truy cập được |
| `/api/v1/products` | `GET` | **Public** | Lấy danh sách menu cà phê, bánh ngọt | Khách chưa đăng nhập vẫn xem được |
| `/api/v1/products/{id}` | `GET` | **Public** | Xem chi tiết 1 sản phẩm | Khách chưa đăng nhập vẫn xem được |
| `/api/v1/users/sync` | `POST` | `USER` hoặc `ADMIN` | Đồng bộ tài khoản từ Clerk vào Postgres | Bắt buộc có Token hợp lệ (`401`) |
| `/api/v1/users/me` | `GET` | `USER` hoặc `ADMIN` | Lấy profile cá nhân, vai trò của mình | Bắt buộc có Token hợp lệ (`401`) |
| `/api/v1/orders` | `POST` | `USER` hoặc `ADMIN` | Tạo đơn hàng mới từ giỏ hàng | Bắt buộc đăng nhập (`401`) |
| `/api/v1/orders/me` | `GET` | `USER` hoặc `ADMIN` | Xem danh sách các đơn hàng của chính mình | Chỉ lọc đơn của `current_user.id` |
| `/api/v1/orders/{id}` | `GET` | `Owner` hoặc `ADMIN` | Xem chi tiết 1 đơn hàng cụ thể | User khác xem ➔ `403 Forbidden` |
| `/api/v1/products` | `POST` | **`ADMIN`** | Tạo món ăn / thức uống mới vào menu | User thường gọi ➔ `403 Forbidden` |
| `/api/v1/products/{id}` | `PUT/PATCH` | **`ADMIN`** | Cập nhật giá tiền, sửa mô tả, ẩn món | User thường gọi ➔ `403 Forbidden` |
| `/api/v1/products/{id}` | `DELETE` | **`ADMIN`** | Xóa món khỏi thực đơn | User thường gọi ➔ `403 Forbidden` |
| `/api/v1/admin/orders` | `GET` | **`ADMIN`** | Xem toàn bộ đơn hàng của tất cả khách | User thường gọi ➔ `403 Forbidden` |
| `/api/v1/orders/{id}/status`| `PATCH` | **`ADMIN`** | Đổi trạng thái đơn (Pha chế, Hoàn thành) | User thường gọi ➔ `403 Forbidden` |

---

## 💻 6. Mẫu triển khai Code chuẩn mực

### 6.1 Phía Backend (FastAPI Guard Dependency)

```python
# app/core/security.py
from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole

# 1. Dependency lấy User hiện tại từ Token
async def get_current_user(
    token_payload: dict = Depends(verify_clerk_jwt),
    db: AsyncSession = Depends(get_db)
) -> User:
    clerk_id = token_payload.get("sub")
    user = await user_repository.get_by_clerk_id(db, clerk_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User inactive or not found"
        )
    return user

# 2. Dependency Factory kiểm tra Role (RBAC)
def require_role(allowed_roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền truy cập bị từ chối. Yêu cầu một trong các quyền: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker
```

**Cách áp dụng vào Router của FastAPI:**

```python
# app/api/v1/endpoints/products.py
from fastapi import APIRouter, Depends
from app.core.security import require_role
from app.models.user import UserRole, User

router = APIRouter()

# Public: Ai cũng xem được
@router.get("/")
async def list_products(db: AsyncSession = Depends(get_db)):
    return await product_service.get_available_products(db)

# Admin Only: Chỉ Admin mới được tạo món mới
@router.post("/", dependencies=[Depends(require_role([UserRole.ADMIN]))])
async def create_product(
    payload: ProductCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    return await product_service.create_product(db, payload)
```

---

### 6.2 Phía Frontend (Flutter Architecture Pattern)

```dart
// 1. Quản lý trạng thái Auth State với Riverpod / Bloc
enum AppRole { guest, user, admin }

class AuthState {
  final bool isAuthenticated;
  final String? token;
  final AppRole role;

  const AuthState({
    required this.isAuthenticated,
    this.token,
    this.role = AppRole.guest,
  });
}

// 2. Dio Interceptor tự động thêm Bearer Token vào mọi request
class AuthInterceptor extends Interceptor {
  final SecureStorageService _storage;
  AuthInterceptor(this._storage);

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _storage.getToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    return handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.response?.statusCode == 401) {
      // Token hết hạn -> Bắt đăng nhập lại
      EventBus.emit(LogoutEvent());
    } else if (err.response?.statusCode == 403) {
      // Báo thông báo: "Bạn không có quyền thực hiện thao tác này"
      Toast.showError("Thao tác bị từ chối: Không đủ quyền hạn!");
    }
    return handler.next(err);
  }
}

// 3. Ẩn/Hiện UI trên màn hình Profile dựa vào Role
class ProfileScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(title: const Text("Tài khoản của tôi")),
      body: ListView(
        children: [
          ListTile(title: const Text("Thông tin cá nhân")),
          ListTile(title: const Text("Lịch sử đơn hàng")),

          // CHỈ HIỂN THỊ NẾU LÀ ADMIN
          if (authState.role == AppRole.admin) ...[
            const Divider(),
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: Text("DÀNH CHO QUẢN TRỊ VIÊN", style: TextStyle(color: Colors.red)),
            ),
            ListTile(
              leading: const Icon(Icons.restaurant_menu),
              title: const Text("Quản lý thực đơn món"),
              onTap: () => Navigator.pushNamed(context, '/admin/products'),
            ),
            ListTile(
              leading: const Icon(Icons.receipt_long),
              title: const Text("Quản lý đơn hàng toàn quán"),
              onTap: () => Navigator.pushNamed(context, '/admin/orders'),
            ),
          ],
        ],
      ),
    );
  }
}
```

---

## 🏆 7. Bốn Nguyên Tắc Vàng (Golden Rules) Bất Di Bất Dịch

1. **Frontend chỉ ẩn nút để phục vụ UX — Backend là bức tường bảo mật tối thượng:**
   - Việc Flutter ẩn nút "Xóa món" chỉ giúp người dùng không bấm nhầm và giao diện sạch sẽ.
   - Luôn luôn phải có `Depends(require_role([UserRole.ADMIN]))` tại Backend để chặn kẻ xấu gọi API trực tiếp bằng Postman/Curl.

2. **Không bao giờ tin giá tiền gửi từ Client lên:**
   - Khi Flutter gọi `POST /api/v1/orders`, Client **chỉ được gửi danh sách `{ product_id, quantity }`**.
   - Backend FastAPI sẽ tự động query database để lấy giá hiện tại của sản phẩm đó và tính tổng tiền (`total_amount`). Client tuyệt đối không được tự gửi trường `total_amount` lên server!

3. **Zero-Network-Delay Authentication (Hiệu năng tối đa):**
   - Không gọi HTTP request sang Clerk ở mỗi request của người dùng.
   - Dùng public key của Clerk (.well-known/jwks.json) để giải mã và kiểm tra chữ ký RS256 ngay trong bộ nhớ RAM của FastAPI server (chỉ mất ~0.1 microsecond).

4. **Giỏ hàng Offline-First (Khách hàng là thượng đế):**
   - Cho phép khách trải nghiệm chọn món tự do lúc chưa đăng nhập.
   - Chỉ chặn ở bước cuối cùng ("Thanh toán") để tối đa hóa tỷ lệ chuyển đổi đơn hàng.

---

> 📌 **File này được lưu vĩnh viễn tại**: [`learn-api-python/Flutter & FastAPI RBAC Integration.md`](file:///Volumes/MacData/fastapi-training/learn-api-python/Flutter%20&%20FastAPI%20RBAC%20Integration.md)  
> Dùng làm tài liệu đối soát khi code Backend ở Phase 4 (Authentication & RBAC) và Phase 6 (API Routes), cũng như làm spec chuẩn khi dựng app Flutter sau này!
