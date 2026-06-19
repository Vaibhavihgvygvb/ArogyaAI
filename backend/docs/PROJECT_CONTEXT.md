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

### AI Platform Foundation
- **Provider Abstraction**: `LLMProvider` ABC with `OllamaProvider` (local), `OpenAIProvider` (cloud), `MockLLMProvider` (tests)
- **Prompt Registry**: `PromptManager` ABC + `PromptRegistry` with template versioning, automatic variable extraction, tag-based filtering
- **Memory Layer**: `MemoryManager` ABC + `InMemoryMemoryManager` with conversation CRUD, context window management, token budgeting, automatic truncation
- **Safety Layer**: `SafetyService` ABC + `DefaultSafetyService` with input validation, prompt injection detection (10 patterns), PHI detection (8 patterns including SSN, email, phone, aadhaar, passport, credit card), dangerous content detection, configurable enable/disable
- **AI Gateway**: `GatewayService` ABC + `GatewayPipeline` orchestrating prompt builder → memory injection → LLM provider → safety check → response formatter; supports both streaming and non-streaming
- **Token Counter**: `estimate_tokens`, `estimate_messages_tokens`, `truncate_to_token_limit`, `truncate_messages` utilities
- **AI API Endpoints (7)**: `POST /ai/generate`, `POST /ai/prompts`, `GET /ai/prompts`, `GET /ai/prompts/{name}`, `POST /ai/conversations`, `DELETE /ai/conversations/{id}`, `POST /ai/safety/check`, `GET /ai/provider`
- **Configuration**: `AISettings` nested in `Settings.AI` — active provider, model, temperature, max_tokens, safety level, memory settings, and more — all configurable via .env
- **Dependency Injection**: All AI components follow get/set/reset singleton pattern (same as cache & ratelimit), overrideable in tests
- **Exception Hierarchy**: 14 AI-specific exception types (`ProviderError`, `PromptNotFoundError`, `SafetyError`, `GatewayError`, etc.)
- **No Medical Logic**: This sprint is pure infrastructure — no medical knowledge, RAG, chatbot, or agents
- **54 tests** across all AI modules, all using `MockLLMProvider` (no live LLM required)

### Enterprise Knowledge Platform
- **7 Document Loaders**: TextLoader (TXT/MD), CSVLoader, JSONLoader, HTMLLoader, PDFLoader (3 library fallbacks: PyPDF2, pdfplumber, pdfminer), DOCXLoader (python-docx optional)
- **5 Normalizers**: WhitespaceNormalizer, UnicodeNormalizer (NFKC), QuoteNormalizer, NumberingNormalizer, CompositeNormalizer
- **2 Cleaners**: BoilerplateRemover (copyright, disclaimer, confidentiality), HeaderFooterStripper
- **Metadata Extractor**: Auto-extracts title (from markdown headings or filename), author (from "Author:" field or "By " prefix), specialty (from medical specialty keyword matching), tags (from tags field or filename)
- **4 Chunking Strategies**: FixedSizeChunker (configurable size + overlap), ParagraphChunker (paragraph-aware), HeadingAwareChunker (preserves document hierarchy), SlidingWindowChunker (word-level sliding window)
- **Validator**: Format validation, size enforcement (configurable max MB), UTF-8 encoding check, content quality check (minimum length, binary detection)
- **StorageProvider ABC + LocalFileStorage**: CRUD operations for document JSON files, temp-directory safe
- **KnowledgeCatalog**: JSON-backed registry with add/update/get/list/remove/count operations
- **ProcessingPipeline**: 10 sequential stages (import → parse → normalize → clean → metadata → validate → chunk → version → store → catalog), all skippable via config
- **KnowledgeService**: Facade with `import_document`, `get_document`, `list_documents`, `delete_document`, `get_document_versions`
- **DI**: `get_knowledge_service()` / `set_knowledge_service()` / `reset_knowledge_service()` — follows same singleton pattern as cache & ratelimit
- **6 REST Endpoints**: `POST /ai/knowledge/import`, `GET /ai/knowledge/documents`, `GET /ai/knowledge/documents/{id}`, `DELETE /ai/knowledge/documents/{id}`, `GET /ai/knowledge/documents/{id}/versions`, `GET /ai/knowledge/stats`
- **Configuration**: `KNOWLEDGE_ENABLED`, `KNOWLEDGE_STORAGE_PATH`, `KNOWLEDGE_CATALOG_PATH`, `KNOWLEDGE_MAX_FILE_SIZE_MB`, `KNOWLEDGE_DEFAULT_CHUNK_SIZE`, `KNOWLEDGE_DEFAULT_CHUNK_OVERLAP` — all in `AISettings`
- **No Database Models**: All storage is file-based JSON on local filesystem
- **71 tests**: exceptions, schemas, utils, loaders, parsers, normalizers, cleaners, metadata, chunkers, validators, storage, catalog, pipeline, service, DI, API
- **No External Dependencies**: PDF/DOCX loaders use try/except fallbacks, all loaders work without optional libraries

