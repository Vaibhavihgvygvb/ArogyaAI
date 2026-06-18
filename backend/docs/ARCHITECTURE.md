# ARCHITECTURE.md

## Backend

**Framework**: FastAPI (v0.137.0)

**Database**: SQLite (development) → PostgreSQL (planned for production)

**ORM**: SQLAlchemy 2.0 (DeclarativeBase, Mapped, mapped_column)

---

## Layer Architecture

```
Presentation Layer (Swagger UI / Client)
       ↓
   API Layer (app/api/) — Routers, Depends(), HTTP status codes
       ↓
       ├── CRUD Routers → CRUD Services (per-entity business logic)
       │                     ↓
       ├── Search Router → SearchService (cross-entity search, RBAC)
       │                     ↓
       ├── Dashboard Router → DashboardService (aggregation layer)
       │                       ↓
       ├── Analytics Router → AnalyticsService (analytics/KPI layer)
       │                       ↓
       └── Jobs Router → JobService (background task orchestration)
                            ↓
Dependency Layer (app/api/deps.py) — Auth, role checks
       ↓
 Service Layer (app/services/) — Business logic, DB operations + AnalyticsService
       ↓        ↑
       └────────┴── Cache Layer (app/cache/) — CacheService, FeatureFlags
                         ↓
   Schema Layer (app/schemas/) — Pydantic request/response models
       ↓
   Model Layer (app/models/) — SQLAlchemy table definitions
       ↓
 Database Layer (app/database/) — Engine, session, Base
       ↓
      SQLite / PostgreSQL
```

The Cache Layer sits alongside the Service Layer as a cross-cutting concern. Services call `CacheService` methods directly for get/set/invalidation. The `CacheProvider` abstraction allows swapping between in-memory (`MemoryCacheProvider`), Redis (`RedisCacheProvider`), or future cluster providers without changing business logic.

---

## Folder Structure

```
backend/
├── app/
│   ├── api/              # Route handlers
│   │   ├── auth.py       # Register, login, refresh, change-password
│   │   ├── doctor.py     # GET/PATCH /doctors/me
│   │   ├── patient.py    # GET/PATCH /patients/me
│   │   ├── profile.py    # POST /profile/complete
│   │   ├── user.py       # GET/PATCH /users/me
│   │   ├── visit.py      # CRUD /visits
│   │   ├── appointment.py # CRUD /appointments
│   │   ├── prescription.py # CRUD /prescriptions
│   │   ├── prescription_item.py # CRUD /prescription-items
│   │   ├── medicine.py   # CRUD /medicines
│   │   ├── medical_record.py # CRUD /medical-records
│   │   ├── notification.py # CRUD /notifications
│   │   ├── search.py     # GET /search
│   │   ├── dashboard.py  # GET /dashboard/*
│   │   ├── analytics.py  # GET /analytics/*
│   │   ├── jobs.py       # POST/GET /jobs, /jobs/health
│   │   ├── chat.py       # POST /chat (stub)
│   │   └── deps.py       # get_current_user, require_roles, etc.
│   ├── cache/            # Cache platform
│   │   ├── base.py       # CacheProvider ABC, CacheEntry, CacheStats, TTL constants
│   │   ├── deps.py       # get_cache_provider, set_cache_provider, reset_cache_provider
│   │   ├── service.py    # CacheService (key naming, get/set, invalidation, stats)
│   │   ├── feature_flags.py # FeatureFlags (enable/disable/check via cache)
│   │   └── providers/
│   │       ├── memory.py # MemoryCacheProvider (thread-safe, TTL, pattern clear)
│   │       └── redis.py  # RedisCacheProvider (SCAN, pipeline, JSON serialization)
│   ├── core/
│   │   ├── config.py     # Pydantic Settings (env-based, includes cache settings)
│   │   ├── security.py   # JWT, bcrypt
│   │   └── logging.py    # Logging configuration
│   ├── database/
│   │   ├── base.py       # DeclarativeBase
│   │   └── session.py    # Engine, SessionLocal, get_db
│   ├── jobs/             # Background job orchestration
│   │   ├── base.py       # JobDefinition, WorkerBase, SchedulerProvider
│   │   ├── registry.py   # JobRegistry (job_type → handler mapping)
│   │   ├── scheduler.py  # APSchedulerProvider (dev scheduler)
│   │   ├── tasks/        # Task handlers
│   │   └── workers/      # Worker implementations
│   ├── models/
│   │   ├── user.py       # User (roles, auth)
│   │   ├── doctor.py     # Doctor profile
│   │   ├── patient.py    # Patient profile
│   │   ├── visit.py      # Visit/consultation
│   │   ├── appointment.py # Appointment scheduling
│   │   ├── prescription.py # Prescriptions
│   │   ├── prescription_item.py # Prescription line items
│   │   ├── medicine.py   # Medicine catalog
│   │   ├── medical_record.py # Clinical records
│   │   ├── notification.py # Notification system
│   │   ├── audit_log.py  # Audit trail
│   │   └── enums.py      # UserRole, AppointmentStatus, Notification enums
│   ├── schemas/          # Pydantic request/response schemas
│   └── services/         # Business logic (CRUD + DashboardService + AnalyticsService + CacheService)
├── tests/
│   ├── conftest.py       # Fixtures, test DB, cache provider
│   ├── test_smoke.py     # 12 smoke tests
│   ├── test_search.py    # 72 search tests
│   ├── test_dashboard.py # 50 dashboard tests
│   ├── test_analytics.py # 50 analytics tests
│   ├── test_cache.py     # 53 cache tests
│   └── ...               # Other test files
├── alembic/              # Migrations
└── docs/                 # Project documentation
```

