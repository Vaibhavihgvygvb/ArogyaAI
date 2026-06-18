# PROJECT_CONTEXT.md

## Project Name

ArogyaAI

---

## Vision

ArogyaAI is an AI-powered healthcare continuity platform that helps doctors monitor patients between consultations and helps patients follow treatment plans correctly.

---

## Problem Statement

Patients often forget:

- Medicines prescribed
- Dosage schedules
- Lifestyle advice
- Follow-up dates

Doctors often:

- Treat hundreds of patients daily
- Cannot remember patient progress between visits
- Lack visibility into adherence and outcomes

---

## Mission

To become India's healthcare continuity layer.

---

## Primary Users

### Doctors

Need:

- Patient tracking
- Better follow-ups
- Faster consultations

---

### Patients

Need:

- Medicine reminders
- Clear instructions
- Progress tracking

---

## Core Workflow

Doctor logs consultation.

↓

Patient receives reminders. *(Planned)*

↓

Patient reports progress. *(Planned)*

↓

Doctor reviews progress before next consultation. *(Planned)*

---

## Non-Negotiables

- Patient safety first.
- No autonomous diagnosis.
- AI assists doctors; it does not replace them.
- HIPAA-like privacy principles.

---

## Current Capabilities — Implemented

### Authentication
- User registration with role selection (admin, doctor, patient, caregiver, receptionist)
- Password-based login with bcrypt hashing
- JWT access tokens (30 min) + refresh tokens (7 days)
- Token refresh endpoint
- Password change
- Input validation: EmailStr format, min_length=8 on passwords

### Authorization
- Bearer token authentication via `get_current_user`
- Role-based access via `require_roles()` factory
- Per-endpoint role enforcement (e.g., doctor/admin for write operations)
- Visit-level access control (own-visit filtering for doctors and patients)

### User Profiles
- `GET /users/me` — view own user record
- `PATCH /users/me` — update email

### Doctor Profiles
- `GET /doctors/me` — view own doctor profile
- `PATCH /doctors/me` — update full_name, phone_number, specialization, clinic_name
- Returns 404 if no linked Doctor record exists

### Patient Profiles
- `GET /patients/me` — view own patient profile
- `PATCH /patients/me` — update full_name, phone_number, date_of_birth, gender, emergency_contact
- Returns 404 if no linked Patient record exists

### Profile Completion
- `POST /profile/complete` — create Doctor or Patient profile based on user role
- Doctor: populates user_id, full_name, email, phone_number, specialization, clinic_name
- Patient: populates user_id, full_name, phone_number, date_of_birth, gender, emergency_contact
- Returns 409 if profile already exists
- Returns 400 for roles that don't support profiles (caregiver, receptionist)

### Visit Management
- Full CRUD: create, read (single + list), update, delete
- Doctor or Admin required for create/update/delete
- Role-based visit filtering: doctors see own patients' visits; patients see own visits
- Fields: visit_date, diagnosis, symptoms, prescription (JSON), instructions, follow_up_date, status

### Audit Logging
- `audit_logs` table exists in schema
- MedicalRecordService creates audit logs on create/update/delete
- Not yet wired into other services *(Planned)*

### Enterprise Notification System
- Full CRUD for notifications with RBAC (admin creates, users read own)
- Mark read/mark all read/archive
- Event hooks: appointment created/cancelled, AI alert, prescription issued, lab report, medical record created
- 9 REST endpoints, 32 tests

### Global Search
- Single `GET /search` endpoint searching 11 entities
- `ilike`-based partial matching with highlight generation
- RBAC: Admin sees all; Doctor sees own patients; Patient sees own data
- Pagination, sorting, date range, entity-specific, doctor/patient filters
- 72 tests

### Enterprise Dashboard APIs
- Three role-based dashboards: Doctor, Patient, Admin
- Single aggregation service (`DashboardService`) — no N+1 queries
- Doctor dashboard: profile, today's/upcoming/completed/pending appointments, total patients, recent visits/prescriptions, notifications, medical record stats, summary cards
- Patient dashboard: profile, upcoming appointments, medical history summary, prescriptions, active medications, recent visits, notifications, timeline preview, health summary cards
- Admin dashboard: entity counts (10 entities), system stats, growth metrics, platform activity, recent registrations/appointments/prescriptions, summary cards
- 50 tests covering auth, RBAC, edge cases, response shapes

