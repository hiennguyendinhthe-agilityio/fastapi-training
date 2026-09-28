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
