# Git Workflow & Commit Standards

These rules govern how code must be committed and pushed in this workspace.
**All git operations must follow these standards without exception.**

## 1. Atomic Commits — One Logical Change Per Commit

Every commit must represent **one single, logical unit of work**. Never bundle unrelated files into a single commit.

### ✅ Correct — Separate commits per concern:
```bash
git add .gitignore
git commit -m "chore: add .gitignore for Python/uv/env files"

git add pyproject.toml
git commit -m "chore: configure pyproject.toml with project metadata"

git add uv.lock
git commit -m "chore: lock dependencies with uv.lock"

git add docker-compose.yml
git commit -m "chore: add Docker Compose for PostgreSQL 16"
```

### ❌ Wrong — Bundling everything into one commit:
```bash
git add .gitignore pyproject.toml uv.lock docker-compose.yml
git commit -m "chore: initialize project"   # Too broad, not atomic
```

---

## 2. Conventional Commits Format

All commit messages must follow the **Conventional Commits** specification:

```
<type>(<scope>): <short description>

[optional body]
[optional footer]
```

### Allowed Types:
| Type | When to use |
|:---|:---|
| `feat` | New feature or endpoint |
| `fix` | Bug fix |
| `chore` | Build, config, tooling (no production code) |
| `refactor` | Code restructure (no behavior change) |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `style` | Formatting, linting (no logic change) |
| `perf` | Performance improvement |
| `ci` | CI/CD pipeline changes |

### Examples:
```bash
# Adding a new feature
git commit -m "feat(auth): implement Clerk RS256 JWKS token verification"

# Adding a model
git commit -m "feat(models): add User model with UserRole enum"

# Config file
git commit -m "chore(config): add Pydantic Settings with .env loader"

# Fixing a bug
git commit -m "fix(orders): snapshot unit_price at order creation time"

# Adding tests
git commit -m "test(products): add happy and negative path tests for CRUD endpoints"
```

---

## 3. Grouping Rules — What Can Be In One Commit

Files **may** be grouped in one commit only if they are **tightly coupled** and have **no meaning without each other**:

| ✅ Can group together | ❌ Must be separate |
|:---|:---|
| A model file + its `__init__.py` export | Model + Schema + Repository |
| A router file + its schema file (if new feature) | Two different features |
| `alembic/env.py` + migration file (same change) | Migration + unrelated route change |
| Test file + its fixture in `conftest.py` | Tests for different modules |

---

## 4. Push Policy

- **Always push to both remotes** after committing: `gitlab` then `github`
- **Verify** with `git log --oneline -3` before pushing to confirm the commit looks right
- **Never force push** (`--force`) to `main` branch

```bash
# Standard push flow
git push gitlab main
git push github main
```

---

## 5. Branch Strategy (for future reference)

| Branch | Purpose |
|:---|:---|
| `main` | Stable, always deployable |
| `feat/<feature-name>` | New feature development |
| `fix/<bug-name>` | Bug fixes |
| `chore/<task>` | Config, tooling, dependencies |

---

## 6. Strict Markdown Local-Only Policy