### Enterprise Embedding Platform
- **Embedding Provider Abstraction**: `EmbeddingProvider` ABC with `MockEmbeddingProvider` (deterministic, normalized, configurable dimension for testing)
- **Embedding Pipeline**: `DefaultEmbeddingPipeline` — 6 stages (validate chunk → check cache → embed → validate vector → version → store vector + record)
- **Embedding Cache**: `MemoryEmbeddingCache` — thread-safe, content-hash keyed, hit/miss tracking, pattern invalidation
- **Embedding Versioning**: `InMemoryVersionManager` — per provider/model version tracking, active version, deprecation, history
- **Embedding Validation**: `DefaultEmbeddingValidator` — chunk emptiness/length, vector dimension, zero-vector, checksum validation
- **Embedding Storage**: `LocalEmbeddingStorage` — JSON-file based with separate records/vectors directories, CRUD, filtered listing
- **Batch Processing**: `BatchProcessor` — configurable batch-size, parallel chunk processing, per-chunk retry, progress tracking
- **Embedding Service**: `EmbeddingService` — facade with generate (single), generate_batch, get, list, delete, rebuild (cache-bypass), get_providers
- **DI**: `get_embedding_service()` / `set_embedding_service()` / `reset_embedding_service()` — follows same singleton pattern as cache, ratelimit, and knowledge
- **6 REST Endpoints**: `POST /ai/embeddings/generate`, `POST /ai/embeddings/generate-all`, `GET /ai/embeddings`, `GET /ai/embeddings/{id}`, `POST /ai/embeddings/rebuild`, `DELETE /ai/embeddings/{id}`, `GET /ai/embeddings/providers`
- **Configuration**: 11 embedding settings in AISettings (`EMBEDDING_ENABLED`, `EMBEDDING_DEFAULT_PROVIDER`, `EMBEDDING_DEFAULT_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_BATCH_SIZE`, `EMBEDDING_STORAGE_PATH`, etc.)
- **No Database Models**: All storage is file-based JSON on local filesystem
- **59 tests**: exceptions, schemas, utils, provider, validators, cache, versioning, pipeline, storage, batch, service, DI, API
- **No External Dependencies**: MockEmbeddingProvider requires no live embedding model; future providers are plug-in through ABC
- **No Retrieval, No RAG, No Chat**: This sprint is pure embedding infrastructure

### Medical Intelligence Platform (Volume 1)
- **10-stage Medical Pipeline**: intent detection → query rewrite → context optimization → prompt building → Gateway generation → citation building → reasoning → confidence scoring → safety validation → response building
- **IntentDetector**: Rule-based detection of 10 intent types, 20 medical specialties, 5 urgency levels
- **QueryRewriter**: 30+ medical abbreviation expansion, intent-specific query expansion, specialty context injection
- **CitationEngine**: Structured CitationEntry with source tracking, relevance scores, evidence text
- **ConfidenceEngine**: Multi-dimensional scoring (retrieval, evidence, generation, citation coverage)
- **SafetyValidator**: Pattern-based detection for unsafe advice, hallucination, contradiction
- **MedicalReasoner**: Chain-of-thought, differential considerations, evidence summary
- **ResponseBuilder**: Structured MedicalResponse assembly with citations and safety warnings
- **MedicalPipeline**: 10-stage orchestration consuming GatewayPipeline + RetrievalService
- **MedicalService**: Facade with `query()` and `search()`
- **DI**: `get_medical_service()` / `set_medical_service()` / `reset_medical_service()` — singleton pattern
- **2 REST Endpoints**: `POST /ai/medical/query`, `POST /ai/medical/search`
- **58 tests**

