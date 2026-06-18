# PROJECT_CONTEXT.md

## Project Name

ArogyaAI

---

## Vision

ArogyaAI is an AI-powered healthcare continuity platform that helps doctors monitor patients between consultations and helps patients follow treatment plans correctly.

---

## Problem Statement

Patients often forget:

* Medicines prescribed
* Dosage schedules
* Lifestyle advice
* Follow-up dates

Doctors often:

* Treat hundreds of patients daily
* Cannot remember patient progress between visits
* Lack visibility into adherence and outcomes

---

## Mission

To become India's healthcare continuity layer.

---

## Primary Users

### Doctors

Need:

* Patient tracking
* Better follow-ups
* Faster consultations

---

### Patients

Need:

* Medicine reminders
* Clear instructions
* Progress tracking

---

## Core Workflow

Doctor logs consultation.

↓

Patient receives reminders.

↓

Patient reports progress.

↓

Doctor reviews progress before next consultation.

---

## Non-Negotiables

* Patient safety first.
* No autonomous diagnosis.
* AI assists doctors; it does not replace them.
* HIPAA-like privacy principles.

---

## Sprint 1 — Completed

Backend foundation built and verified:

| Component | Status |
|---|---|
| SQLite database infrastructure | ✅ Done |
| Doctor model (`doctors` table) | ✅ Done |
| Patient model (`patients` table) | ✅ Done |
| Visit model (`visits` table) with FK relationships | ✅ Done |
| Pydantic schemas (Base, Create, Update, Response) | ✅ Done |
| Visit CRUD Service (7 methods) | ✅ Done |
| REST API endpoints (POST, GET, PUT, DELETE /visits) | ✅ Done |
| Swagger UI verification at `/docs` | ✅ Verified |

All endpoints tested manually — create, read (single + list), update, and delete operations confirmed working against SQLite.

---
