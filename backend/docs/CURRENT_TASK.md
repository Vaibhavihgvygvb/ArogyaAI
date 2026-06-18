# CURRENT_TASK.md

## Sprint

Sprint 1 ✅ Completed

---

## What Was Built

* **Doctor model** — `app/models/doctor.py`
* **Patient model** — `app/models/patient.py`
* **Visit model** — `app/models/visit.py` (with FK relationships to doctors & patients)
* **Pydantic schemas** — `app/schemas/visit.py` (VisitBase, VisitCreate, VisitUpdate, VisitResponse)
* **CRUD service** — `app/services/visit_service.py` (7 methods)
* **REST API** — `app/api/visit.py` (5 endpoints: POST, GET list, GET by ID, PUT, DELETE)
* **Swagger verification** — All endpoints tested and confirmed working

---

## Definition of Done

| Requirement | Status |
|---|---|
| Doctor model exists | ✅ |
| Patient model exists | ✅ |
| Visit model exists with FK relationships | ✅ |
| Pydantic schemas for request/response | ✅ |
| CRUD service with create, read, update, delete | ✅ |
| REST API endpoints for visits | ✅ |
| Doctor can log patient visits | ✅ |
| Visits can be retrieved | ✅ |
| Swagger UI loads at `/docs` | ✅ |

---

---

## Next Sprint

Sprint 2 — Medication & Reminder Foundation

### Objectives

* Medication model (structured prescriptions with dosage, frequency, duration)
* Medication CRUD service + API
* Reminder scheduling infrastructure
* Medication adherence tracking
* Unit tests for new models and services