### Enterprise Analytics APIs
- Six analytics modules: Platform, Doctor, Patient, System, Summary
- Single analytics service (`AnalyticsService`) — 5 public methods, 12+ private helpers
- Platform analytics: entity counts across 11 entities, daily/weekly/monthly activity trends, growth metrics (30-day lookback with percentage)
- Doctor analytics: KPIs (appointments, patients, visits, prescriptions, records), averages (per day/week), recent activity
- Patient analytics: clinical summary (visits, appointments, prescriptions, records, medications), timeline summary
- System analytics: most active doctors ranking, registration trends (daily/monthly), appointment utilization rate, prescription/visit/notification trends
- Summary: aggregated summary cards for all entity types
- All endpoints support optional `date_from`/`date_to` date range filtering
- RBAC: Admin→all, Doctor→own, Patient→own
- Single-query GROUP BY patterns for time-series aggregations
- 50 tests covering auth, RBAC, counts, date filters, edge cases, response shapes

### Enterprise Cache Platform
- `CacheProvider` abstraction with `MemoryCacheProvider` (in-memory, thread-safe, TTL expiry) and `RedisCacheProvider` (Redis-backed with SCAN pattern clear, pipeline operations)
- `CacheService` — static-method service for key naming, get/set/get_or_set, invalidation by key or namespace, bulk operations, all TTL-tiered
- `FeatureFlags` — cache-based feature flag enable/disable/check
- Cache integrated into 5 services: DashboardService (5-min TTL), AnalyticsService (5-min TTL), SearchService (1-min TTL), NotificationService (1-min TTL + invalidation on mutations), MedicineService (1-hour TTL + invalidation on mutations)
- Cache key convention: `{redis_prefix}:v1:{namespace}:{parts}`
- Config-driven: `CACHE_PROVIDER`, `REDIS_URL`, `REDIS_PREFIX`, 6 TTL settings
- 53 tests (provider operations, service layer, feature flags, TTL/eviction, integration benchmarks)

### Automated Testing
- 454 tests across all modules
- Isolated test database (SQLite)
- Transaction rollback per test

---

## Current Database Schema

| Table | Key Columns |
|-------|-------------|
| `users` | id, email (unique), hashed_password, role (enum), is_active, is_verified, created_at, updated_at |
| `doctors` | id, user_id (FK → users), full_name, email (unique), phone_number, specialization, clinic_name, created_at |
| `patients` | id, user_id (FK → users), full_name, phone_number, date_of_birth, gender, emergency_contact, created_at |
| `visits` | id, doctor_id (FK → doctors), patient_id (FK → patients), visit_date, diagnosis, symptoms, prescription, instructions, follow_up_date, status, created_at |
| `appointments` | id, doctor_id, patient_id, appointment_date, appointment_time, reason, status (enum), notes, created_at, updated_at |
| `prescriptions` | id, visit_id, doctor_id, patient_id, diagnosis, notes, created_at, updated_at |
| `prescription_items` | id, prescription_id, medicine_name, strength, dosage, frequency, duration, quantity, route, instructions, created_at, updated_at |
| `medicines` | id, generic_name, brand_name, manufacturer, strength, dosage_form, route, drug_class, is_active, created_at, updated_at |
| `medical_records` | id, visit_id (unique), doctor_id, patient_id, chief_complaint, diagnosis, assessment, treatment_plan, height, weight, bmi, blood_pressure, pulse, temperature, oxygen_saturation, notes, created_at, updated_at |
| `notifications` | id, user_id, title, message, notification_type (enum), priority (enum), status (enum), is_read, metadata_json, action_url, read_at, created_at, updated_at |
| `audit_logs` | id, user_id, action, resource, ip_address, details, created_at |

---

## Current API Modules