---

## Authentication Flow

```
Client                          Server
  │                                │
  │  POST /auth/register           │
  │  {email, password, role}       │
  │ ──────────────────────────────>│  hash_password(password)
  │                                │  store in users table
  │  <── 201 UserResponse ────────│
  │                                │
  │  POST /auth/login              │
  │  {email, password}             │
  │ ──────────────────────────────>│  verify_password()
  │  <── 200 Token ───────────────│  {access_token, refresh_token}
  │                                │
  │  GET /protected-endpoint       │
  │  Authorization: Bearer <at>    │
  │ ──────────────────────────────>│  decode_access_token()
  │                                │  get_current_user() → User
  │  <── 200 Response ────────────│
  │                                │
  │  POST /auth/refresh            │
  │  {refresh_token}               │
  │ ──────────────────────────────>│  validate type="refresh"
  │  <── 200 Token ───────────────│  {new access_token, same refresh_token}
```

### JWT Payload

```json
// Access Token (expires: 30 min)
{"sub": "1", "role": "doctor", "type": "access", "exp": 1718000000}

// Refresh Token (expires: 7 days)
{"sub": "1", "role": "doctor", "type": "refresh", "exp": 1718600000}
```

---

## Profile Completion Flow

```
Client                          Server
  │                                │
  │  POST /profile/complete        │
  │  Authorization: Bearer <token> │
  │  {full_name, phone_number, ...}│
  │ ──────────────────────────────>│
  │                                │  get_current_user() → user
  │                                │  ┌─ user.role == DOCTOR?
  │                                │  │  → DoctorService.create_doctor_profile()
  │                                │  │  → sets user_id, email from user
  │                                │  └─ user.role == PATIENT?
  │                                │     → PatientService.create_patient_profile()
  │                                │     → sets user_id from user
  │  <── 200 Profile ─────────────│
```

---

## Visit Workflow

