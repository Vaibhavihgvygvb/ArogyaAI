# CURRENT_TASK.md

## Sprint Status

Sprint 4.1 ✅ **Complete** — AI Platform Foundation
Sprint 4.2 ✅ **Complete** — Enterprise Knowledge Platform
Sprint 4.3 ✅ **Complete** — Enterprise Embedding Platform
Sprint 4.4 ✅ **Complete** — Enterprise Vector Platform

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

### Sprint 3.8.4 — Enterprise Analytics APIs
- Analytics schemas: `PlatformAnalyticsResponse`, `DoctorAnalyticsResponse`, `PatientAnalyticsResponse`, `SystemAnalyticsResponse`, `AnalyticsSummaryResponse`
- Shared types: `EntityCount`, `ActivityTrend`, `GrowthMetric`, `SummaryCard`
- `AnalyticsService` — 5 public methods (`get_platform_analytics`, `get_doctor_analytics`, `get_patient_analytics`, `get_system_analytics`, `get_analytics_summary`)
- 12+ private helper methods
- 5 REST endpoints: `GET /analytics/platform`, `GET /analytics/doctor`, `GET /analytics/patient`, `GET /analytics/system`, `GET /analytics/summary`
- Single-query GROUP BY patterns for time-series trends (daily/weekly/monthly)
- Growth metrics with percentage calculation (30-day lookback)
- Appointment utilization rate (completed/total)
- Most-active-doctor ranking by appointment count
- Date-range filtering via `date_from`/`date_to` query params on all endpoints
- RBAC: Admin→all, Doctor→own, Patient→own
- 50 tests covering auth, RBAC, counts, aggregations, date filters, edge cases, response shape

### Sprint 3.8.5 — Enterprise Background Jobs & Task Orchestration
- JobStatus and JobType enums (`app/models/enums.py`)
- Job model (`app/models/job.py`) with SQLAlchemy 2.0 (Mapped, mapped_column, indexes on job_type, status, scheduled_at)
- Alembic migration `2d5dc9f0cccb` (add_jobs_table)
- Job schemas (`app/schemas/job.py`): `JobCreate`, `JobResponse`, `JobUpdate`, `JobRetryRequest`, `JobListResponse`, `JobHealthResponse`
- Job abstraction layer (`app/jobs/base.py`): `JobDefinition`, `JobResult`, `WorkerBase`, `SchedulerProvider` abstract classes
- `JobRegistry` (`app/jobs/registry.py`): centralized job_type → handler mapping
- `APSchedulerProvider` (`app/jobs/scheduler.py`): dev scheduler singleton with start/shutdown
- `InProcessWorker` (`app/jobs/workers/in_process_worker.py`): synchronous task executor
- 10 representative health task handlers registered via registry (`app/jobs/tasks/health_tasks.py`)
- `JobService` (`app/services/job_service.py`): 9 static methods (submit, list, get, update, delete, retry, cancel, health, status update)
- 6 REST endpoints: `POST /jobs`, `GET /jobs`, `GET /jobs/health`, `GET /jobs/{id}`, `DELETE /jobs/{id}`, `POST /jobs/{id}/retry`, `POST /jobs/{id}/cancel` — all Admin-only
- Route ordering fix: `/jobs/health` declared before `/{job_id}` to prevent path-parameter capture
- Lifespan migration: replaced deprecated `@app.on_event("startup")` with FastAPI `lifespan` context manager
- 42 comprehensive tests (auth, RBAC, creation, listing, filtering, retrieval, retry, cancel, delete, health, edge cases, response shape)

### Volume 6 — Enterprise Cache Platform
- `CacheProvider` abstract base (`app/cache/base.py`): `CacheEntry`, `CacheStats`, `TTL` constants
- `MemoryCacheProvider` (`app/cache/providers/memory.py`): thread-safe in-memory dict with TTL expiry, pattern-based clear, hit/miss/eviction tracking
- `RedisCacheProvider` (`app/cache/providers/redis.py`): Redis-backed with SCAN-based pattern clear, pipeline operations, JSON serialization
- `CacheService` (`app/cache/service.py`): static methods — `build_key`, `get`, `set`, `get_or_set`, `invalidate_key`, `invalidate_namespace`, `clear_all`, `get_stats`, `get_many`
- Key naming convention: `{redis_prefix}:v1:{namespace}:{parts}`
- `FeatureFlags` (`app/cache/feature_flags.py`): `is_enabled`, `enable`, `disable`, `clear_all_flags` via cache
- DashboardService cache: all 3 methods (5-min TTL)
- AnalyticsService cache: all 5 methods (5-min TTL)
- SearchService cache: `global_search` (1-min TTL)
- NotificationService cache: `get_unread_count` (1-min TTL) + invalidation on mutations
- MedicineService cache: `get_medicine` / `list_medicines` / `search_medicines` (1-hour TTL) + namespace invalidation on mutations
- Cache settings: `CACHE_PROVIDER`, `REDIS_URL`, `REDIS_PREFIX`, 6 TTL settings
- 53 tests (provider, service, feature flags, integration, benchmarks)

