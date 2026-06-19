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
        ├── Jobs Router → JobService (background task orchestration)
        │                       ↓
        ├── AI Router → AI Gateway → Prompt Builder → Memory → Provider → Safety → Formatter
        │                     ↓
        │               AI Platform (app/ai/)
        │                       ↓
        └── Embedding Router → EmbeddingService → Pipeline → Provider → Cache → Storage
                                ↓
                          Embedding Platform (app/ai/embeddings/)
                                ↓
                ┌── Vector Router → VectorService → VectorStoreProvider → Memory / ChromaDB
                │                     ↓
                │               Vector Platform (app/ai/vector/)
                │                     ↓
    ├── Retrieval Router → RetrievalService → RetrievalPipeline → RerankerProvider
    │                     ↓                                     ↓
    │               Retrieval Engine (app/ai/retrieval/)    VectorService + EmbeddingService
    │                                                           + KnowledgeService
    │                     ↓
     ├── Medical Router → MedicalService → MedicalPipeline → IntentDetector + QueryRewriter
     │                     ↓                                     + CitationEngine + ConfidenceEngine
     │               Medical Intelligence (app/ai/medical/)       + SafetyValidator + ResponseBuilder
     │                                                           + MedicalReasoner
     │                     ↓
     ├── Evidence Router → EvidenceService → EvidencePipeline → Verifier + Citation + Coverage
     │                     ↓                                     + Ranking + Conflict + Confidence
     │               Evidence Intelligence (app/ai/evidence/)     + Provenance + Explain
     │                     ↓
     ├── Safety Router → SafetyService → SafetyPipeline → Hallucination + Emergency + Unsupported
     │                     ↓                                     + Risk + PHI + Disclaimer
     │               Clinical Safety (app/ai/clinical_safety/)    + Compliance + Approval
Dependency Layer (app/api/deps.py) — Auth, role checks
       ↓
 Service Layer (app/services/) — Business logic, DB operations + AnalyticsService
       ↓        ↑
       └────────┴── Cache Layer (app/cache/) — CacheService, FeatureFlags
       ↓        ↑
       └────────┴── AI Platform (app/ai/) — GatewayService, PromptManager, MemoryManager, SafetyService
                         ↓
   Schema Layer (app/schemas/) — Pydantic request/response models
       ↓
   Model Layer (app/models/) — SQLAlchemy table definitions
       ↓
 Database Layer (app/database/) — Engine, session, Base
       ↓
      SQLite / PostgreSQL