### Medical Query Understanding Platform (Volume 2)
- **QueryUnderstandingEngine**: Upstream NLU engine that transforms unstructured questions into structured metadata BEFORE retrieval/LLM
- **9 submodules**: intent, rewrite, entities, specialty, urgency, audience, language, context, taxonomy
- **Intent Detection**: 15 categories (symptom_inquiry, disease_information, medication_information, prescription_explanation, lab_report_interpretation, medical_record_explanation, appointment_inquiry, preventive_care, emergency, mental_health, lifestyle_guidance, nutrition, vaccination, follow_up, administrative) with confidence-ranked candidates
- **Clinical Specialty Classification**: 12 specialties with ranked confidence, matched terms, multi-specialty support
- **Medical Entity Recognition**: 13 entity types (symptom, disease, medication, procedure, lab_test, vital_sign, anatomy, allergy, dosage, time_expression, age_reference, chronic_condition, pregnancy_status) via regex patterns
- **Urgency Classification**: 4 levels (emergency, urgent, routine, informational) with advisory disclaimer
- **Audience Classification**: 6 types (patient, doctor, nurse, caregiver, administrator, unknown)
- **Language Detection**: language, abbreviations, acronyms, informal phrasing, typos, normalization
- **Query Rewriting**: abbreviation expansion (35+), preserves original query, normalized output
- **Conversation Awareness**: Integrates with existing Memory Platform (InMemoryMemoryManager) via ContextResolver
- **Medical Taxonomy Abstraction**: Interface for future ICD-10/ICD-11/SNOMED CT/LOINC/RxNorm/ATC integration
- **DI**: `get_query_understanding_engine()` / `set_query_understanding_engine()` / `reset_query_understanding_engine()` — singleton pattern
- **6 REST Endpoints**: `POST /ai/medical/analyze`, `POST /ai/medical/intent`, `POST /ai/medical/entities`, `POST /ai/medical/rewrite`, `GET /ai/medical/specialties`, `GET /ai/medical/intents`
- **Business Rules**: Original query preserved, rewritten queries internal, deterministic classification, multiple intent candidates with confidence scores
- **Validation**: Empty queries rejected, max 10000 chars, structured validation errors
- **No LLM calls** — pure rule-based NLU; no medical answers generated
- **77 tests** (exceptions, schemas, classifiers, engine, DI, API auth/RBAC)
- **No downstream component performs these responsibilities again**

### Enterprise Clinical Safety Platform
- **8 rule-based engines** — no LLM calls, deterministic, auditable
- **Hallucination Detection**: 7 hallucination types (FABRICATED_MEDICATION, FABRICATED_DISEASE, FABRICATED_CITATION, FABRICATED_GUIDELINE, FABRICATED_STATISTIC, FABRICATED_RECOMMENDATION, UNSUPPORTED_CLAIM) using built-in medication/disease lists and regex patterns
- **Unsupported Claim Detection**: 4 support levels (FULLY_SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTORY) with evidence matching
- **Clinical Risk Classification**: Weighted scoring (hallucination 30%, unsupported 25%, topic sensitivity 20%, emergency 25%) → LOW/MODERATE/HIGH/CRITICAL
- **Emergency Detection**: 7 emergency types via regex (chest pain, stroke, severe bleeding, suicidal ideation, anaphylaxis, respiratory distress, loss of consciousness)
- **PHI Validation**: 10 PHI types (SSN, email, phone, Aadhaar, passport, credit card, MRN, insurance ID, DOB, name) with value masking
- **Medical Disclaimer Engine**: 7 built-in disclaimers (GENERAL_MEDICAL, EMERGENCY, MEDICATION, MENTAL_HEALTH, PREGNANCY, PEDIATRIC, CLINICAL_UNCERTAINTY), context-aware selection
- **Compliance Validation**: 7 checks (hallucination, unsupported, evidence threshold, disclaimer, prohibited terms, absolute guarantees, citation coverage)
- **Safety Approval Engine**: 4-level decision (APPROVED, APPROVED_WITH_WARNINGS, ESCALATE, REJECT) with deterministic business rules
- **ClinicalSafetyPipeline**: 8-stage pipeline orchestrating all engines
- **10 REST Endpoints**: `GET /ai/safety/health`, `POST /ai/safety/validate`, `POST /ai/safety/hallucination`, `POST /ai/safety/unsupported`, `POST /ai/safety/risk`, `POST /ai/safety/emergency`, `POST /ai/safety/phi`, `POST /ai/safety/disclaimer`, `POST /ai/safety/compliance`, `POST /ai/safety/approval`
- **Business Rules**: Hallucinated content never approved; emergencies bypass normal flow; risk classifications deterministic; approval decisions auditable
- **324 tests**, all passing

