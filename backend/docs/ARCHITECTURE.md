# ARCHITECTURE.md

## Backend

Framework:

FastAPI

---

Database:

PostgreSQL

ORM:

SQLAlchemy

Migrations:

Alembic

---

Background Jobs:

Celery + Redis

---

Communication Layer:

WhatsApp Business API

---

Frontend:

Doctor Dashboard → Next.js

Patient Interface → WhatsApp

---

Core Modules

app/models

Database tables.

---

app/services

Business logic.

---

app/api

API endpoints.

---

app/schemas

Pydantic schemas.

---

app/tests

Unit and integration tests.

---

AI Layer (Future)

Prescription summarization.

Medication schedule extraction.

Risk detection.

Patient progress summarization.

---