```
Doctor                          Server                        Patient
  │                               │                               │
  │  POST /visits (Doctor/Admin)  │                               │
  │  {doctor_id, patient_id, ...} │                               │
  │ ─────────────────────────────>│                               │
  │                               │  VisitService.create_visit()  │
  │ <──── 201 Visit ─────────────│                               │
  │                               │                               │
  │                               │                               │  GET /visits
  │                               │  VisitService.get_all_visits()│
  │                               │  Filter: patient_id == pat.id │
  │                               │ <──── 200 [visits] ──────────│
  │                               │                               │
  │  GET /visits (Doctor)         │                               │
  │  VisitService.get_all_visits()│                               │
  │  Filter: doctor_id == doc.id  │                               │
  │ <──── 200 [visits] ──────────│                               │
```

### Access Control Matrix

| Endpoint | Anonymous | Patient | Doctor | Admin |
|----------|-----------|---------|--------|-------|
| POST /visits | ❌ | ❌ | ✅ | ✅ |
| GET /visits | ❌ | Own only | Own only | All |
| GET /visits/{id} | ❌ | Own only | Own only | ✅ |
| PUT /visits/{id} | ❌ | ❌ | Own only | ✅ |
| DELETE /visits/{id} | ❌ | ❌ | Own only | ✅ |

---

## Relationship Diagram

```
users (User)
  │
  ├── 1:1 ── doctors (Doctor)
  │              │
  │              ├── 1:N ── visits (Visit) ── 1:1 ── medical_records (MedicalRecord)
  │              │              │
  │              │              └── 1:N ── prescriptions (Prescription)
  │              │                              │
  │              │                              └── 1:N ── prescription_items (PrescriptionItem)
  │              │
  │              └── 1:N ── appointments (Appointment)
  │
  ├── 1:1 ── patients (Patient)
  │              │
  │              ├── 1:N ── visits (Visit)
  │              ├── 1:N ── appointments (Appointment)
  │              ├── 1:N ── prescriptions (Prescription)
  │              └── 1:N ── medical_records (MedicalRecord)
  │
  └── 1:N ── notifications (Notification)

medicines (Medicine) — standalone catalog (no FK relationships)
audit_logs (AuditLog) — standalone audit trail
```

- `Doctor.user_id → User.id` (nullable)
- `Patient.user_id → User.id` (nullable)
- `Visit.doctor_id → Doctor.id` (required)
- `Visit.patient_id → Patient.id` (required)
- `Appointment.doctor_id → Doctor.id` (required)
- `Appointment.patient_id → Patient.id` (required)
- `Prescription.visit_id → Visit.id` (required)
- `Prescription.doctor_id → Doctor.id` (required)
- `Prescription.patient_id → Patient.id` (required)
- `PrescriptionItem.prescription_id → Prescription.id` (required)
- `MedicalRecord.visit_id → Visit.id` (required, unique)
- `MedicalRecord.doctor_id → Doctor.id` (required)
- `MedicalRecord.patient_id → Patient.id` (required)
- `Notification.user_id → User.id` (required)

---

## Dependency Rules

```
api/ ───> services/ ───> schemas/ ───> models/ ───> database/
  │         │               │                           │
  │         ├──> cache/     │      (cache import)        │
  │         │    service.py                               │
  │         │    feature_flags.py                         │
  │         │       │                                     │
  │         │       └──> cache/deps.py                    │
  │         │              │                              │
  │         │              └──> cache/providers/          │
  │         │                     memory.py               │
  │         │                     redis.py                │
  │         │                                             │
  └────────> deps.py ──> core/security.py                 │
                           │                              │
                           └──> core/config.py             │
                                                          │
                          core/logging.py ────────────────┘
```

- Models never import from services, schemas, cache, or api
- Services import from models, schemas, and cache (CacheService for caching)
- API imports from services, schemas, models, and deps
- Cache layer is a cross-cutting concern: services import CacheService directly
- Core modules (config, security, logging) are standalone
- Tests import from app, override `get_db` to isolate database

---

## Background Jobs *(Planned)*

- Celery + Redis for reminders and notifications

## Communication Layer *(Planned)*

- WhatsApp Business API for patient notifications

## Frontend *(Planned)*

- Doctor Dashboard → Next.js
- Patient Interface → WhatsApp
