# ArogyaAI Agent Instructions

## Project Overview

ArogyaAI is an AI-powered healthcare continuity platform. The backend is a REST API built with FastAPI, SQLAlchemy 2.0, and SQLite (development) / PostgreSQL (planned).

---

## Tech Stack

- **Framework**: FastAPI 0.137.0
- **ORM**: SQLAlchemy 2.0 (DeclarativeBase, Mapped, mapped_column)
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **Auth**: JWT (access + refresh tokens), bcrypt
- **Validation**: Pydantic v2
- **Migrations**: Alembic
- **Testing**: pytest, httpx, FastAPI TestClient
- **Runtime**: Python 3.13+, uvicorn

---

## Folder Structure

```
backend/
├── app/
│   ├── api/           # Route handlers (routers)
│   ├── cache/         # Cache platform (providers, service, feature flags)
│   ├── core/          # Config, security, logging
│   ├── database/      # Engine, session, Base
│   ├── models/        # SQLAlchemy models
│   ├── ratelimit/     # Rate limiting platform (providers, middleware, deps)
│   ├── schemas/       # Pydantic request/response schemas
│   └── services/      # Business logic layer (CRUD + DashboardService + AnalyticsService)
├── tests/
│   ├── conftest.py    # Fixtures, test DB
│   ├── test_smoke.py  # Smoke tests
│   ├── test_analytics.py  # Analytics tests
│   ├── test_cache.py      # Cache tests
│   ├── test_ratelimit.py  # Rate limit tests
│   └── ...            # Other test files
├── alembic/           # Database migrations
└── docs/              # Project documentation
```

---

## Architecture Rules

1. **Layers**: models → schemas → services → api (strict top-down; no skipping or circular deps)
2. **Build order**: Database → Models → Schemas → Services → APIs → Tests
3. **Services**: All methods are `@staticmethod`, accept `db: Session`, return ORM objects or `None`
4. **Routers**: Only authenticate, validate (Pydantic), call service, return response. No inline business logic.
5. **No circular imports**: Models never import from services or api; services import from models and schemas; api imports from services and deps.

---

## Coding Conventions

### SQLAlchemy 2.0 Rules
- Use `Mapped[]` and `mapped_column()` everywhere
- Use `DeclarativeBase` (not `declarative_base()`)
- Use `db.scalar(select(...))` for scalar queries, `db.execute(select(...))` for multi-row
- Use `db.get(Model, id)` for primary key lookups
- All models have `id` (PK, autoincrement), `created_at` (server_default=func.now())
- FK columns are nullable=True; relationships use `back_populates`
- `user_id` on Doctor/Patient is nullable FK to users.id (True)

### Pydantic / Schema Rules
- Request schemas use `BaseModel` with `Field(min_length=..., max_length=...)` matching DB column sizes
- Response schemas use `model_config = ConfigDict(from_attributes=True)`
- PATCH schemas make all fields `None` default; services use `exclude_unset=True`
- Use `EmailStr` for email fields

### FastAPI Conventions
- Router prefix matches resource name (e.g., `/users`, `/doctors`, `/patients`)
- `tags` provide Swagger grouping
- All authenticated endpoints use `Depends(get_current_user)`
- Role-restricted endpoints use `Depends(require_roles(...))` or explicit role checks in router

---

## Layer Responsibilities

### Models (`app/models/`)
- Define tables, columns, types, constraints, relationships
- No business logic, no validation, no serialization

### Schemas (`app/schemas/`)
- Define request shapes (what the client sends)
- Define response shapes (what the client receives)
- Validation rules: type checks, length constraints, email format
- `from_attributes=True` for response schemas (ORM mode)
- `exclude_unset=True` for partial updates

### Services (`app/services/`)
- All database operations (CRUD + analytics)
- Business rules and validation beyond type checking
- Static methods only; no state
- Return ORM objects or `None` (CRUD), `AnalyticsService` returns Pydantic response objects
- Accept `db: Session` as first parameter, user/data objects as needed
- `AnalyticsService` follows the same static-method pattern but returns schema objects directly

### APIs (`app/api/`)
- Route definitions with HTTP method, path, response model, status codes
- Dependency injection for `db`, `current_user`
- Call service methods; wrap results in HTTP responses or exceptions
- No inline database queries (except role resolution lookups where unavoidable)

---

## Dependency Injection Rules

- `get_db`: yields SQLAlchemy `Session`, always as `Depends(get_db)`
- `get_current_user`: validates Bearer token, returns `User` or 401
- `require_roles(*roles)`: factory for role-based access control
- Override `app.dependency_overrides[get_db]` in tests to isolate database