```

The Cache Layer and AI Platform sit alongside the Service Layer as cross-cutting concerns. The AI Platform is fully isolated in `app/ai/` — business services never depend on it directly. The AI Gateway orchestrates the pipeline: prompt builder → memory injection → LLM provider call → safety check → response formatting. The Embedding Platform is isolated in `app/ai/embeddings/` and orchestrates: validate chunk → check cache → embedding provider → validate vector → version → store. The Vector Platform is isolated in `app/ai/vector/` and provides: vector storage, cosine similarity search, and metadata-filtered retrieval. The Retrieval Engine is in `app/ai/retrieval/` and orchestrates: embed query → vector search → chunk retrieval → rerank → return. The Medical Intelligence Platform is in `app/ai/medical/` and orchestrates: intent detection → query rewrite → retrieval → context optimization → prompt building → LLM generation (via Gateway) → citation building → reasoning → confidence scoring → safety validation → response building. All AI, Embedding, Vector, Retrieval, and Medical interactions pass through abstraction layers (interfaces in `app/ai/interfaces/`, `app/ai/embeddings/interfaces/`, `app/ai/vector/interfaces/`, `app/ai/retrieval/interfaces/`, and `app/ai/medical/interfaces/`). No router or service calls an LLM, embedding model, vector store, retrieval engine, or medical pipeline directly.

---

## Folder Structure

```
backend/
├── app/
│   ├── ai/               # AI Platform (fully isolated)
│   │   ├── api/          # Gateway endpoints (/ai/generate, /ai/prompts, etc.)
│   │   ├── config/       # AISettings (active provider, model, temperature, etc.)
│   │   ├── exceptions/   # AI-specific exceptions (ProviderError, SafetyError, etc.)
│   │   ├── gateway/      # GatewayPipeline (orchestrates prompt → memory → provider → safety)
│   │   ├── interfaces/   # ABCs: LLMProvider, PromptManager, MemoryManager, SafetyService, GatewayService
│   │   ├── knowledge/    # Knowledge Platform (loaders, parsers, normalizers, cleaners, chunkers, validators, storage, catalog, pipeline, service)
│   │   │   ├── api/          # Knowledge REST endpoints (/ai/knowledge/import, /ai/knowledge/documents, etc.)
│   │   │   ├── catalog/      # KnowledgeCatalog (JSON-backed document registry)
│   │   │   ├── chunkers/     # 4 chunking strategies (fixed, paragraph, heading-aware, sliding window)
│   │   │   ├── cleaners/     # BoilerplateRemover, HeaderFooterStripper
│   │   │   ├── exceptions/   # Knowledge-specific exceptions
│   │   │   ├── interfaces/   # ABCs: Loader, Parser, Normalizer, Cleaner, MetadataExtractor, Chunker, Validator, StorageProvider
│   │   │   ├── loaders/      # 7 document loaders (TXT, MD, CSV, JSON, HTML, PDF, DOCX)
│   │   │   ├── metadata/     # DefaultMetadataExtractor (title, author, specialty, tags)
│   │   │   ├── normalizers/  # Whitespace, Unicode, Quote, Numbering, Composite
│   │   │   ├── parsers/      # DocumentParser (text extraction, heading detection)
│   │   │   ├── pipelines/    # ProcessingPipeline (10-stage sequential pipeline)
│   │   │   ├── schemas/      # Pydantic schemas (KnowledgeDocument, DocumentChunk, etc.)
│   │   │   ├── services/     # KnowledgeService (facade) + deps (get/set/reset)
│   │   │   ├── storage/      # LocalFileStorage (JSON-based, StorageProvider ABC)
│   │   │   ├── utils/        # generate_document_id, compute_checksum
│   │   │   └── validators/   # DocumentValidator (format, size, encoding, content quality)
│   │   ├── embeddings/   # Embedding Platform (providers, pipeline, batch, cache, storage, validators, versioning)
│   │   │   ├── api/          # Embedding REST endpoints (/ai/embeddings/generate, /ai/embeddings, etc.)
│   │   │   ├── batch/        # BatchProcessor (configurable batch-size, parallel processing, retries)
│   │   │   ├── cache/        # MemoryEmbeddingCache (content-hash keyed, hit/miss tracking)
│   │   │   ├── deps/         # get/set/reset embedding service singletons
│   │   │   ├── exceptions/   # Embedding-specific exceptions
│   │   │   ├── interfaces/   # ABCs: EmbeddingProvider, EmbeddingPipeline, EmbeddingCache, EmbeddingValidator, EmbeddingVersionManager, EmbeddingStorage
│   │   │   ├── pipelines/    # DefaultEmbeddingPipeline (validate → cache → embed → validate → version → store)
│   │   │   ├── providers/    # MockEmbeddingProvider (deterministic, normalized, configurable dimension)
│   │   │   ├── schemas/      # Pydantic schemas (EmbeddingVector, EmbeddingRecord, EmbeddingBatch, etc.)
│   │   │   ├── services/     # EmbeddingService (facade) + deps (get/set/reset)
│   │   │   ├── storage/      # LocalEmbeddingStorage (JSON-based, separate records/vectors directories)
│   │   │   ├── utils/        # generate_embedding_id, compute_content_hash, compute_vector_checksum, normalize_vector
│   │   │   ├── validators/   # DefaultEmbeddingValidator (chunk, vector dimension, checksum)
│   │   │   └── versioning/   # InMemoryVersionManager (per provider/model, active version, deprecation)
│   │   ├── vector/       # Vector Platform (vector storage, similarity search)
│   │   │   ├── api/          # Vector REST endpoints (/ai/vector/search, /ai/vector/index, etc.)
│   │   │   ├── deps/         # get/set/reset vector service singletons
│   │   │   ├── exceptions/   # Vector-specific exceptions
│   │   │   ├── interfaces/   # ABC: VectorStoreProvider (add, add_batch, search, delete, delete_by_filter, count, clear)
│   │   │   ├── providers/    # MemoryVectorStore, ChromaDBVectorStore
│   │   │   ├── schemas/      # Pydantic schemas (SearchQuery, SearchResult, VectorStats, etc.)
│   │   │   ├── services/     # VectorService (facade) + deps (get/set/reset)
│   │   │   └── utils/        # cosine_similarity, l2_distance, dot_product, generate_vector_id
│   │   ├── retrieval/    # Retrieval Engine (query → embed → search → rerank → return)
│   │   │   ├── api/          # Retrieval REST endpoints (/ai/retrieval/search, /ai/retrieval/rag)
│   │   │   ├── deps/         # get/set/reset retrieval service singletons
│   │   │   ├── exceptions/   # Retrieval-specific exceptions
│   │   │   ├── interfaces/   # ABC: RerankerProvider
│   │   │   ├── pipelines/    # RetrievalPipeline (embed → search → retrieve → rerank → return)
│   │   │   ├── providers/    # (future: hybrid retrieval providers)
│   │   │   ├── rerankers/    # NoOpReranker, MockReranker, TimeReranker
│   │   │   ├── schemas/      # Pydantic schemas (RetrievalQuery, RetrievalResult, RetrievalResponse, RAGRequest, RAGResponse, etc.)
│   │   │   ├── services/     # RetrievalService (facade) + deps (get/set/reset)
│   │   │   └── utils/        # generate_query_id, timing_ms, compute_query_hash, estimate_tokens
│   │   ├── medical/      # Medical Intelligence Platform (Volume 1 + Volume 2)
│   │   │   ├── api/          # Medical REST endpoints (Volume 1: /ai/medical/query, /ai/medical/search)
│   │   │   │   └── query_api.py  # Volume 2: /ai/medical/analyze, /intent, /entities, /rewrite, /specialties, /intents
│   │   │   ├── audience/     # AudienceClassifier (patient, doctor, nurse, caregiver, admin) [V2]
│   │   │   ├── citations/    # CitationEngine (structured citations from DocumentChunks)
│   │   │   ├── confidence/   # ConfidenceEngine (multi-dimensional scoring)
│   │   │   ├── config/       # MedicalSettings (specialties, urgency, token budgets)
│   │   │   ├── context/      # ContextResolver (memory platform integration) [V2]
│   │   │   ├── deps/         # get/set/reset medical service singletons (V1 + V2)
│   │   │   ├── engine/       # QueryUnderstandingEngine (orchestrator for all V2 modules) [V2]
│   │   │   ├── entities/     # EntityExtractor (13 entity types, regex-based) [V2]
│   │   │   ├── exceptions/   # Medical-specific + QueryUnderstanding exceptions [V1+V2]
│   │   │   ├── intent/       # Volume 1: IntentDetector (single-file, backward-compat)
│   │   │   │   ├── classifiers.py  # Volume 2: RuleBasedIntentClassifier (15 categories)
│   │   │   │   ├── interfaces.py   # Volume 2: ABCs
│   │   │   │   ├── schemas.py      # Volume 2: IntentCategory definitions
│   │   │   │   ├── services.py     # Volume 2: IntentDetectorService
│   │   │   │   ├── validators.py   # Volume 2: validation
│   │   │   │   ├── utils.py        # Volume 2: keyword extraction
│   │   │   │   └── deps.py         # Volume 2: DI
│   │   │   ├── interfaces/   # ABCs: 9 Volume 1 interfaces
│   │   │   ├── language/     # LanguageDetector (abbreviations, typos, normalization) [V2]
│   │   │   ├── pipelines/    # MedicalPipeline (10-stage orchestration)
│   │   │   ├── reasoning/    # MedicalReasoner (chain-of-thought, differentials)
│   │   │   ├── responses/    # ResponseBuilder (structured MedicalResponse assembly)
│   │   │   ├── rewrite/      # QueryRewriter (35+ abbreviation expansions) [V2]
│   │   │   ├── rewriters/    # Volume 1 QueryRewriter (backward-compat)
│   │   │   ├── safety/       # (shared with app/ai/safety/ conceptually)
│   │   │   ├── schemas/      # Pydantic schemas [V1+V2]
│   │   │   ├── services/     # MedicalService (facade) + deps [V1]
│   │   │   ├── specialty/    # SpecialtyClassifier (12 specialties) [V2]
│   │   │   ├── taxonomy/     # MedicalTaxonomyService (ICD-10/SNOMED/LOINC abstraction) [V2]
│   │   │   ├── urgency/      # UrgencyClassifier (4 levels) [V2]
│   │   │   ├── utils/        # (shared utilities)
│   │   │   └── validators/   # SafetyValidator (V1) + query validators (V2)
│   │   ├── memory/       # InMemoryMemoryManager (conversation CRUD, context window, token budget)
│   │   ├── models/       # Pydantic schemas (GatewayRequest, MessageSchema, etc.)
│   │   ├── prompts/      # PromptRegistry (templates, versioning, variables, tags)
│   │   ├── providers/    # LLMProvider ABC + OllamaProvider + OpenAIProvider + MockLLMProvider
│   │   ├── safety/       # DefaultSafetyService (input validation, prompt injection, PHI detection) [Sprint 4.1]
│   │   ├── clinical_safety/ # Clinical Safety Platform (hallucination, risk, emergency, PHI, compliance, approval) [Sprint 4.6.4.3]
│   │   │   ├── __init__.py
│   │   │   ├── api/          # Clinical Safety REST endpoints (/ai/safety/validate, /hallucination, etc.)
│   │   │   ├── config/       # ClinicalSafetyConfig (thresholds, flags, settings)
│   │   │   ├── deps.py       # get/set/reset DI for all 8 engines + pipeline + service
│   │   │   ├── exceptions.py # ClinicalSafetyError hierarchy (12 exception types)
│   │   │   ├── interfaces/   # 8 ABCs: HallucinationDetector, UnsupportedClaimDetector, ClinicalRiskEngine, EmergencyDetector, PHIValidator, DisclaimerEngine, ComplianceValidator, SafetyApprovalEngine
│   │   │   ├── pipelines/    # ClinicalSafetyPipeline (8-stage: hallucination → emergency → unsupported → risk → PHI → disclaimer → compliance → approval)
│   │   │   ├── schemas.py    # 18 Pydantic schemas + 7 enums
│   │   │   └── services/     # 8 engine implementations + ClinicalSafetyService facade
│   │   ├── services/     # Concrete implementations (future: LLMService, PromptService)
│   │   └── utils/        # Token counter (estimate_tokens, truncate_messages)
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
│   ├── test_ai_platform.py # 54 AI Platform tests
│   ├── test_smoke.py     # 12 smoke tests
│   ├── test_search.py    # 72 search tests
│   ├── test_dashboard.py # 50 dashboard tests
│   ├── test_analytics.py # 50 analytics tests
│   ├── test_cache.py     # 53 cache tests
│   ├── test_knowledge_platform.py # 71 Knowledge Platform tests
│   ├── test_embedding_platform.py # 78 Embedding Platform tests
│   ├── test_vector_platform.py # 78 Vector Platform tests
│   ├── test_retrieval_engine.py # 33 Retrieval Engine tests
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

