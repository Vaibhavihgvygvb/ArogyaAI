# CURRENT_TASK.md

## Sprint Status

Sprint 3.8.3 ✅ **Complete** — Enterprise Dashboard APIs

---

## What Was Built

### Sprint 1 — Foundation
- SQLite database infrastructure, Base class, SessionLocal
- Doctor model (`app/models/doctor.py`)
- Patient model (`app/models/patient.py`)
- Visit model (`app/models/visit.py`) with FK relationships
- Pydantic schemas (`app/schemas/visit.py`): VisitBase, VisitCreate, VisitUpdate, VisitResponse
- Visit CRUD Service (`app/services/visit_service.py`): 7 methods
- Visit REST API (`app/api/visit.py`): 5 endpoints (POST, GET list, GET by ID, PUT, DELETE)
- Alembic migration: `a0e420dac08c` (initial_complete_schema)
- Swagger UI verification at `/docs`

### Sprint 2 — Authentication & User Management
- User model (`app/models/user.py`) with roles (ADMIN, DOCTOR, PATIENT, CAREGIVER, RECEPTIONIST)
- Auth system: register, login, JWT (access + refresh), change password
- AuditLog model (`app/models/audit_log.py`)

### Sprint 2.5 — Profiles
- User Profile API: GET/PATCH /users/me
- Doctor Profile API: GET/PATCH /doctors/me (DoctorUpdate, DoctorResponse)
- Patient Profile API: GET/PATCH /patients/me (PatientUpdate, PatientResponse)
- Profile Completion API: POST /profile/complete (role-based, returns 409 on duplicate)

### Sprint 2.6 — Stabilization & Testing
- Visit patient authorization bug fix (was comparing patient_id with user_id directly)
- SECRET_KEY default changed to `dev-only-insecure-change-in-production`
- .gitignore updated (env, pycache, coverage, etc.)
- Pydantic validation: EmailStr on all email fields, min_length/max_length constraints
- pytest infrastructure: conftest.py with 7 fixtures, test_smoke.py with 12 smoke tests
- All tests passing with isolated SQLite test database
- Documentation refresh (AGENTS.md, PROJECT_CONTEXT.md, ARCHITECTURE.md, CURRENT_TASK.md)

### Sprint 3.x — Supporting Infrastructure
- Appointment model, CRUD service, API with state machine (28 tests)
- Prescription model, CRUD service, API (17 tests)
- PrescriptionItem model, CRUD service, API (18 tests)
- Medicine model, CRUD service, API (31 tests)
- MedicalRecord model, CRUD service, API with BMI auto-calculation (36 tests)

### Sprint 3.8.1 — Enterprise Notification System
- Notification model + enums (NotificationType, NotificationPriority, NotificationStatus)
- Alembic migration for notifications table
- 6 event-hook methods in NotificationService (appointment created/cancelled/rescheduled, AI alert, prescription issued, lab report)
- 9 REST endpoints (CRUD + mark read, mark all read, unread count, archive)
- 32 tests covering all RBAC, CRUD, filters, and event hooks

### Sprint 3.8.2 — Global Search
- `SearchResultItem` + `SearchResponse` schemas with uniform shape
- `SearchService` — 11 entity-specific methods + `global_search` orchestrator
- `GET /search` endpoint with entity filter, pagination, sorting, date range, doctor/patient filters
- RBAC enforced in service layer (Admin: all; Doctor: own patients; Patient: own data)
- `ilike`-based partial matching with highlight generation
- 72 comprehensive tests (global search, entity-specific, RBAC, pagination, sorting, filtering, edge cases)

### Sprint 3.8.3 — Enterprise Dashboard APIs
- Dashboard schemas: `DoctorDashboardResponse`, `PatientDashboardResponse`, `AdminDashboardResponse`
- Response types: `StatCard`, `RecentAppointment`, `RecentVisit`, `RecentPrescription`, `NotificationSummary`, `TimelineEvent`, `ActiveMedication`, `PlatformActivity`, `RegistrationSummary`
- `DashboardService` — 3 aggregation methods (`get_doctor_dashboard`, `get_patient_dashboard`, `get_admin_dashboard`)
- 3 REST endpoints: `GET /dashboard/doctor`, `GET /dashboard/patient`, `GET /dashboard/admin`
- Role-based access: Doctor→own dashboard, Patient→own dashboard, Admin→platform dashboard
- Efficient single queries (no N+1), COUNT aggregates, reusable helper methods
- 50 tests covering auth, RBAC, profiles, counts, summary cards, recent activity, edge cases, response shape

---