### Volume 7 — Enterprise API Protection
- `RateLimiter` abstract base (`app/ratelimit/base.py`): `RateLimitResult`, `RateLimitRule`, `RateLimitScope`
- `MemoryRateLimiter` (`app/ratelimit/providers/memory.py`): sliding-window log using deque, thread-safe, TTL-based expiry
- `RedisRateLimiter` (`app/ratelimit/providers/redis.py`): Redis-backed sliding window using sorted sets (ZREMRANGEBYSCORE + ZADD + ZCARD)
- `get_rate_limiter()` / `set_rate_limiter()` / `reset_rate_limiter()` singletons (`app/ratelimit/deps.py`) — overrideable for tests
- `RateLimitMiddleware` (`app/ratelimit/middleware.py`): FastAPI `BaseHTTPMiddleware` applying IP-based limits to all endpoints
- Public endpoint overrides: `/auth/login` (5/minute), `/auth/register` (3/hour)
- `rate_limit()` dependency factory (`app/ratelimit/deps.py`) for per-endpoint user-specific rate limits
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- 429 JSON responses with `retry_after_seconds` detail
- Rate limit settings in `app/core/config.py`: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PROVIDER`, `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_AUTHENTICATED`, `RATE_LIMIT_LOGIN_MAX`, `RATE_LIMIT_REGISTER_MAX`, `RATE_LIMIT_BURST_MULTIPLIER`
- 35 tests (rule/result models, memory limiter, sliding window, login protection, 429 responses, edge cases, concurrent access)

### Sprint 4.1 — Complete (AI Platform Foundation)
- Provider abstraction layer: `LLMProvider` ABC with `OllamaProvider`, `OpenAIProvider`, `MockLLMProvider`
- Provider DI: `get_llm_provider()` / `set_llm_provider()` / `reset_llm_provider()` (overrideable for tests)
- Prompt Registry: `PromptManager` ABC + `PromptRegistry` with versioning, template variables, auto-extraction, tag filtering
- Memory Layer: `MemoryManager` ABC + `InMemoryMemoryManager` with conversation CRUD, message management, context window truncation, token budgeting
- Safety Layer: `SafetyService` ABC + `DefaultSafetyService` with input validation, prompt injection detection (10 patterns), PHI detection (8 patterns: SSN, email, phone, aadhaar, passport, credit card), dangerous content detection (suicide, self-harm, weapons), configurable via `SAFETY_ENABLED`
- AI Gateway: `GatewayService` ABC + `GatewayPipeline` orchestrating prompt builder → memory → provider → safety → formatter; supports streaming and non-streaming
- Configuration: `AISettings` (20+ settings) nested in `Settings.AI`; all configurable via env vars / .env
- AI API endpoints (7): `POST /ai/generate`, `POST /ai/prompts`, `GET /ai/prompts`, `GET /ai/prompts/{name}`, `POST /ai/conversations`, `DELETE /ai/conversations/{id}`, `POST /ai/safety/check`, `GET /ai/provider`
- Token counter utility (`app/ai/utils/token_counter.py`)
- AI-specific exceptions (14 types: `ProviderError`, `PromptNotFoundError`, `SafetyError`, etc.)
- Architecture: Fully isolated `app/ai/` module; no cross-contamination with business logic
- No medical logic, no RAG, no chatbot logic, no agents implemented
- 54 tests (provider abstraction, prompt registry, memory, safety, gateway pipeline, token utils, DI overrides, API endpoints)
- All tests use `MockLLMProvider` (no live LLM required)
- 54 tests (provider abstraction, prompt registry, memory, safety, gateway pipeline, token utils, DI overrides, API endpoints)
- All tests use `MockLLMProvider` (no live LLM required)

### Sprint 4.2 — Complete (Enterprise Knowledge Platform)
- 16 subdirectories under `app/ai/knowledge/` (api, catalog, chunkers, cleaners, exceptions, interfaces, loaders, metadata, normalizers, parsers, pipelines, schemas, services, storage, utils, validators)
- 7 abstract interfaces: Loader, Parser, Normalizer, Cleaner, MetadataExtractor, Chunker, Validator, StorageProvider
- 7 document loaders: TextLoader (TXT/MD), CSVLoader, JSONLoader, HTMLLoader, PDFLoader (3 library fallbacks), DOCXLoader (try/except dependency fallback)
- 5 normalizers: WhitespaceNormalizer, UnicodeNormalizer, QuoteNormalizer, NumberingNormalizer, CompositeNormalizer
- 2 cleaners: BoilerplateRemover (copyright, disclaimer, confidentiality patterns), HeaderFooterStripper
- MetadataExtractor: auto-extracts title, author, specialty, tags, language, word/char counts
- 4 chunking strategies: FixedSizeChunker, ParagraphChunker, HeadingAwareChunker, SlidingWindowChunker
- Validator: format validation, size check, encoding check, content quality check, checksum computation
- StorageProvider ABC + LocalFileStorage (JSON files, CRUD operations)
- KnowledgeCatalog: JSON-backed registry with add/update/get/list/remove/count
- ProcessingPipeline: 10-stage sequential pipeline (import → parse → normalize → clean → metadata → validate → chunk → store → catalog), each stage skippable
- KnowledgeService: facade with import_document, get_document, list_documents, delete_document, get_document_versions
- DI: `get_knowledge_service()` / `set_knowledge_service()` / `reset_knowledge_service()` singletons (overrideable for tests)
- 6 REST endpoints: `POST /ai/knowledge/import`, `GET /ai/knowledge/documents`, `GET /ai/knowledge/documents/{id}`, `DELETE /ai/knowledge/documents/{id}`, `GET /ai/knowledge/documents/{id}/versions`, `GET /ai/knowledge/stats`
- Knowledge settings added to AISettings: `KNOWLEDGE_ENABLED`, `KNOWLEDGE_STORAGE_PATH`, `KNOWLEDGE_CATALOG_PATH`, `KNOWLEDGE_MAX_FILE_SIZE_MB`, `KNOWLEDGE_DEFAULT_CHUNK_SIZE`, `KNOWLEDGE_DEFAULT_CHUNK_OVERLAP`
- No database models required — all storage is file-based JSON on local filesystem
- No embeddings, vector databases, semantic search, retrieval, Medical RAG, AI agents
- 71 tests (exceptions, schemas, utils, loaders, parsers, normalizers, cleaners, metadata, chunkers, validators, storage, catalog, pipeline, service, DI, API)
- All 614 tests passing, no regressions

---

### Sprint 4.3 — Complete (Enterprise Embedding Platform)
- 16 subdirectories under `app/ai/embeddings/` (api, deps, exceptions, interfaces, pipelines, providers, schemas, services, storage, batch, cache, versioning, validators, utils)
- `EmbeddingProvider` ABC with `MockEmbeddingProvider` (deterministic, L2-normalized, configurable 384-dim via MD5 seed)
- `DefaultEmbeddingPipeline`: 6-stage pipeline (validate chunk → validate provider → check cache → embed → validate vector → manage version → store vector + record)
- `MemoryEmbeddingCache`: thread-safe in-memory cache with hit/miss tracking, content-hash keyed `{provider}:{model}:{content_hash}`, pattern invalidation
- `InMemoryVersionManager`: version tracking per provider/model with create, deprecate, active version, history, auto-increment, rollback, `knowledge_version` linkage
- `DefaultEmbeddingValidator`: chunk emptiness/length (1-16384 chars), vector dimension/zero-vector, checksum, provider availability enum, duplicate detection by content hash
- `LocalEmbeddingStorage`: JSON-file based — separate `records/` and `vectors/` directories, CRUD + filtered listing (by knowledge_id, chunk_id, status, pagination)
- `BatchProcessor`: configurable batch-size parallel chunk processing with per-chunk retry (max 3), progress tracking
- `EmbeddingService` facade: `generate` (with `skip_duplicate_check`), `generate_batch`, `get_embedding`, `get_record`, `list_embeddings`, `delete_embedding`, `rebuild` (cache-bypass), `get_providers`
- Pipeline tracks `processing_time_ms` per embedding — stored in both `EmbeddingVector` and `EmbeddingRecord` schemas
- RBAC: `generate`/`generate-all`/`batches`/`reindex`/`rebuild`/`delete` → Admin or Doctor; `list`/`get` → any authenticated user; `providers` → any authenticated user
- 9 REST endpoints: `POST /ai/embeddings/generate`, `POST /ai/embeddings/generate-all`, `POST /ai/embeddings/batches`, `GET /ai/embeddings`, `GET /ai/embeddings/{id}`, `POST /ai/embeddings/rebuild`, `POST /ai/embeddings/reindex`, `DELETE /ai/embeddings/{id}`, `GET /ai/embeddings/providers`
- Configuration: 11 embedding settings in AISettings (`EMBEDDING_ENABLED`, `EMBEDDING_DEFAULT_PROVIDER`, `EMBEDDING_DEFAULT_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_BATCH_SIZE`, `EMBEDDING_MAX_RETRIES`, `EMBEDDING_RETRY_DELAY_MS`, `EMBEDDING_STORAGE_PATH`, `EMBEDDING_CACHE_ENABLED`, `EMBEDDING_VALIDATE_VECTORS`, `EMBEDDING_MAX_CHUNK_CHARS`)
- No database models required — all storage is file-based JSON on local filesystem
- No vector database, retrieval, similarity search, Medical RAG, AI assistant
- 78 tests (exceptions, schemas, utils, provider, validators, cache, versioning, pipeline, storage, batch, service, DI, API)
- All 770 tests passing, no regressions

---

### Sprint 4.4 — Complete (Enterprise Vector Platform)
- 9 subdirectories under `app/ai/vector/` (api, deps, exceptions, interfaces, providers, schemas, services, utils)
- `VectorStoreProvider` ABC: `add`, `add_batch`, `search`, `delete`, `delete_by_filter`, `count`, `clear`, `provider_name`
- `MemoryVectorStore`: in-memory with cosine similarity, thread-safe, filter operators ($gt/$gte/$lt/$lte/$ne/$in/$and/$or)
- `ChromaDBVectorStore`: ChromaDB-backed with cosine distance → similarity, optional dep via try/except
- `VectorService` facade: `index_vector`, `index_batch`, `search_by_vector`, `delete`, `delete_by_filter`, `get_stats`, `clear`
- DI: `get_vector_service()` / `set_vector_service()` / `reset_vector_service()` (overrideable for tests)
- 5 REST endpoints: `POST /ai/vector/search`, `POST /ai/vector/index`, `GET /ai/vector/stats`, `DELETE /ai/vector/{id}`, `DELETE /ai/vector/clear`
- Configuration: 6 vector settings in AISettings (`VECTOR_ENABLED`, `VECTOR_DEFAULT_PROVIDER`, `VECTOR_STORE_PATH`, `VECTOR_COLLECTION_NAME`, `VECTOR_DEFAULT_TOP_K`, `VECTOR_MAX_TOP_K`)
- No database models required — all storage is in-memory or ChromaDB
- No retrieval, RAG, chatbot integration — pure vector storage and similarity search
- 78 tests (exceptions, schemas, utils, memory store, service, DI, API)
- All 751 tests passing, no regressions

### Sprint 4.5 — Complete (Enterprise Retrieval Engine)
- 9 subdirectories under `app/ai/retrieval/` (api, deps, exceptions, interfaces, pipelines, providers, rerankers, schemas, services, utils)
- `RerankerProvider` ABC: `rerank(query, results, top_k) -> list[RetrievalResult]`
- 3 reranker implementations:
  - `NoOpReranker`: assigns rank indices in original order, respects top_k
  - `MockReranker`: sorts by score descending, assigns ranks
  - `TimeReranker`: sorts by `created_at` metadata descending (recency-based)
- `RetrievalPipeline`: orchestrates embed query → vector search → chunk retrieval → filter by min_score → rerank
- `RetrievalService` facade: `search`, `retrieve`, `assemble_context`, `rag_generate`
- `assemble_context`: retrieves chunks, builds context string with `[Source N]` formatting, token estimation, automatic truncation at `max_tokens` threshold
- `rag_generate`: assembles context → calls `GatewayPipeline.execute()` with default RAG system message (`{context}` injected) → returns answer + sources + timing
- Default RAG system message with citation instructions and "don't make up information" guardrails
- Integration points:
  - `EmbeddingService.generate()` → query embedding (handles failed status → raises `EmbeddingQueryError`)
  - `VectorService.search_by_vector()` → similarity search with filter/min_score support
  - `KnowledgeService.get_chunk()` → chunk content retrieval (new method added)
  - `GatewayPipeline.execute()` → context-augmented LLM generation
- DI: `get_retrieval_service()` / `set_retrieval_service()` / `reset_retrieval_service()` (singleton pattern)
- 2 REST endpoints: `POST /ai/retrieval/search`, `POST /ai/retrieval/rag`
- RBAC: All authenticated users (any role) can search and RAG
- Configuration: 6 retrieval settings in AISettings (`RETRIEVAL_ENABLED`, `RETRIEVAL_DEFAULT_TOP_K`, `RETRIEVAL_MAX_TOP_K`, `RETRIEVAL_DEFAULT_RERANKER`, `RETRIEVAL_MAX_CONTEXT_TOKENS`, `RETRIEVAL_ALLOW_RAG`)
- No medical RAG, no AI assistant — pure retrieval + RAG infrastructure
- 33 tests (exceptions, schemas, rerankers, service, pipeline, DI, API, knowledge integration)
- All 803 tests passing, no regressions

### Sprint 4.6 Volume 1 — Complete (Enterprise Medical Intelligence Platform)
- **Enterprise Medical Intelligence Platform** — query understanding, rewriting, retrieval orchestration, reasoning, citations, confidence scoring, safety validation, and structured responses
- 17 subdirectories under `app/ai/medical/` (api, citations, confidence, config, deps, exceptions, intent, interfaces, pipelines, reasoning, responses, rewriters, safety, schemas, services, utils, validators)
- 9 abstract interfaces: IntentDetectorABC, QueryRewriterABC, ContextOptimizerABC, MedicalPromptBuilderABC, MedicalReasonerABC, CitationEngineABC, ConfidenceEngineABC, SafetyValidatorABC, ResponseBuilderABC
- **IntentDetector** — rule-based detection of 10 intent types, 20 medical specialties, 5 urgency levels
- **QueryRewriter** — medical abbreviation expansion (30+), intent-specific query expansion, specialty context injection
- **CitationEngine** — structured CitationEntry list from retrieval results
- **ConfidenceEngine** — multi-dimensional scoring (retrieval, evidence, generation, citation coverage)
- **SafetyValidator** — unsafe advice, hallucination, contradiction detection, disclaimer enforcement
- **MedicalReasoner** — chain-of-thought, differential considerations, limitations, evidence summary
- **ResponseBuilder** — structured MedicalResponse assembly with citation references and safety warnings
- **MedicalPipeline** — 10-stage orchestration: intent → rewrite → context → prompt → generate → citations → reason → confidence → safety → response
- **MedicalService** — facade with `query()` (full pipeline + retrieval) and `search()` (retrieval + intent + citations)
- **MedicalSettings** — 11 configurable settings
- DI: `get_medical_service()` / `set_medical_service()` / `reset_medical_service()` — singleton pattern
- 2 REST endpoints: `POST /ai/medical/query`, `POST /ai/medical/search`
- 58 tests
- All 861 tests passing

### Sprint 4.6 Volume 2 — Complete (Enterprise Medical Query Understanding Engine)
- **Enterprise Medical Query Understanding Engine** — transforms unstructured user questions into structured medical intelligence BEFORE retrieval/LLM
- 9 new submodules under `app/ai/medical/` (intent/restructured, rewrite/, entities/, specialty/, urgency/, audience/, language/, context/, taxonomy/)
- **QueryUnderstandingEngine** — orchestrates all 9 modules: intent → entities → specialty → urgency → audience → language → context → rewrite
- **Intent Detection** (15 categories): symptom_inquiry, disease_information, medication_information, prescription_explanation, lab_report_interpretation, medical_record_explanation, appointment_inquiry, preventive_care, emergency, mental_health, lifestyle_guidance, nutrition, vaccination, follow_up, administrative — with confidence-ranked candidates
- **Clinical Specialty Classification** — 12 specialties with ranked confidence, matched terms, multi-specialty support
- **Medical Entity Recognition** — 13 entity types (symptom, disease, medication, procedure, lab_test, vital_sign, anatomy, allergy, dosage, time_expression, age_reference, chronic_condition, pregnancy_status) via regex patterns
- **Urgency Classification** — 4 levels (emergency, urgent, routine, informational) with advisory disclaimer
- **Audience Classification** — 6 audience types (patient, doctor, nurse, caregiver, administrator, unknown)
- **Language Detection** — language detection, abbreviation/acronym detection, informal phrasing, typo detection, normalization
- **Query Rewriting** — abbreviation expansion (35+), normalized output while preserving original
- **Conversation Awareness** — integrates with existing Memory Platform (InMemoryMemoryManager) via ContextResolver
- **Medical Taxonomy Abstraction** — interface for future ICD-10, ICD-11, SNOMED CT, LOINC, RxNorm, ATC integration
- **New Exceptions**: QueryUnderstandingError hierarchy (9 types: IntentError → TaxonomyError)
- **Dependency Injection**: `get_query_understanding_engine()` / `set_query_understanding_engine()` / `reset_query_understanding_engine()` singleton pattern
- **6 REST endpoints**: `POST /ai/medical/analyze`, `POST /ai/medical/intent`, `POST /ai/medical/entities`, `POST /ai/medical/rewrite`, `GET /ai/medical/specialties`, `GET /ai/medical/intents`
- **Business Rules**: Original query always preserved, rewritten queries internal only, deterministic classification for identical inputs, multiple intent candidates allowed, confidence scores required
- **Validation**: Empty queries rejected, max length 10000 chars, structured validation errors
- No LLM calls — pure rule-based NLU; no medical answers generated
- 77 tests (exceptions, schemas, intent classifiers, entity extraction, specialty classification, urgency, audience, language, rewrite, context, taxonomy, engine orchestration, DI, API auth/RBAC)
- All 938 tests passing (861 Volume 1 + 77 Volume 2), zero regressions

### Sprint 4.6 Volume 4 Part 3 — Complete (Enterprise Clinical Safety Platform)
- **Enterprise Clinical Safety Platform** — final trust gate before any AI-generated medical response is delivered, responsible for hallucination prevention, unsupported claim detection, clinical safety validation, emergency escalation, PHI validation, disclaimer selection, compliance, and final approval
- 12 exceptions: `ClinicalSafetyError` hierarchy (HallucinationDetectionError → SafetyValidationError)
- 7 enums: `HallucinationType`, `SupportLevel`, `RiskLevel`, `EmergencyType`, `PHIType`, `DisclaimerType`, `ApprovalDecision`
- 18 Pydantic schemas: `HallucinationReport`, `UnsupportedClaimReport`, `ClinicalRiskReport`, `EmergencyReport`, `PHIValidationReport`, `DisclaimerResult`, `ComplianceReport`, `ApprovalResult`, `SafetyState`, `PipelineResult`, `SafetyServiceResult`, etc.
- 8 ABC interfaces: `HallucinationDetector`, `UnsupportedClaimDetector`, `ClinicalRiskEngine`, `EmergencyDetector`, `PHIValidator`, `DisclaimerEngine`, `ComplianceValidator`, `SafetyApprovalEngine`
- 8 engine implementations:
  - **HallucinationDetectorService** — 7 hallucination types (FABRICATED_MEDICATION, FABRICATED_DISEASE, FABRICATED_CITATION, FABRICATED_GUIDELINE, FABRICATED_STATISTIC, FABRICATED_RECOMMENDATION, UNSUPPORTED_CLAIM) using built-in medication/disease lists and regex patterns; NO LLM
  - **UnsupportedClaimDetectorService** — FULLY_SUPPORTED/PARTIALLY_SUPPORTED/UNSUPPORTED/CONTRADICTORY classification
  - **ClinicalRiskEngineService** — weighted scoring → LOW/MODERATE/HIGH/CRITICAL
  - **EmergencyDetectorService** — 7 emergency types via regex
  - **PHIValidatorService** — 10 PHI types (SSN, email, phone, Aadhaar, passport, credit card, MRN, insurance ID, DOB, name)
  - **DisclaimerEngineService** — 7 built-in disclaimers, context-aware selection
  - **ComplianceValidatorService** — 7 compliance checks
  - **SafetyApprovalEngineService** — 4-level decision (APPROVED/APPROVED_WITH_WARNINGS/ESCALATE/REJECT)
- **ClinicalSafetyPipeline** — 8-stage pipeline (hallucination → emergency → unsupported → risk → PHI → disclaimer → compliance → approval)
- **ClinicalSafetyService** — facade with 9 public methods
- **Dependency Injection**: `get_`/`set_`/`reset_` for all 8 engines + pipeline + service — follows same singleton pattern
- **10 REST endpoints**: `GET /ai/safety/health`, `POST /ai/safety/validate`, `POST /ai/safety/hallucination`, `POST /ai/safety/unsupported`, `POST /ai/safety/risk`, `POST /ai/safety/emergency`, `POST /ai/safety/phi`, `POST /ai/safety/disclaimer`, `POST /ai/safety/compliance`, `POST /ai/safety/approval`
- **Business Rules**: Every response must pass safety validation; hallucinated content never approved; emergencies bypass normal flow; risk classifications deterministic; approval decisions auditable
- Independent of Retrieval and Evidence — pure rule-based safety validation
- 324 tests, all passing
- Total test count: 324 clinical safety + 308 evidence + 938 prior = 1,570 tests

---

## Current API Surface (105+ endpoints)

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
| GET | `/analytics/platform` | Admin only | Platform-wide entity counts, activity trends, growth metrics |
| GET | `/analytics/doctor` | Doctor only | Personal doctor KPIs, averages, recent activity |
| GET | `/analytics/patient` | Patient only | Personal patient clinical summary, timeline |
| GET | `/analytics/system` | Admin only | System-wide trends, top doctors, utilization rates |
| GET | `/analytics/summary` | Admin only | High-level summary cards with total counts |
| POST | `/jobs` | Admin only | Submit a background job |
| GET | `/jobs` | Admin only | List jobs with status/type filters |
| GET | `/jobs/health` | Admin only | Job system health status |
| GET | `/jobs/{id}` | Admin only | Get job details |
| DELETE | `/jobs/{id}` | Admin only | Delete a job |
| POST | `/jobs/{id}/retry` | Admin only | Retry a failed/pending job |
| POST | `/jobs/{id}/cancel` | Admin only | Cancel a running/pending job |
| POST | `/ai/generate` | Authenticated | Generate AI response through gateway pipeline |
| POST | `/ai/prompts` | Authenticated | Register a prompt template |
| GET | `/ai/prompts` | Authenticated | List prompt templates |
| GET | `/ai/prompts/{name}` | Authenticated | Get prompt template by name |
| POST | `/ai/conversations` | Authenticated | Create a conversation |
| DELETE | `/ai/conversations/{id}` | Authenticated | Delete a conversation |
| POST | `/ai/safety/check` | Authenticated | Check text for safety issues |
| GET | `/ai/provider` | Authenticated | Get active AI provider info |
| POST | `/ai/knowledge/import` | Authenticated | Import document into knowledge base |
| GET | `/ai/knowledge/documents` | Authenticated | List knowledge base documents |
| GET | `/ai/knowledge/documents/{id}` | Authenticated | Get document by ID |
| DELETE | `/ai/knowledge/documents/{id}` | Authenticated | Delete document from knowledge base |
| GET | `/ai/knowledge/documents/{id}/versions` | Authenticated | Get document version history |
| GET | `/ai/knowledge/stats` | Authenticated | Knowledge base statistics |
| POST | `/ai/embeddings/generate` | Authenticated | Generate embedding for a single chunk |
| POST | `/ai/embeddings/generate-all` | Admin/Doctor | Generate embeddings for all chunks |
| POST | `/ai/embeddings/batches` | Admin/Doctor | Submit batch of chunks for embedding |
| GET | `/ai/embeddings` | Authenticated | List embeddings with optional filters |
| GET | `/ai/embeddings/{id}` | Authenticated | Get embedding details by ID |
| POST | `/ai/embeddings/rebuild` | Admin/Doctor | Rebuild embeddings (bypass cache) |
| POST | `/ai/embeddings/reindex` | Admin/Doctor | Reindex embeddings with new version |
| DELETE | `/ai/embeddings/{id}` | Admin/Doctor | Delete an embedding |
| GET | `/ai/embeddings/providers` | Authenticated | List available embedding providers |
| POST | `/ai/vector/search` | Authenticated | Search similar vectors by query vector |
| POST | `/ai/vector/index` | Authenticated | Index embeddings from storage into vector store |
| GET | `/ai/vector/stats` | Authenticated | Vector store statistics |
| DELETE | `/ai/vector/{id}` | Authenticated | Delete a vector from the store |
| DELETE | `/ai/vector/clear` | Authenticated | Clear all vectors from the store |
| POST | `/ai/retrieval/search` | Authenticated | Semantic search across knowledge base |
| POST | `/ai/retrieval/rag` | Authenticated | Retrieval-Augmented Generation with context-aware answer |
| POST | `/ai/medical/query` | Authenticated | Medical intelligence query with intent detection, citations, confidence |
| POST | `/ai/medical/search` | Authenticated | Medical search with intent detection across knowledge base |
| POST | `/ai/medical/analyze` | Authenticated | Full query understanding — intent, entities, specialty, urgency, audience, language, rewrite |
| POST | `/ai/medical/intent` | Authenticated | Detect medical intent of a query (15 categories) |
| POST | `/ai/medical/entities` | Authenticated | Extract structured medical entities (13 types) |
| POST | `/ai/medical/rewrite` | Authenticated | Rewrite query with abbreviation expansion |
| GET | `/ai/medical/specialties` | Authenticated | List supported medical specialties (12) |
| GET | `/ai/medical/intents` | Authenticated | List supported intent categories (15) |
| POST | `/ai/evidence/validate` | Authenticated | Validate evidence for medical response spans |
| POST | `/ai/evidence/verify` | Authenticated | Verify evidence spans against knowledge base |
| POST | `/ai/evidence/citations` | Authenticated | Generate citations for evidence spans |
| POST | `/ai/evidence/coverage` | Authenticated | Analyze evidence coverage |
| POST | `/ai/evidence/conflicts` | Authenticated | Detect conflicts in evidence |
| POST | `/ai/evidence/confidence` | Authenticated | Calculate confidence scores for evidence |
| POST | `/ai/evidence/provenance` | Authenticated | Track provenance of evidence processing |
| POST | `/ai/evidence/explain` | Authenticated | Get explanation of evidence validation results |
| POST | `/ai/evidence/pipeline` | Authenticated | Run full evidence pipeline |
| GET | `/ai/safety/health` | Public | Clinical Safety service health check |
| POST | `/ai/safety/validate` | Authenticated | Run full clinical safety validation on a response |
| POST | `/ai/safety/hallucination` | Authenticated | Detect hallucinations in a response |
| POST | `/ai/safety/unsupported` | Authenticated | Detect unsupported claims in a response |
| POST | `/ai/safety/risk` | Authenticated | Assess clinical risk level of a response |
| POST | `/ai/safety/emergency` | Authenticated | Detect emergency situations in a response |
| POST | `/ai/safety/phi` | Authenticated | Validate response for PHI leakage |
| POST | `/ai/safety/disclaimer` | Authenticated | Select appropriate medical disclaimers |
| POST | `/ai/safety/compliance` | Authenticated | Validate regulatory compliance of a response |
| POST | `/ai/safety/approval` | Authenticated | Get safety approval decision for a response |

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
| Enterprise Analytics APIs (Platform, Doctor, Patient, System, Summary) | ✅ |
| Enterprise Background Jobs & Task Orchestration (Job model, service, API, scheduler, worker, 42 tests) | ✅ |
| Enterprise Cache Platform (CacheProvider, CacheService, FeatureFlags, 5-service integration, 53 tests) | ✅ |
| Lifespan migration (replaced deprecated `on_event` with `lifespan` context manager) | ✅ |
| Pydantic validation (EmailStr, length constraints) | ✅ |
| Automated tests (pytest, isolated DB, 938 tests across 19 files) | ✅ |
| AI Platform Foundation (provider abstraction, prompt registry, memory, safety, gateway) | ✅ |
| AI-specific tests (54 tests, MockLLMProvider, no live LLM) | ✅ |
| Enterprise Knowledge Platform (loaders, parsers, normalizers, cleaners, chunkers, validators, storage, catalog, pipeline, service, API) | ✅ |
| Knowledge Platform tests (71 tests, mock-based, no external dependencies) | ✅ |
| Enterprise Embedding Platform (provider abstraction, pipeline, batch, cache, versioning, validation, storage, service, API) | ✅ |
| Embedding Platform tests (78 tests, mock-based, no live embedding models) | ✅ |
| Enterprise Vector Platform (VectorStoreProvider ABC, MemoryVectorStore, ChromaDBVectorStore, VectorService, DI, API) | ✅ |
| Vector Platform tests (78 tests, mock-based, no live vector store required) | ✅ |
| Enterprise Retrieval Engine (RerankerProvider ABC, 3 rerankers, RetrievalPipeline, RetrievalService with search/assemble/rag) | ✅ |
| RAG generation with context assembly, token budgeting, GatewayPipeline integration | ✅ |
| Retrieval Engine tests (33 tests, mock-based, no live services required) | ✅ |
| Medical Intelligence Platform Volume 1 (10-stage pipeline, 58 tests) | ✅ |
| Medical Query Understanding Platform Volume 2 (9 submodules, 6 endpoints, 77 tests) | ✅ |
| Evidence Intelligence Platform (9 engines, 308 tests, 93% coverage) | ✅ |
| Clinical Safety Platform (8 engines, 10 endpoints, 324 tests, 93% coverage) | ✅ |
| Hallucination detection (7 types, rule-based, no LLM) | ✅ |
| Unsupported claim detection (4 levels, evidence-based) | ✅ |
| Clinical risk classification (4 levels, weighted scoring) | ✅ |
| Emergency escalation (7 emergency types, override flow) | ✅ |
| PHI validation (10 PHI types, value masking) | ✅ |
| Medical Disclaimer Engine (7 disclaimers, context-aware) | ✅ |
| Regulatory compliance (7 checks, prohibited terms enforcement) | ✅ |
| Safety Approval Engine (4 decision levels, deterministic rules) | ✅ |
| Dependency Injection (get/set/reset for all 8 engines + pipeline + service) | ✅ |
| Documentation (AGENTS, PROJECT_CONTEXT, ARCHITECTURE, CURRENT_TASK) | ✅ |
| All endpoints pass Swagger verification | ✅ |

---

## Next Sprint: Sprint 4.7 — AI Assistant

### Planned
- Doctor AI Assistant with specialized medical knowledge
- Patient-facing intelligent health companion
- Multi-turn conversational medical guidance
- Integration with Medical Intelligence Platform for grounded responses
- Medical Ontology Integration (ICD-10, SNOMED CT, RxNorm, LOINC) follows

## Technical Debt & Future Work

### Clinical Safety Platform
- Clinical guideline rule engine (structured guideline-as-code)
- Regulatory rule packs by country (HIPAA, GDPR, DPDP, etc.)
- ML-based hallucination detection (complement rule-based)
- Physician review workflows (human-in-the-loop approval)
- Adaptive safety policies based on user role and context
- Safety report persistence to database for audit trail
- Rate limiting on safety endpoints
- Caching for disclaimer selection and compliance results
- Safety dashboard for admin monitoring
- Integration test with full pipeline (query → medical → evidence → safety)