- Models never import from services, schemas, cache, api, or ai
- Services import from models, schemas, and cache (CacheService for caching)
- API imports from services, schemas, models, deps, and ai/api (gateway router)
- Cache layer is a cross-cutting concern: services import CacheService directly
- AI Platform is a fully isolated module: no business service imports from it
- AI router depends on `app/ai/gateway/deps.py` for gateway, prompt, memory, safety injectors
- Core modules (config, security, logging) are standalone
- Tests import from app, override `get_db` to isolate database
- AI tests override `get_db` and use `MockLLMProvider` (no live LLM)
- Knowledge tests use temp directories for storage, no external dependencies
- Knowledge DI follows same get/set/reset pattern as cache & ratelimit
- Embedding Platform is fully isolated in `app/ai/embeddings/` — no coupling with retrieval, RAG, or chat
- Embedding DI follows same get/set/reset pattern as cache, ratelimit, and knowledge
- Embedding tests use `MockEmbeddingProvider` (no live embedding model required), temp directories for storage
- Retrieval Engine is in `app/ai/retrieval/` — integrates EmbeddingService, VectorService, KnowledgeService, GatewayPipeline
- Retrieval DI follows same get/set/reset pattern as cache, ratelimit, knowledge, embeddings, and vector
- Retrieval tests mock all 3 dependent services (embedding, vector, knowledge) and use MockReranker
- Medical Intelligence Platform (Volume 1) is in `app/ai/medical/` — consumed by future AI Assistant (Sprint 4.7); no other module depends on it
- Medical Query Understanding Platform (Volume 2) is in `app/ai/medical/` — sits upstream of Volume 1, provides structured metadata for retrieval and generation
- Volume 2 uses the existing Memory Platform (`app/ai/memory/`) for conversation awareness — no duplicate memory management
- Medical DI (Volume 1) follows same get/set/reset pattern as cache, ratelimit, knowledge, embeddings, vector, and retrieval
- Query Understanding DI (Volume 2) follows same get/set/reset singleton pattern via `engine/deps.py`
- Medical Pipeline imports GatewayPipeline (Sprint 4.1) and RetrievalService (Sprint 4.5) — no circular dependencies
- Volume 2 is pure rule-based NLU — no LLM calls, no retrieval, no medical answers generated
- Volume 1 Volume 2 tests mock GatewayPipeline and RetrievalService; no live LLM or retrieval required
- Volume 2 tests use no mocks for rule-based classifiers — pure deterministic logic
- Evidence Intelligence Platform is in `app/ai/evidence/` — consumes VerificationResult from Knowledge Platform, produces ServiceResult for downstream safety validation
- Evidence DI follows same get/set/reset singleton pattern as cache, ratelimit, knowledge, embeddings, vector, retrieval, and medical
- Clinical Safety Platform is in `app/ai/clinical_safety/` — sits downstream of Evidence and upstream of Final Response API
- Clinical Safety DI follows same get/set/reset singleton pattern as all other AI modules
- Clinical Safety depends only on its own interfaces and schemas — no coupling with retrieval, evidence, or gateway modules
- All safety engines are pure rule-based (no LLM calls) for deterministic, auditable results