## Current API Surface (48+ endpoints)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | Public | Root welcome |
| GET | `/health` | Public | Health check + DB status |
| POST | `/chat` | Public | Chat (stub) |
| POST | `/auth/register` | Public | Register new user |
| POST | `/auth/login` | Public | Login, get JWT pair |
| POST | `/auth/refresh` | Public | Refresh access token |
| POST | `/auth/change-password` | Authenticated | Change password |
| GET | `/auth/me` | Authenticated | Get current user |
| GET | `/users/me` | Authenticated | Get user profile |
| PATCH | `/users/me` | Authenticated | Update user email |
| GET | `/doctors/me` | Authenticated | Get doctor profile |
| PATCH | `/doctors/me` | Authenticated | Update doctor profile |
| GET | `/patients/me` | Authenticated | Get patient profile |
| PATCH | `/patients/me` | Authenticated | Update patient profile |
| POST | `/profile/complete` | Authenticated | Complete profile (role-based) |
| POST | `/visits` | Doctor/Admin | Create visit |
| GET | `/visits` | Authenticated | List visits (filtered by role) |
| GET | `/visits/{id}` | Authenticated | Get visit (own only) |
| PUT | `/visits/{id}` | Doctor/Admin | Update visit |
| DELETE | `/visits/{id}` | Doctor/Admin | Delete visit |
| POST | `/appointments` | Doctor/Admin | Create appointment |
| GET | `/appointments` | Authenticated | List appointments (filtered by role) |
| GET | `/appointments/{id}` | Authenticated | Get appointment by ID |
| PATCH | `/appointments/{id}` | Doctor/Admin | Update appointment |
| DELETE | `/appointments/{id}` | Doctor/Admin | Delete appointment |
| POST | `/prescriptions` | Doctor/Admin | Create prescription |
| GET | `/prescriptions` | Authenticated | List prescriptions (filtered by role) |
| GET | `/prescriptions/{id}` | Authenticated | Get prescription by ID |
| PATCH | `/prescriptions/{id}` | Doctor/Admin | Update prescription |
| DELETE | `/prescriptions/{id}` | Doctor/Admin | Delete prescription |
| POST | `/prescription-items` | Doctor/Admin | Create prescription item |
| GET | `/prescription-items` | Authenticated | List prescription items |
| GET | `/prescription-items/{id}` | Authenticated | Get prescription item |
| PATCH | `/prescription-items/{id}` | Doctor/Admin | Update prescription item |
| DELETE | `/prescription-items/{id}` | Doctor/Admin | Delete prescription item |
| POST | `/medicines` | Admin | Create medicine |
| GET | `/medicines` | Authenticated | List medicines |
| GET | `/medicines/search` | Authenticated | Search medicines |
| GET | `/medicines/{id}` | Authenticated | Get medicine by ID |
| PATCH | `/medicines/{id}` | Admin | Update medicine |
| DELETE | `/medicines/{id}` | Admin | Delete medicine |
| POST | `/medical-records` | Doctor/Admin | Create medical record |
| GET | `/medical-records` | Authenticated | List medical records |
| GET | `/medical-records/{id}` | Authenticated | Get medical record by ID |
| GET | `/medical-records/by-visit/{visit_id}` | Authenticated | Get record by visit |
| PATCH | `/medical-records/{id}` | Doctor/Admin | Update medical record |
| DELETE | `/medical-records/{id}` | Admin | Delete medical record |
| POST | `/notifications` | Admin | Create notification |
| GET | `/notifications` | Authenticated | List notifications |
| GET | `/notifications/unread-count` | Authenticated | Unread notification count |
| GET | `/notifications/{id}` | Authenticated | Get notification |
| PATCH | `/notifications/{id}` | Admin | Update notification |
| PATCH | `/notifications/{id}/read` | Authenticated | Mark notification read |
| POST | `/notifications/mark-all-read` | Authenticated | Mark all notifications read |
| POST | `/notifications/{id}/archive` | Authenticated | Archive notification |
| DELETE | `/notifications/{id}` | Admin | Delete notification |
| GET | `/search` | Authenticated | Global search across 11 entities |
| GET | `/dashboard/doctor` | Doctor only | Aggregated doctor dashboard |
| GET | `/dashboard/patient` | Patient only | Aggregated patient dashboard |
| GET | `/dashboard/admin` | Admin only | Aggregated platform dashboard |

---

## Definition of Done

| Requirement | Status |
|---|---|
| Database models (User, Doctor, Patient, Visit, AuditLog) | ✅ |
| Alembic migration for all tables | ✅ |
| Authentication (register, login, JWT, refresh, change password) | ✅ |
| Role-based authorization (admin, doctor, patient) | ✅ |
| User Profile API (view + update) | ✅ |
| Doctor Profile API (view + update) | ✅ |
| Patient Profile API (view + update) | ✅ |
| Profile Completion (role-based, duplicate detection) | ✅ |
| Visit CRUD with role-filtered access | ✅ |
| Appointment CRUD with state machine | ✅ |
| Prescription + PrescriptionItem CRUD | ✅ |
| Medicine catalog CRUD + search/filter | ✅ |
| MedicalRecord CRUD with BMI auto-calculation | ✅ |
| Notification system (CRUD + event hooks + RBAC) | ✅ |
| Global Search (11 entities, RBAC, pagination, filtering) | ✅ |
| Enterprise Dashboard APIs (Doctor, Patient, Admin) | ✅ |
| Pydantic validation (EmailStr, length constraints) | ✅ |
| Automated tests (pytest, isolated DB, 309 tests) | ✅ |
| Documentation (AGENTS, PROJECT_CONTEXT, ARCHITECTURE, CURRENT_TASK) | ✅ |
| All endpoints pass Swagger verification | ✅ |

---

## Next Sprint: Sprint 4 — AI & Insights

### Planned
- AI Chat integration with healthcare context
- Patient timeline aggregation service (enhancement)
- Audit Log integration into remaining services
- File upload support for lab reports
- Analytics/BI dashboard enhancements
- Real-time dashboards (WebSocket)
- Redis caching for dashboard aggregation
