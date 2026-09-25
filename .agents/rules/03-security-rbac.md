# Security, RBAC & Exception Handling Rules

These rules enforce distributed authentication, role-based access control, and centralized error handling for the **FastAPI Practice (Blogging Platform API)**.

## 1. Asymmetric Stateless JWT Authentication (RS256 & JWKS)
* **Asymmetric Verification**: The API uses **RS256** (asymmetric RSA with SHA-256). Clerk holds the Private Key in the cloud; the backend strictly decodes tokens using Public Keys fetched from `CLERK_JWKS_URL`.
* **Zero Secret Key Storage**: The backend server must NEVER store or require private signing keys in `.env`.
* **PyJWKClient LRU Caching**: To prevent network saturation and Clerk rate-limiting (HTTP 429), the JWKS client MUST be cached in memory via `@lru_cache(maxsize=1)` ([`app/core/security.py`](file:///Volumes/MacData/fastapi-training/app/core/security.py)).
* **Clock Skew Tolerance (5s Leeway)**: All JWT decode calls must include `leeway=5` to prevent `ImmatureSignatureError` or premature expiration caused by microscopic server clock drifts.

## 2. Real-Time Revocation (Soft-Disable Active Guard)
* **Hybrid Authentication Guard**: Although JWT is stateless, every authenticated request resolved via `get_current_user` ([`app/api/deps.py`](file:///Volumes/MacData/fastapi-training/app/api/deps.py)) must verify the user's database status:
  ```python
  if not user.is_active:
      raise HTTPException(status_code=403, detail="User account is deactivated")
  ```
* **Instant Lockout**: When an administrator toggles an account to disabled (`is_active = False`), access must be revoked in real-time without waiting for the JWT expiration window to elapse. Disabled users cannot perform any actions.

## 3. RBAC 2-Tier & Resource Ownership Guard
* **Role Hierarchy**: System recognizes two primary roles: **`ADMIN`** and **`USER`** ([`app/models/user.py`](file:///Volumes/MacData/fastapi-training/app/models/user.py)).
* **Post Ownership Guard**:
  * Normal users (`USER`) can create posts, view other users' posts, but can ONLY update (`PUT`/`PATCH`) or delete (`DELETE`) posts authored by themselves (`post.author_id == current_user.id`).
  * Attempting to alter another user's post without Admin privileges must return `HTTP 403 Forbidden`.
* **Admin Role Authority**:
  * Administrators possess full access to manage (view, update, delete) all users' posts.
  * Administrators can enable/disable user accounts (`is_active`).
  * Only administrators can retrieve the full user list (`GET /api/v1/users`).
* **Profile Privacy Principle**:
  * Users can view and update their own personal profile (`GET /api/v1/users/me/profile`, `PUT /api/v1/users/me/profile`).
  * Administrators CANNOT edit a user's personal profile (strict domain boundary).
* **Admin Self-Lock Guard**:
  * An administrator is strictly prohibited from disabling their own account (`target_user_id == current_user.id`).
  * The API must immediately abort with `HTTP 400 Bad Request: 'Admin cannot disable themselves'` to prevent orphaned system states.

## 4. Centralized Exception Handling & Zero Data Exposure
* **Single Source of Truth**: All application exceptions must be caught and transformed in [`app/core/exceptions.py`](file:///Volumes/MacData/fastapi-training/app/core/exceptions.py).
* **Standardized HTTP Status Envelopes**:
  * `400 Bad Request`: Business rule violations (self-lock, invalid status transition).
  * `401 Unauthorized`: Missing, invalid, or expired Bearer JWT tokens.
  * `403 Forbidden`: RBAC permission failures or deactivated accounts.
  * `404 Not Found`: Missing resources (post, user, category).
  * `409 Conflict`: Unique constraint collisions (duplicate emails or slugs).
  * `422 Unprocessable Entity`: Pydantic schema validation failures.
  * `500 Internal Server Error`: Unhandled runtime exceptions.
* **No Leaky Stack Traces**: Raw database exceptions (e.g. `sqlalchemy.exc.IntegrityError`, connection timeouts) must never expose internal SQL queries, table names, or database credentials to the client.