---

## AI Platform Architecture

```
Client → POST /ai/generate
              ↓
       AI Router (app/ai/api/gateway.py)
              ↓
       GatewayService (app/ai/gateway/pipeline.py)
              ↓
       ┌──────────────────────────────────────┐
       │         GatewayPipeline              │
       │                                      │
       │  1. Build messages (from request,    │
       │     prompt template, or conversation)│
       │  2. Safety check input               │
       │  3. Inject into memory (if conv_id)  │
       │  4. Call LLM Provider (generate)     │
       │  5. Safety check output              │
       │  6. Store in memory (if conv_id)     │
       │  7. Format response                  │
       └──────────────────────────────────────┘
              ↓
       LLMProvider (app/ai/providers/)
          ├── OllamaProvider (local)
          ├── OpenAIProvider (cloud)
          └── MockLLMProvider (tests)

  Prompt Registry        Memory Manager         Safety Service
  (app/ai/prompts/)      (app/ai/memory/)       (app/ai/safety/)
  ├── Register prompts   ├── Conversations      ├── Input validation
  ├── Versioning         ├── Messages           ├── Prompt injection detection
  ├── Template variables ├── Context window     ├── PHI detection (SSN, email, phone)
  ├── Tag filtering      ├── Token budgeting    ├── Output validation
  └── Auto-extraction    └── Truncation         └── Dangerous content detection
```