---

## Authentication Flow

1. Client sends `POST /auth/register` with `{email, password, role}`
2. Password is bcrypt-hashed; user stored in `users` table
3. Client sends `POST /auth/login` → server verifies password → returns `{access_token, refresh_token, token_type}`
4. Authenticated requests include `Authorization: Bearer <access_token>`
5. Access token: 30 min expiry, `{sub: user_id, role: role, type: "access"}`
6. Refresh token: 7 day expiry, `{sub: user_id, role: role, type: "refresh"}`
7. `POST /auth/refresh` with expired access token + valid refresh token → new access token
8. `POST /auth/change-password` with `{old_password, new_password}`

---

## Authorization Flow

- **Public**: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /`, `GET /health`
- **Authenticated (any role)**: `GET /users/me`, `PATCH /users/me`, `GET /doctors/me`, `PATCH /doctors/me`, `GET /patients/me`, `PATCH /patients/me`, `POST /profile/complete`
- **Doctor or Admin**: `POST /visits`, `PUT /visits/{id}`, `DELETE /visits/{id}`
- **Own-visit access**: Doctors see visits where `doctor_id == doctor.id`; patients see visits where `patient_id == patient.id`

---

## Profile Completion Flow

1. User registers → has `User` record only, no `Doctor`/`Patient` profile
2. Client calls `POST /profile/complete` with role-appropriate fields
3. Router checks `current_user.role`:
   - `DOCTOR` → `DoctorService.create_doctor_profile()` — populates `user_id`, `full_name`, `email` (from user), `phone_number`, `specialization`, `clinic_name`
   - `PATIENT` → `PatientService.create_patient_profile()` — populates `user_id`, `full_name`, `phone_number`, `date_of_birth`, `gender`, `emergency_contact`
4. Returns 409 if profile already exists
5. Returns 400 if role does not support profile completion (e.g., caregiver)

---

## Alembic Workflow

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check status
alembic current
```

Current migration: `a1c0304461c0` (add_notifications_table) — latest of 7 migration files.

---

## Testing Workflow

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app

