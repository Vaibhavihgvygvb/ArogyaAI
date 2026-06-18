# ARCHITECTURE.md

## Backend

Framework:

FastAPI (v0.137.0)

---

Database:

SQLite (development) → PostgreSQL (planned for production)

ORM:

SQLAlchemy 2.0 (DeclarativeBase, Mapped, mapped_column)

---

Background Jobs (Future):

Celery + Redis

---

Communication Layer (Future):

WhatsApp Business API

---

Frontend (Future):

Doctor Dashboard → Next.js

Patient Interface → WhatsApp

---

## Models (`app/models`)

| Model | Table | Status |
|---|---|---|
| `Doctor` | `doctors` | ✅ Complete — id, full_name, email, phone_number, specialization, clinic_name, created_at |
| `Patient` | `patients` | ✅ Complete — id, full_name, phone_number, date_of_birth, gender, emergency_contact, created_at |
| `Visit` | `visits` | ✅ Complete — id, doctor_id (FK), patient_id (FK), visit_date, diagnosis, symptoms, prescription (JSON), instructions, follow_up_date, status, created_at |

All models inherit from `Base` (SQLAlchemy `DeclarativeBase`). Relationships: Doctor → visits (one-to-many), Patient → visits (one-to-many).

---

## Schemas (`app/schemas`)

| Schema | Purpose |
|---|---|
| `ChatRequest` / `ChatResponse` | Chat endpoint |
| `VisitBase` | Shared Visit fields |
| `VisitCreate` | Input for POST /visits |
| `VisitUpdate` | Input for PUT /visits (all optional) |
| `VisitResponse` | Output — includes id, created_at, ORM-compatible |

---

## Services (`app/services`)

| Service | Methods |
|---|---|
| `VisitService` | create_visit, get_visit_by_id, get_all_visits, get_visits_by_patient, get_visits_by_doctor, update_visit, delete_visit |

All methods are static, accept SQLAlchemy `Session`, return ORM objects or None.

---

## API (`app/api`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Chat endpoint |
| `GET` | `/` | Root welcome message |
| `GET` | `/health` | Health check |
| `POST` | `/visits` | Create visit |
| `GET` | `/visits` | List visits (skip, limit) |
| `GET` | `/visits/{id}` | Get visit by ID |
| `PUT` | `/visits/{id}` | Update visit |
| `DELETE` | `/visits/{id}` | Delete visit |

---

## Tests (`app/tests`)

Status: Not yet implemented.

---

## AI Layer (Future)

* Prescription summarization.
* Medication schedule extraction.
* Risk detection.
* Patient progress summarization.

---