## Embedding Platform Architecture

```
Client → POST /ai/embeddings/generate
               ↓
       Embedding Router (app/ai/embeddings/api/)
               ↓
       EmbeddingService (app/ai/embeddings/services/)
               ↓
       ┌──────────────────────────────────────┐
       │       DefaultEmbeddingPipeline       │
       │                                      │
       │  1. Validate chunk (not empty/size)  │
       │  2. Check cache (content-hash)       │
       │  3. Call Embedding Provider          │
       │  4. Validate vector (dimension/zeros)│
       │  5. Manage version (active/increment)│
       │  6. Store vector + record (JSON)     │
       └──────────────────────────────────────┘
               ↓
       EmbeddingProvider (app/ai/embeddings/providers/)
          ├── MockEmbeddingProvider (tests, deterministic)
          └── Future: Ollama, BGE, OpenAI, Cohere, etc.
```

```
   Batch Processing Flow:

   Knowledge Chunks
        ↓
   BatchProcessor (configurable batch_size)
        ↓
   ┌─────────────────────────────┐
   │  Parallel chunk processing  │
   │  with per-chunk retry       │
   │  and progress tracking      │
   └─────────────────────────────┘
        ↓
   EmbeddingBatch {total, processed, failed}
```

```
Vector Platform Data Flow:

  POST /ai/vector/index
       ↓
  VectorService.index_batch() ← reads from EmbeddingStorage
       ↓
  VectorStoreProvider.add_batch() → Memory / ChromaDB
       ↓
  {indexed_count, skipped_count, errors}
```