| Prefix | Endpoints | Auth |
|--------|-----------|------|
| `/auth` | register, login, refresh, me, change-password | Mixed (public + authenticated) |
| `/users` | GET/PATCH /me | Authenticated (any role) |
| `/doctors` | GET/PATCH /me | Authenticated (any role) |
| `/patients` | GET/PATCH /me | Authenticated (any role) |
| `/profile` | POST /complete | Authenticated (any role) |
| `/visits` | CRUD | Doctor/Admin for write; any role for read (filtered) |
| `/appointments` | CRUD + cancel/reschedule | Doctor/Admin for write; patient cancel own |
| `/prescriptions` | CRUD | Doctor/Admin for write; any role for read (filtered) |
| `/prescription-items` | CRUD | Doctor/Admin for write; any role for read (filtered) |
| `/medicines` | CRUD + search/filter | Admin for write; any role for read |
| `/medical-records` | CRUD + by-visit | Doctor/Admin for write; any role for read (filtered) |
| `/notifications` | CRUD + mark-read + archive | Admin for write; any role for read (own) |
| `/search` | GET /search | Authenticated (RBAC-filtered) |
| `/dashboard` | GET /doctor, /patient, /admin | Role-restricted |
| `/analytics` | GET /platform, /doctor, /patient, /system, /summary | Role-restricted |
| `/chat` | POST | Public (stub) |
| `/` | GET | Public |
| `/health` | GET | Public |

---

## Current Sprint Status

### Sprint 1 — ✅ Complete
- Database infrastructure, Base class, SessionLocal
- Doctor, Patient, Visit models with relationships
- Visit CRUD service + API + Swagger verification

### Sprint 2 — ✅ Complete
- User model with roles (admin, doctor, patient, caregiver, receptionist)
- Auth system (register, login, JWT, refresh, change password)
- AuditLog model

### Sprint 2.5 — ✅ Complete
- User Profile API (GET/PATCH /users/me)
- Doctor Profile API (GET/PATCH /doctors/me)
- Patient Profile API (GET/PATCH /patients/me)
- Profile Completion API (POST /profile/complete)

### Sprint 2.6 — ✅ Complete
- Visit authorization bug fix
- SECRET_KEY hardening
- .gitignore cleanup
- Pydantic validation (EmailStr, length constraints)
- pytest infrastructure with 12 smoke tests
- Documentation refresh

### Sprint 3.x — ✅ Complete
- Appointment scheduling with state machine (28 tests)
- Prescription + PrescriptionItem CRUD (35 tests)
- Medicine catalog with search/filter (31 tests)
- MedicalRecord with BMI auto-calculation (36 tests)

### Sprint 3.8.1 — ✅ Complete
- Enterprise Notification System (32 tests)

### Sprint 3.8.2 — ✅ Complete
- Global Search across 11 entities (72 tests)

### Sprint 3.8.3 — ✅ Complete
- Enterprise Dashboard APIs (50 tests)
- Doctor, Patient, Admin dashboards
- DashboardService aggregation layer
- 3 GET endpoints: `/dashboard/doctor`, `/dashboard/patient`, `/dashboard/admin`

### Sprint 3.8.4 — ✅ Complete
- Enterprise Analytics APIs (50 tests)
- Platform, Doctor, Patient, System, Summary analytics modules
- AnalyticsService with 5 public methods, single-query GROUP BY patterns
- 5 GET endpoints: `/analytics/platform`, `/analytics/doctor`, `/analytics/patient`, `/analytics/system`, `/analytics/summary`
- Date-range filtering, growth metrics, utilization rates, most-active-doctor rankings
- RBAC: Admin→all, Doctor→own, Patient→own

### Volume 6 — ✅ Complete (Enterprise Cache Platform)
- CacheProvider abstraction (MemoryCacheProvider, RedisCacheProvider)
- CacheService with TTL tiers, key naming convention, invalidation
- Feature flags via cache
- Cache integration in Dashboard, Analytics, Search, Notification, Medicine services
- Config-driven: `CACHE_PROVIDER`, `REDIS_URL`, `REDIS_PREFIX`, 6 TTL settings
- 53 cache tests, all 454 tests passing

---

## Upcoming Roadmap *(Planned)*
- Volume 7: Enterprise API Protection (rate limiting, brute-force prevention)
- Volume 8: Enterprise Storage Platform (S3, signed URLs, file upload)
- Volume 9: Production Deployment (Docker, PostgreSQL, Redis, Nginx)
- Volume 10: Enterprise Observability (Prometheus, OpenTelemetry, structured logging)
- Volume 11: Enterprise Performance Optimization (index review, N+1 detection)
- Volume 12: Enterprise Security Hardening (OWASP Top 10, PHI handling, encryption)