### Automated Testing
- 1,570 tests across 35+ test files (938 prior + 308 evidence + 324 clinical safety)
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
| `/ai` | POST /generate, POST/GET /prompts, GET /prompts/{name}, POST /conversations, DELETE /conversations/{id}, POST /safety/check, GET /provider | Authenticated (any role) |
| `/ai/knowledge` | POST /import, GET /documents, GET /documents/{id}, DELETE /documents/{id}, GET /documents/{id}/versions, GET /stats | Authenticated (any role) |
| `/ai/embeddings` | POST /generate, POST /generate-all, POST /batches, GET /, GET /{id}, POST /rebuild, POST /reindex, DELETE /{id}, GET /providers | Admin/Doctor for write; any role for read |
| `/ai/vector` | POST /search, POST /index, GET /stats, DELETE /{id}, DELETE /clear | Authenticated (any role) |
| `/ai/retrieval` | POST /search, POST /rag | Authenticated (any role) |
| `/ai/medical` | POST /query, POST /search, POST /analyze, POST /intent, POST /entities, POST /rewrite, GET /specialties, GET /intents | Authenticated (any role) |
| `/ai/evidence` | GET /health, POST /validate, POST /verify, POST /citations, POST /coverage, POST /conflicts, POST /confidence, POST /provenance, POST /explain, POST /pipeline | Authenticated (any role) |
| `/ai/safety` | GET /health, POST /validate, POST /hallucination, POST /unsupported, POST /risk, POST /emergency, POST /phi, POST /disclaimer, POST /compliance, POST /approval | Authenticated (any role) |
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