```
  POST /ai/vector/search {query_vector, top_k, filters}
       ↓
  VectorService.search_by_vector()
       ↓
  VectorStoreProvider.search() → cosine similarity scoring
       ↓
  SearchResponse {results[{embedding_id, chunk_id, score, metadata, vector}], total, query_time_ms}
```

```
  Similarity Search:
  query_vector → cosine_similarity → scored items → sort desc → top_k → SearchResult[]
  Filters: exact match, list, range ($gt/$gte/$lt/$lte), $ne, $in, $and, $or
```

## Retrieval Engine Architecture

```
Client → POST /ai/retrieval/search / POST /ai/retrieval/rag
               ↓
       Retrieval Router (app/ai/retrieval/api/)
               ↓
       RetrievalService (app/ai/retrieval/services/)
               ↓
       ┌─────────────────────────────────────────┐
       │          RetrievalPipeline              │
       │                                         │
       │  1. Embed query via EmbeddingService    │
       │  2. Search via VectorService            │
       │  3. Get chunk content via KnowledgeSvc  │
       │  4. Filter by min_score                 │
       │  5. Rerank via RerankerProvider         │
       │  6. Return results                      │
       └─────────────────────────────────────────┘
               ↓
        RerankerProvider (app/ai/retrieval/rerankers/)
           ├── NoOpReranker (pass-through)
           ├── MockReranker (score-based)
           └── TimeReranker (recency-based)
```

```
  RAG Flow:

  POST /ai/retrieval/rag {query, top_k, filters}
       ↓
  RetrievalService.rag_generate()
       ↓
  ┌─────────────────────────────────────────┐
  │  1. Retrieve chunks (embed + search)    │
  │  2. Assemble context with token budget  │
  │  3. Call GatewayPipeline.execute()      │
  │     → system: RAG system message        │
  │     → user: query                       │
  │  4. Return {answer, sources, timing}    │
  └─────────────────────────────────────────┘
```

## Medical Query Understanding Architecture (Volume 2)

```
Client → POST /ai/medical/analyze / POST /ai/medical/intent / etc.
               ↓
        Medical Query Router (app/ai/medical/api/query_api.py)
               ↓
        QueryUnderstandingEngine (app/ai/medical/engine/)
               ↓
        ┌──────────────────────────────────────────────────┐
        │          QueryUnderstandingEngine                │
        │                                                  │
        │  1. Intent Detection → IntentResult              │
        │     (15 categories with confidence candidates)   │
        │  2. Entity Recognition → EntityResult            │
        │     (13 entity types via regex patterns)         │
        │  3. Specialty Classification → SpecialtyResult   │
        │     (12 specialties, multi-specialty rankings)   │
        │  4. Urgency Classification → UrgencyResult       │
        │     (4 levels: emergency → informational)        │
        │  5. Audience Classification → AudienceResult     │
        │     (6 types: patient → administrator)           │
        │  6. Language Detection → LanguageInfo             │
        │     (abbreviations, acronyms, typos, informal)   │
        │  7. Context Resolution (memory integration)      │
        │  8. Query Rewriting → RewriteResult              │
        │     (abbreviation expansion, normalization)      │
        └──────────────────────────────────────────────────┘
               ↓
        Pure rule-based NLU — no LLM calls, no retrieval
               ↓
        Downstream: Medical Intelligence Pipeline (Volume 1)
```

### Volume 2 Submodule Structure