# Run specific test file
python -m pytest tests/test_analytics.py -v
```

- Tests use isolated `test.db` SQLite (never touches `arogyaai.db`)
- `get_db` is overridden to use test database
- Each test gets a fresh transaction that rolls back on cleanup
- Fixtures: `db`, `client`, `doctor_token`, `patient_token`, `admin_token`, `doctor_with_profile`, `patient_with_profile`
- Total test count: 489 tests across 13 test files

---

## Git Workflow

- Feature branches from `main`
- Commit messages: concise, imperative mood
- No direct pushes to `main`
- PRs with summary of changes

---

## Documentation Standards

- `AGENTS.md` — engineering workflow, conventions, sprint status
- `docs/PROJECT_CONTEXT.md` — product vision, capabilities, roadmap
- `docs/ARCHITECTURE.md` — technical architecture, layers, data flow
- `docs/CURRENT_TASK.md` — current sprint status, next sprint plans
- Docs must match implementation exactly; clearly mark not-yet-implemented features as "Planned"

---

## Sprint History

### Sprint 1 — Complete
- SQLite infrastructure, Base class, SessionLocal, Alembic setup
- Doctor model, Patient model, Visit model
- Visit CRUD schemas, service (7 methods), API (5 endpoints)
- Swagger verification

### Sprint 2 — Complete
- User model with roles (admin, doctor, patient, caregiver, receptionist)
- Auth system: register, login, JWT (access + refresh), change password
- AuditLog model

### Sprint 2.5 — Complete
- User Profile API (GET/PATCH /users/me)
- Doctor Profile API (GET/PATCH /doctors/me) with schemas + service
- Patient Profile API (GET/PATCH /patients/me) with schemas + service
- Profile Completion API (POST /profile/complete)

### Sprint 2.6 — Complete
- Critical stabilization (visit auth bug fix, SECRET_KEY, .gitignore, validation)
- Automated testing: pytest, conftest.py, 12 smoke tests
- Documentation refresh

### Sprint 3.8.1 — Complete
- Enterprise Notification System (model, migration, 6 event hooks, 9 endpoints, 32 tests)

### Sprint 3.8.2 — Complete
- Global Search across 11 entities (service, RBAC, pagination, 72 tests)

### Sprint 3.8.3 — Complete
- Enterprise Dashboard APIs (Doctor, Patient, Admin dashboards)
- `DashboardService` aggregates data efficiently (no N+1, single queries)
- 3 GET endpoints: `/dashboard/doctor`, `/dashboard/patient`, `/dashboard/admin`
- 50 tests covering auth, RBAC, edge cases, response shape

### Sprint 3.8.4 — Complete
- Enterprise Analytics APIs (Platform, Doctor, Patient, System, Summary)
- `AnalyticsService` — reusable layer with 5 public methods, 12+ private helpers
- 5 GET endpoints: `/analytics/platform`, `/analytics/doctor`, `/analytics/patient`, `/analytics/system`, `/analytics/summary`
- Single-query GROUP BY patterns for time-series trends (daily/weekly/monthly)
- Growth metrics, utilization rates, most-active-doctor rankings
- Date-range filtering on all analytics endpoints
- RBAC: Admin→all, Doctor→own, Patient→own
- 50 tests covering auth, RBAC, counts, aggregations, date filters, edge cases, response shape

### Sprint 3.8.5 — Complete
- JobStatus/JobType enums, Job SQLAlchemy model
- Alembic migration `2d5dc9f0cccb` (add_jobs_table)
- Job schemas (create, response, update, retry, list, health)
- Job abstraction layer: JobRegistry, APSchedulerProvider (dev), InProcessWorker
- 10 health-task handlers via registry
- JobService — 9 static methods (submit, list, get, update, delete, retry, cancel, health, status)
- 6 job REST endpoints (all Admin-only): POST/GET /jobs, GET /jobs/health, GET/DELETE /jobs/{id}, POST /jobs/{id}/retry, POST /jobs/{id}/cancel
- Fixed route ordering: `/jobs/health` before `/{job_id}`
- Migrated `on_event` → FastAPI `lifespan` context manager (fixes DeprecationWarning)
- 42 tests (auth, RBAC, CRUD, edge cases, response shape)

### Volume 6 — Complete (Enterprise Cache Platform)
- `CacheProvider` abstract base class with `CacheStats`, `CacheEntry`, `TTL` constants
- `MemoryCacheProvider` — thread-safe in-memory dict with TTL expiry, pattern-based clear, hit/miss/eviction tracking
- `RedisCacheProvider` — Redis-backed provider with SCAN-based pattern clear, pipeline operations
- `CacheService` — static-method service with `build_key`, `get`, `set`, `get_or_set`, `invalidate_key`, `invalidate_namespace`, `clear_all`, `get_stats`, `get_many`
- Cache key naming convention: `{redis_prefix}:v1:{namespace}:{parts}`
- `FeatureFlags` — flag enable/disable/check via cache, namespaced under `feature`
- `get_cache_provider()` / `set_cache_provider()` / `reset_cache_provider()` singletons (overrideable for tests)
- DashboardService caching: all 3 dashboard methods with 5-min TTL
- AnalyticsService caching: all 5 analytics methods with 5-min TTL
- SearchService caching: global_search results with 1-min TTL
- NotificationService caching: unread count with 1-min TTL + invalidation on create/mark-read/delete
- MedicineService caching: get/list/search with 1-hour TTL + invalidation on create/update/delete
- Cache settings added to `config.py`: `CACHE_PROVIDER`, `REDIS_URL`, `REDIS_PREFIX`, 6 TTL settings
- 53 tests (provider, service, feature flags, TTL/eviction, integration with 5 services, benchmarks)

### Volume 7 — Complete (Enterprise API Protection)
- `RateLimiter` abstract base class with `RateLimitResult`, `RateLimitRule`, `RateLimitScope`
- `MemoryRateLimiter` — sliding-window log using deque per key, thread-safe, TTL-based expiry
- `RedisRateLimiter` — Redis-backed sliding window using sorted sets (ZREMRANGEBYSCORE + ZADD + ZCARD)
- `RateLimitMiddleware` — FastAPI middleware applying IP-based limits to all endpoints
- Public endpoint overrides: `/auth/login` (5/min), `/auth/register` (3/hour)
- `rate_limit()` dependency factory for per-endpoint user-specific limits
- `get_rate_limiter()` / `set_rate_limiter()` / `reset_rate_limiter()` singletons (overrideable for tests)
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- 429 JSON responses with `retry_after_seconds` detail
- Config-driven: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PROVIDER`, `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_AUTHENTICATED`, `RATE_LIMIT_LOGIN_MAX`, `RATE_LIMIT_REGISTER_MAX`, `RATE_LIMIT_BURST_MULTIPLIER`
- 35 tests (rule/result models, memory limiter, sliding window, login protection, 429 responses, edge cases, concurrent access)
- All 489 tests passing, no regressions