### Volume 7 — ✅ Complete (Enterprise API Protection)
- RateLimiter abstraction (MemoryRateLimiter, RedisRateLimiter)
- RateLimitMiddleware (FastAPI middleware, IP-based limits)
- Per-endpoint rate_limit() dependency factory
- Config-driven: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PROVIDER`, `RATE_LIMIT_DEFAULT`, etc.
- 35 tests, all 489 tests passing

### Sprint 4.1 — ✅ Complete (AI Platform Foundation)
- Provider abstraction: `LLMProvider` ABC + `OllamaProvider` + `OpenAIProvider` + `MockLLMProvider`
- Prompt Registry: `PromptManager` ABC + `PromptRegistry` with versioning, template variables, tag filtering
- Memory Layer: `MemoryManager` ABC + `InMemoryMemoryManager` with conversation CRUD, context window, token budgeting
- Safety Layer: `SafetyService` ABC + `DefaultSafetyService` with input validation, prompt injection detection (10 patterns), PHI detection (8 patterns), dangerous content detection
- AI Gateway: `GatewayService` ABC + `GatewayPipeline` orchestrating prompt → memory → provider → safety → formatter
- AI API endpoints (7): `/ai/generate`, `/ai/prompts`, `/ai/conversations`, `/ai/safety/check`, `/ai/provider`
- Token counter utility: estimate_tokens, truncate_messages
- AI-specific exceptions: 14 exception types
- Configuration: `AISettings` nested in `Settings.AI`, env-var configurable
- Dependency Injection: all AI components follow get/set/reset singleton pattern (overrideable in tests)
- Fully isolated `app/ai/` module — no cross-contamination with business logic
- 54 tests using `MockLLMProvider` (no live LLM required), all 543 tests passing

### Sprint 4.2 — ✅ Complete (Enterprise Knowledge Platform)
- 7 document loaders (TXT, MD, CSV, JSON, HTML, PDF, DOCX)
- 5 normalizers, 2 cleaners, metadata extractor
- 4 chunking strategies (fixed, paragraph, heading-aware, sliding window)
- Document validator (format, size, encoding, content quality)
- LocalFileStorage + KnowledgeCatalog (JSON-based, no DB models)
- ProcessingPipeline (10-stage sequential, all skippable)
- KnowledgeService facade + DI singletons
- 6 REST endpoints at `/ai/knowledge/`
- Configuration: 6 knowledge settings in AISettings
- 71 tests, all 673 tests passing

### Sprint 4.3 — ✅ Complete (Enterprise Embedding Platform)
- EmbeddingProvider ABC + MockEmbeddingProvider (deterministic, normalized, configurable 384-dim via MD5 seed)
- DefaultEmbeddingPipeline: 6-stage (validate chunk → validate provider → check cache → embed → validate vector → version → store)
- LocalEmbeddingStorage (JSON-based, separate records/vectors, no DB models)
- MemoryEmbeddingCache (content-hash keyed, hit/miss tracking, pattern invalidation)
- InMemoryVersionManager (per provider/model, active version, deprecation, rollback, knowledge_version linkage)
- DefaultEmbeddingValidator (chunk emptiness/length, vector dimension/zero-vector, checksum, provider availability, duplicate detection)
- BatchProcessor (configurable batch-size, parallel chunks, retries, progress tracking)
- EmbeddingService facade + DI singletons
- Pipeline tracks `processing_time_ms` per embedding in both vector and record schemas
- RBAC: Admin/Doctor for write operations, any authenticated for read
- 9 REST endpoints at `/ai/embeddings/` (including `/batches` and `/reindex`)
- Configuration: 11 embedding settings in AISettings
- No vector database, no retrieval, no RAG, no similarity search
- 78 tests, all 770 tests passing

### Sprint 4.4 — ✅ Complete (Enterprise Vector Platform)
- VectorStoreProvider ABC (add, add_batch, search, delete, delete_by_filter, count, clear)
- MemoryVectorStore (in-memory, cosine similarity, thread-safe, filter operators: $gt/$gte/$lt/$lte/$ne/$in/$and/$or)
- ChromaDBVectorStore (ChromaDB-backed, cosine distance → similarity, optional dep via try/except)
- VectorService facade (index_vector, index_batch, search_by_vector, delete, delete_by_filter, get_stats, clear)
- DI: get_vector_service() / set_vector_service() / reset_vector_service() singletons
- 5 REST endpoints at `/ai/vector/` (search, index, stats, delete, clear)
- Configuration: 6 vector settings in AISettings (VECTOR_ENABLED, VECTOR_DEFAULT_PROVIDER, etc.)
- No retrieval, no RAG, no chatbot integration — pure vector storage and similarity search
- 78 tests, all 751 tests passing

### Sprint 4.5 — ✅ Complete (Enterprise Retrieval Engine)
- **Reranker Abstraction**: `RerankerProvider` ABC with `NoOpReranker`, `MockReranker` (score-based), `TimeReranker` (recency-based)
- **Retrieval Pipeline**: `RetrievalPipeline` orchestrating embed query → vector search → chunk retrieval → filter → rerank
- **Retrieval Service**: `RetrievalService` facade with `search`, `retrieve`, `assemble_context`, `rag_generate`
- **RAG Generation**: Context assembly with token budgeting + truncation, GatewayPipeline integration for answer generation
- **Integration**: `EmbeddingService` (query embedding), `VectorService` (similarity search), `KnowledgeService` (chunk content via `get_chunk`), `GatewayPipeline` (LLM generation)
- **DI**: `get_retrieval_service()` / `set_retrieval_service()` / `reset_retrieval_service()` — follows same singleton pattern as cache, ratelimit, knowledge, vector
- **2 REST endpoints**: `POST /ai/retrieval/search` (semantic search), `POST /ai/retrieval/rag` (retrieval-augmented generation)
- **Configuration**: 6 retrieval settings in AISettings (`RETRIEVAL_ENABLED`, `RETRIEVAL_DEFAULT_TOP_K`, `RETRIEVAL_MAX_TOP_K`, `RETRIEVAL_DEFAULT_RERANKER`, `RETRIEVAL_MAX_CONTEXT_TOKENS`, `RETRIEVAL_ALLOW_RAG`)
- **Default RAG system message**: context injection, citation instructions, no-make-believe guardrail
- **No Medical RAG**: pure retrieval + RAG infrastructure, no medical domain tuning
- **33 tests**: exceptions, schemas, rerankers, service, pipeline, DI, API, knowledge integration

---

## Upcoming Roadmap *(Planned)*
- Sprint 4.7: AI Assistant (Doctor AI + Patient Health Companion)
- Clinical guideline rule engine
- Regulatory rule packs by country (HIPAA, GDPR, DPDP)
- ML-based hallucination detection
- Physician review workflows (human-in-the-loop approval)
- Volume 9: Production Deployment (Docker, PostgreSQL, Redis, Nginx)
- Volume 10: Enterprise Observability (Prometheus, OpenTelemetry, structured logging)
- Volume 11: Enterprise Performance Optimization (index review, N+1 detection)
- Volume 12: Enterprise Security Hardening (OWASP Top 10, PHI handling, encryption)
- Volume 13: Medical Ontology Integration (ICD-10, SNOMED CT, RxNorm, LOINC)