```
app/ai/medical/
├── intent/         → IntentDetectorService + RuleBasedIntentClassifier (15 categories)
├── rewrite/        → QueryRewriter (35+ abbreviation expansions)
├── entities/       → EntityExtractor (13 entity types, regex-based)
├── specialty/      → SpecialtyClassifier (12 clinical specialties)
├── urgency/        → UrgencyClassifier (4 urgency levels)
├── audience/       → AudienceClassifier (6 audience types)
├── language/       → LanguageDetector (abbreviations, typos, informal phrasing)
├── context/        → ContextResolver (memory platform integration)
├── taxonomy/       → MedicalTaxonomyService (future ICD-10/SNOMED CT/LOINC interface)
├── engine/         → QueryUnderstandingEngine (orchestrator)
├── api/query_api.py → 6 REST endpoints
├── deps/           → get/set/reset singleton DI
└── exceptions/query_exceptions.py → 10 exception types
```

### Pipeline Data Flow

```
User Query (original preserved)
    ↓
QueryUnderstandingEngine.analyze()
    ↓
├── IntentDetectorService.detect() → confidence-ranked candidates
├── EntityExtractor.extract() → structured entity list with types
├── SpecialtyClassifier.classify() → ranked specialty candidates
├── UrgencyClassifier.classify() → level + indicators + disclaimer
├── AudienceClassifier.classify() → audience type + confidence
├── LanguageDetector.detect() → language info + normalization
├── ContextResolver.resolve() → conversation history (if conv_id)
└── QueryRewriter.rewrite() → expanded, normalized query (internal only)
    ↓
QueryUnderstandingResult {original_query, intent, entities, specialty,
                         urgency, audience, language, rewrite, context}
```

## Medical Intelligence Platform Architecture (Volume 1)

```
Client → POST /ai/medical/query / POST /ai/medical/search
               ↓
        Medical Router (app/ai/medical/api/)
               ↓
        MedicalService (app/ai/medical/services/)
               ↓
        ┌──────────────────────────────────────────────────┐
        │              MedicalPipeline                     │
        │                                                  │
        │  1. Intent Detection → MedicalIntent             │
        │  2. Query Rewrite → QueryRewrite                 │
        │  3. Context Optimization → MedicalContext        │
        │  4. Prompt Building → system + user messages     │
        │  5. GatewayPipeline.execute() → LLM generation   │
        │  6. Citation Building → list[CitationEntry]      │
        │  7. Reasoning → MedicalReasoning                 │
        │  8. Confidence Scoring → ConfidenceScore         │
        │  9. Safety Validation → SafetyCheckResult        │
        │ 10. Response Building → MedicalResponse          │
        └──────────────────────────────────────────────────┘
               ↓
        Retrieval Engine (Sprint 4.5)  ← for all document retrieval
               ↓
        GatewayPipeline (Sprint 4.1)   ← for LLM generation
```

### Volume 1 Pipeline Data Flow

```
MedicalQuery
    ↓
IntentDetector.detect(query) → MedicalIntent {intent_type, specialty, urgency}
    ↓
QueryRewriter.rewrite(query, intent) → QueryRewrite {rewritten_query, expansions}
    ↓
RetrievalService.search(rewritten_query) → results + context
    ↓
ContextOptimizer.optimize(context, intent) → MedicalContext {context, token_count}
    ↓
MedicalPromptBuilder.build(query, context, intent) → {system_message, prompt}
    ↓
GatewayPipeline.execute({system, user}) → generated answer
    ↓
CitationEngine.build_citations(results) → list[CitationEntry]
    ↓
MedicalReasoner.reason(query, context, answer, intent) → MedicalReasoning
    ↓
ConfidenceEngine.score(query, answer, citations, intent) → ConfidenceScore
    ↓
SafetyValidator.validate(query, answer, citations, intent) → SafetyCheckResult
    ↓
ResponseBuilder.build(answer, intent, reasoning, citations, confidence, safety) → MedicalResponse
```

### Consumer Architecture

The Medical Intelligence Platform is consumed by:
- Future Doctor AI Assistant (Sprint 4.7)
- Future Patient Health Companion (Sprint 4.7)
- Future Voice AI interface

It consumes:
- QueryUnderstandingEngine (Volume 2) for query analysis
- Retrieval Engine (Sprint 4.5) for all knowledge retrieval
- GatewayPipeline (Sprint 4.1) for all LLM generation
- No downstream platform consumes the Medical Intelligence Platform directly

## Background Jobs *(Planned)*

- Celery + Redis for reminders and notifications

## Communication Layer *(Planned)*

- WhatsApp Business API for patient notifications

## Frontend *(Planned)*

- Doctor Dashboard → Next.js
- Patient Interface → WhatsApp