- **NO Markdown Files Committed Except README & Agent Configs**:
  - The repository strictly ignores all `.md` files (`*.md`) via `.gitignore`.
  - The ONLY permitted markdown files in version control are [`README.md`](file:///Volumes/MacData/fastapi-training/README.md) and files under [`.agents/`](file:///Volumes/MacData/fastapi-training/.agents/).
  - All tracking roadmaps ([`Cocoloco FastAPI.md`](file:///Volumes/MacData/fastapi-training/Cocoloco%20FastAPI.md)) and all teaching documents in [`learn-api-python/`](file:///Volumes/MacData/fastapi-training/learn-api-python/) are strictly **local learning artifacts**.
  - **NEVER** edit `.gitignore` to whitelist or track `learn-api-python/` or `Cocoloco FastAPI.md`.
  - **NEVER** stage (`git add`) or commit any markdown file other than `README.md` or `.agents/`.

---

## 7. Quy trình 3 Bước Bắt buộc Trước Khi Triển Khai Tính Năng Mới (Short-Lived Feature Branch Protocol)

Để triệt tiêu 100% rủi ro xung đột (Git Conflicts) do lịch sử phân nhánh (diverged history) hoặc do cơ chế Squash Commits trên GitLab, **AI Agent và Kỹ sư BẮT BUỘC thực hiện đúng 3 bước này TRƯỚC KHI viết bất kỳ dòng code nào**:

### 🔹 Bước 1: Xác nhận nhánh cũ đã hoàn thành nhiệm vụ
- Sau khi một Merge Request (MR) đã được merge vào nhánh đích trên GitLab/GitHub, nhánh tính năng cũ (feature branch) được coi là **đã hoàn tất vòng đời (Closed/Deprecated)**.
- **TUYỆT ĐỐI KHÔNG TIẾP TỤC COMMIT TÍNH NĂNG MỚI LÊN NHÁNH CŨ ĐÃ MERGE.**

### 🔹 Bước 2: Chuyển về nhánh đích và kéo code mới nhất (Sync Upstream)
```bash
# 1. Chuyển về nhánh đích (nhánh chính hoặc nhánh tích hợp, ví dụ main hoặc feature/training-flutter-advance)
git checkout <target-branch>

# 2. Kéo toàn bộ mã nguồn và commit squash mới nhất về máy local
git pull origin <target-branch>   # hoặc git pull gitlab <target-branch>
```

### 🔹 Bước 3: Tạo nhánh MỚI TINH xuất phát từ code mới nhất
```bash
# Tạo nhánh mới có tên mô tả đúng tính năng (Short-lived branch)
git checkout -b <type>/<short-feature-name>

# Ví dụ thực tế:
git checkout -b feat/splash-screen-and-icon
git checkout -b fix/cart-product-id-mapping
```
- **Lợi ích sống còn**: Nhánh mới xuất phát 100% từ đỉnh của nhánh đích (`0 commits behind`). Khi tạo MR, nút Merge sẽ luôn sáng xanh (`Ready to merge`) và không bao giờ gặp xung đột do lệch commit hash!

---

## 8. Hai Mẹo Nhỏ Bất Biến Khi Thao Tác Trên GitLab (GitLab Conflict Prevention)

Khi làm việc với GitLab Merge Requests trong các dự án thực tế, AI Agent và Kỹ sư phải tuân thủ 2 mẹo vàng sau:

### 💡 Mẹo 1: Luôn bật tùy chọn "Delete source branch" khi mở Merge Request
- **Hành động**: Luôn giữ tick chọn ô **`[x] Delete source branch`** trên giao diện tạo/chỉnh sửa Merge Request của GitLab.
- **Mục đích**: Khi MR được merge thành công, GitLab sẽ tự động xóa nhánh nguồn trên remote. Điều này ngăn chặn triệt để thói quen dùng tiếp nhánh cũ, buộc lập trình viên phải tạo nhánh mới tinh ở bước tiếp theo.

### 💡 Mẹo 2: Quy tắc Đồng bộ Tức thì (Immediate Sync) nếu bắt buộc dùng lại nhánh
- **Hành động**: Trong trường hợp đặc biệt bắt buộc phải giữ lại nhánh cũ (ví dụ nhánh đào tạo dài hạn):
  - **NGAY SAU KHI** bấm Merge trên GitLab (đặc biệt khi có tick `Squash commits`), việc đầu tiên phải làm dưới local là kéo nhánh đích về và đồng bộ ngay lập tức **TRƯỚC KHI** viết thêm code:
    ```bash
    git fetch gitlab
    git merge gitlab/<target-branch>
    ```
  - **Xử lý file nhị phân (Binary Assets)**: Nếu xảy ra xung đột ở các file ảnh/icon (`.png`, `.jpg`), luôn dùng lệnh ưu tiên phiên bản của nhánh hiện tại:
    ```bash
    git checkout --ours <path/to/binary/files>
    ```
  - **TUYỆT ĐỐI KHÔNG** bắt đầu code tính năng mới khi chưa hoàn tất bước đồng bộ này.

