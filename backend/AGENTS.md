# ArogyaAI Agent Instructions

## Project Overview

ArogyaAI is an AI-powered healthcare continuity platform. The backend is a REST API built with FastAPI, SQLAlchemy 2.0, and SQLite (development) / PostgreSQL (planned).

---

## Tech Stack

- **Framework**: FastAPI 0.137.0
- **ORM**: SQLAlchemy 2.0 (DeclarativeBase, Mapped, mapped_column)
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **Auth**: JWT (access + refresh tokens), bcrypt
- **Validation**: Pydantic v2
- **Migrations**: Alembic
- **Testing**: pytest, httpx, FastAPI TestClient
- **Runtime**: Python 3.13+, uvicorn

---

## Folder Structure

```
backend/
├── app/
│   ├── ai/            # AI Platform (providers, prompts, memory, gateway, safety, knowledge, embeddings, vector, retrieval, medical)
│   │   ├── knowledge/ # Knowledge Platform (loaders, parsers, chunkers, cleaners, pipeline)
│   │   ├── embeddings/# Embedding Platform (providers, pipeline, batch, cache, storage, validators, versioning)
│   │   ├── vector/    # Vector Platform (providers, services, API, DI)
│   │   ├── retrieval/ # Retrieval Engine (pipeline, rerankers, service, API, DI)
│   │   ├── clinical_safety/ # Clinical Safety Platform (api, config, deps, exceptions, interfaces, pipelines, schemas, services)
│   │   └── medical/   # Medical Intelligence Platform (intent, rewriters, rewrite, entities, specialty, urgency, audience, language, context, taxonomy, engine, citations, reasoning, confidence, safety, responses)
│   ├── api/           # Route handlers (routers)
│   ├── cache/         # Cache platform (providers, service, feature flags)
│   ├── core/          # Config, security, logging
│   ├── database/      # Engine, session, Base
│   ├── models/        # SQLAlchemy models
│   ├── ratelimit/     # Rate limiting platform (providers, middleware, deps)
│   ├── schemas/       # Pydantic request/response schemas
│   └── services/      # Business logic layer (CRUD + DashboardService + AnalyticsService)
├── tests/
│   ├── conftest.py    # Fixtures, test DB
│   ├── test_smoke.py  # Smoke tests
│   ├── test_medical_query_understanding.py  # Medical Query Understanding tests (77)
│   ├── test_ai_platform.py  # AI Platform tests (54)
│   ├── test_analytics.py  # Analytics tests
│   ├── test_cache.py      # Cache tests
│   ├── test_embedding_platform.py  # Embedding Platform tests (59)
│   ├── test_knowledge_platform.py  # Knowledge Platform tests (71)
│   ├── test_ratelimit.py  # Rate limit tests
│   ├── test_embedding_platform.py  # Embedding Platform tests (78)
│   ├── test_knowledge_platform.py  # Knowledge Platform tests (71)
│   ├── test_ratelimit.py  # Rate limit tests
│   ├── test_medical_query_understanding.py  # Medical Query Understanding tests (77)
│   └── ai/
│       ├── evidence/     # Evidence Intelligence tests (308)
│       └── clinical_safety/  # Clinical Safety tests (324)
├── alembic/           # Database migrations
└── docs/              # Project documentation
```

---

## Architecture Rules

1. **Layers**: models → schemas → services → api (strict top-down; no skipping or circular deps)
2. **Build order**: Database → Models → Schemas → Services → APIs → Tests
3. **Services**: All methods are `@staticmethod`, accept `db: Session`, return ORM objects or `None`
4. **Routers**: Only authenticate, validate (Pydantic), call service, return response. No inline business logic.
5. **No circular imports**: Models never import from services or api; services import from models and schemas; api imports from services and deps.

---

## Coding Conventions

### SQLAlchemy 2.0 Rules
- Use `Mapped[]` and `mapped_column()` everywhere
- Use `DeclarativeBase` (not `declarative_base()`)
- Use `db.scalar(select(...))` for scalar queries, `db.execute(select(...))` for multi-row
- Use `db.get(Model, id)` for primary key lookups
- All models have `id` (PK, autoincrement), `created_at` (server_default=func.now())
- FK columns are nullable=True; relationships use `back_populates`
- `user_id` on Doctor/Patient is nullable FK to users.id (True)

### Pydantic / Schema Rules
- Request schemas use `BaseModel` with `Field(min_length=..., max_length=...)` matching DB column sizes
- Response schemas use `model_config = ConfigDict(from_attributes=True)`
- PATCH schemas make all fields `None` default; services use `exclude_unset=True`
- Use `EmailStr` for email fields

### FastAPI Conventions
- Router prefix matches resource name (e.g., `/users`, `/doctors`, `/patients`)
- `tags` provide Swagger grouping
- All authenticated endpoints use `Depends(get_current_user)`
- Role-restricted endpoints use `Depends(require_roles(...))` or explicit role checks in router

---

## Layer Responsibilities

### Models (`app/models/`)
- Define tables, columns, types, constraints, relationships
- No business logic, no validation, no serialization

### Schemas (`app/schemas/`)
- Define request shapes (what the client sends)
- Define response shapes (what the client receives)
- Validation rules: type checks, length constraints, email format
- `from_attributes=True` for response schemas (ORM mode)
- `exclude_unset=True` for partial updates

### Services (`app/services/`)
- All database operations (CRUD + analytics)
- Business rules and validation beyond type checking
- Static methods only; no state
- Return ORM objects or `None` (CRUD), `AnalyticsService` returns Pydantic response objects
- Accept `db: Session` as first parameter, user/data objects as needed
- `AnalyticsService` follows the same static-method pattern but returns schema objects directly
- **AI Services**: GatewayService, PromptManager, MemoryManager, SafetyService are async ABCs in `app/ai/interfaces/`; injectable via `Depends()`
- **Embedding Services**: EmbeddingService, EmbeddingPipeline, EmbeddingProvider, EmbeddingValidator, EmbeddingCache, EmbeddingVersionManager are async ABCs in `app/ai/embeddings/interfaces/`; injectable via `Depends()`

### APIs (`app/api/`)
- Route definitions with HTTP method, path, response model, status codes
- Dependency injection for `db`, `current_user`
- Call service methods; wrap results in HTTP responses or exceptions
- No inline database queries (except role resolution lookups where unavoidable)

---

## Dependency Injection Rules

- `get_db`: yields SQLAlchemy `Session`, always as `Depends(get_db)`
- `get_current_user`: validates Bearer token, returns `User` or 401
- `require_roles(*roles)`: factory for role-based access control
- Override `app.dependency_overrides[get_db]` in tests to isolate database
- AI providers/registries/managers use get/set/reset singleton pattern (same as cache & ratelimit)
  - `get_llm_provider()` / `set_llm_provider()` / `reset_llm_provider()`
  - `get_prompt_registry()` / `set_prompt_registry()` / `reset_prompt_registry()`
  - `get_memory_manager()` / `set_memory_manager()` / `reset_memory_manager()`
  - `get_safety_service()` / `set_safety_service()` / `reset_safety_service()`
  - `get_gateway()` / `set_gateway()` / `reset_gateway()`
  - `get_verifier()` / `set_verifier()` / `reset_verifier()` (evidence)
  - `get_hallucination_detector()` / `set_hallucination_detector()` / `reset_hallucination_detector()` (clinical safety)

---

## Authentication Flow

1. Client sends `POST /auth/register` with `{email, password, role}`
2. Password is bcrypt-hashed; user stored in `users` table
3. Client sends `POST /auth/login` → server verifies password → returns `{access_token, refresh_token, token_type}`
4. Authenticated requests include `Authorization: Bearer <access_token>`
5. Access token: 30 min expiry, `{sub: user_id, role: role, type: "access"}`
6. Refresh token: 7 day expiry, `{sub: user_id, role: role, type: "refresh"}`
7. `POST /auth/refresh` with expired access token + valid refresh token → new access token
8. `POST /auth/change-password` with `{old_password, new_password}`

---

## Authorization Flow

- **Public**: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /`, `GET /health`
- **Authenticated (any role)**: `GET /users/me`, `PATCH /users/me`, `GET /doctors/me`, `PATCH /doctors/me`, `GET /patients/me`, `PATCH /patients/me`, `POST /profile/complete`
- **Doctor or Admin**: `POST /visits`, `PUT /visits/{id}`, `DELETE /visits/{id}`
- **Own-visit access**: Doctors see visits where `doctor_id == doctor.id`; patients see visits where `patient_id == patient.id`

---

## Profile Completion Flow

1. User registers → has `User` record only, no `Doctor`/`Patient` profile
2. Client calls `POST /profile/complete` with role-appropriate fields
3. Router checks `current_user.role`:
   - `DOCTOR` → `DoctorService.create_doctor_profile()` — populates `user_id`, `full_name`, `email` (from user), `phone_number`, `specialization`, `clinic_name`
   - `PATIENT` → `PatientService.create_patient_profile()` — populates `user_id`, `full_name`, `phone_number`, `date_of_birth`, `gender`, `emergency_contact`
4. Returns 409 if profile already exists
5. Returns 400 if role does not support profile completion (e.g., caregiver)

---

## Alembic Workflow

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check status
alembic current
```

Current migration: `a1c0304461c0` (add_notifications_table) — latest of 7 migration files.

---

## Testing Workflow

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app

# Run specific test file
python -m pytest tests/test_analytics.py -v
```

- Tests use isolated `test.db` SQLite (never touches `arogyaai.db`)
- `get_db` is overridden to use test database
- Each test gets a fresh transaction that rolls back on cleanup
- Fixtures: `db`, `client`, `doctor_token`, `patient_token`, `admin_token`, `doctor_with_profile`, `patient_with_profile`
- Total test count: 1,570 tests across 35+ test files (938 prior + 308 evidence + 324 clinical safety)

---

## Git Workflow

- Feature branches from `main`
- Commit messages: concise, imperative mood
- No direct pushes to `main`
- PRs with summary of changes

---

## Documentation Standards

- `AGENTS.md` — engineering workflow, conventions, sprint status
- `docs/PROJECT_CONTEXT.md` — product vision, capabilities, roadmap
- `docs/ARCHITECTURE.md` — technical architecture, layers, data flow
- `docs/CURRENT_TASK.md` — current sprint status, next sprint plans
- Docs must match implementation exactly; clearly mark not-yet-implemented features as "Planned"

---

## Sprint History

### Sprint 1 — Complete
- SQLite infrastructure, Base class, SessionLocal, Alembic setup
- Doctor model, Patient model, Visit model
- Visit CRUD schemas, service (7 methods), API (5 endpoints)
- Swagger verification

### Sprint 2 — Complete
- User model with roles (admin, doctor, patient, caregiver, receptionist)
- Auth system: register, login, JWT (access + refresh), change password
- AuditLog model

### Sprint 2.5 — Complete
- User Profile API (GET/PATCH /users/me)
- Doctor Profile API (GET/PATCH /doctors/me) with schemas + service
- Patient Profile API (GET/PATCH /patients/me) with schemas + service
- Profile Completion API (POST /profile/complete)

### Sprint 2.6 — Complete
- Critical stabilization (visit auth bug fix, SECRET_KEY, .gitignore, validation)
- Automated testing: pytest, conftest.py, 12 smoke tests
- Documentation refresh

### Sprint 3.8.1 — Complete
- Enterprise Notification System (model, migration, 6 event hooks, 9 endpoints, 32 tests)

### Sprint 3.8.2 — Complete
- Global Search across 11 entities (service, RBAC, pagination, 72 tests)

### Sprint 3.8.3 — Complete
- Enterprise Dashboard APIs (Doctor, Patient, Admin dashboards)
- `DashboardService` aggregates data efficiently (no N+1, single queries)
- 3 GET endpoints: `/dashboard/doctor`, `/dashboard/patient`, `/dashboard/admin`
- 50 tests covering auth, RBAC, edge cases, response shape

### Sprint 3.8.4 — Complete
- Enterprise Analytics APIs (Platform, Doctor, Patient, System, Summary)
- `AnalyticsService` — reusable layer with 5 public methods, 12+ private helpers
- 5 GET endpoints: `/analytics/platform`, `/analytics/doctor`, `/analytics/patient`, `/analytics/system`, `/analytics/summary`
- Single-query GROUP BY patterns for time-series trends (daily/weekly/monthly)
- Growth metrics, utilization rates, most-active-doctor rankings
- Date-range filtering on all analytics endpoints
- RBAC: Admin→all, Doctor→own, Patient→own
- 50 tests covering auth, RBAC, counts, aggregations, date filters, edge cases, response shape

### Sprint 3.8.5 — Complete
- JobStatus/JobType enums, Job SQLAlchemy model
- Alembic migration `2d5dc9f0cccb` (add_jobs_table)
- Job schemas (create, response, update, retry, list, health)
- Job abstraction layer: JobRegistry, APSchedulerProvider (dev), InProcessWorker
- 10 health-task handlers via registry
- JobService — 9 static methods (submit, list, get, update, delete, retry, cancel, health, status)
- 6 job REST endpoints (all Admin-only): POST/GET /jobs, GET /jobs/health, GET/DELETE /jobs/{id}, POST /jobs/{id}/retry, POST /jobs/{id}/cancel
- Fixed route ordering: `/jobs/health` before `/{job_id}`
- Migrated `on_event` → FastAPI `lifespan` context manager (fixes DeprecationWarning)
- 42 tests (auth, RBAC, CRUD, edge cases, response shape)

### Volume 6 — Complete (Enterprise Cache Platform)
- `CacheProvider` abstract base class with `CacheStats`, `CacheEntry`, `TTL` constants
- `MemoryCacheProvider` — thread-safe in-memory dict with TTL expiry, pattern-based clear, hit/miss/eviction tracking
- `RedisCacheProvider` — Redis-backed provider with SCAN-based pattern clear, pipeline operations
- `CacheService` — static-method service with `build_key`, `get`, `set`, `get_or_set`, `invalidate_key`, `invalidate_namespace`, `clear_all`, `get_stats`, `get_many`
- Cache key naming convention: `{redis_prefix}:v1:{namespace}:{parts}`
- `FeatureFlags` — flag enable/disable/check via cache, namespaced under `feature`
- `get_cache_provider()` / `set_cache_provider()` / `reset_cache_provider()` singletons (overrideable for tests)
- DashboardService caching: all 3 dashboard methods with 5-min TTL
- AnalyticsService caching: all 5 analytics methods with 5-min TTL
- SearchService caching: global_search results with 1-min TTL
- NotificationService caching: unread count with 1-min TTL + invalidation on create/mark-read/delete
- MedicineService caching: get/list/search with 1-hour TTL + invalidation on create/update/delete
- Cache settings added to `config.py`: `CACHE_PROVIDER`, `REDIS_URL`, `REDIS_PREFIX`, 6 TTL settings
- 53 tests (provider, service, feature flags, TTL/eviction, integration with 5 services, benchmarks)

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

### Volume 7 — Complete (Enterprise API Protection)
- `RateLimiter` abstract base class with `RateLimitResult`, `RateLimitRule`, `RateLimitScope`
- `MemoryRateLimiter` — sliding-window log using deque per key, thread-safe, TTL-based expiry
- `RedisRateLimiter` — Redis-backed sliding window using sorted sets (ZREMRANGEBYSCORE + ZADD + ZCARD)
- `RateLimitMiddleware` — FastAPI middleware applying IP-based limits to all endpoints
- Public endpoint overrides: `/auth/login` (5/min), `/auth/register` (3/hour)
- `rate_limit()` dependency factory for per-endpoint user-specific limits
- `get_rate_limiter()` / `set_rate_limiter()` / `reset_rate_limiter()` singletons (overrideable for tests)
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- 429 JSON responses with `retry_after_seconds` detail
- Config-driven: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PROVIDER`, `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_AUTHENTICATED`, `RATE_LIMIT_LOGIN_MAX`, `RATE_LIMIT_REGISTER_MAX`, `RATE_LIMIT_BURST_MULTIPLIER`
- 35 tests (rule/result models, memory limiter, sliding window, login protection, 429 responses, edge cases, concurrent access)
- All 543 tests passing, no regressions

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
- 11 embedding settings in AISettings (`EMBEDDING_ENABLED`, `EMBEDDING_DEFAULT_PROVIDER`, etc.)
- No database models required — all storage is file-based JSON on local filesystem
- No vector database, retrieval, similarity search, Medical RAG, AI assistant
- 78 tests (exceptions, schemas, utils, provider, validators, cache, versioning, pipeline, storage, batch, service, DI, API)
- All 770 tests passing, no regressions

### Sprint 4.4 — Complete
- **Enterprise Vector Platform** — vector database abstraction and similarity search
- `VectorStoreProvider` ABC: `add`, `add_batch`, `search`, `delete`, `delete_by_filter`, `count`, `clear`, `provider_name`
- `MemoryVectorStore` — in-memory with cosine similarity, thread-safe, supporting exact-match, list, range (`$gt`/`$gte`/`$lt`/`$lte`), `$ne`, `$in`, `$and`, `$or` filter operators
- `ChromaDBVectorStore` — ChromaDB-backed with cosine distance → similarity conversion, metadata filtering, persistent client (optional dep via try/except)
- `VectorService` facade: `index_vector`, `index_batch`, `search_by_vector`, `delete`, `delete_by_filter`, `get_stats`, `clear`
- DI: `get_vector_service()` / `set_vector_service()` / `reset_vector_service()` — follows same singleton pattern as cache, ratelimit, knowledge, embeddings
- 5 REST endpoints: `POST /ai/vector/search`, `POST /ai/vector/index`, `GET /ai/vector/stats`, `DELETE /ai/vector/{id}`, `DELETE /ai/vector/clear`
- 6 vector settings in AISettings: `VECTOR_ENABLED`, `VECTOR_DEFAULT_PROVIDER`, `VECTOR_STORE_PATH`, `VECTOR_COLLECTION_NAME`, `VECTOR_DEFAULT_TOP_K`, `VECTOR_MAX_TOP_K`
- No retrieval, no RAG, no chatbot integration — pure vector storage and similarity search
- 78 tests (exceptions, schemas, utils, memory store, service, DI, API)
- All 751 tests passing, no regressions

### Sprint 4.5 — Complete
- **Enterprise Retrieval Engine** — query → embed → search → rerank → return
- `RerankerProvider` ABC with `NoOpReranker`, `MockReranker` (score-based), `TimeReranker` (recency-based)
- `RetrievalPipeline` — orchestrates embed query → vector search → chunk retrieval → filter → rerank
- `RetrievalService` facade: `search`, `retrieve`, `assemble_context`, `rag_generate`
- `RAG Service` — context assembly with token budgeting + truncation, GatewayPipeline integration for answer generation
- Integration: `EmbeddingService` (query embedding), `VectorService` (similarity search), `KnowledgeService` (chunk content via new `get_chunk` method)
- DI: `get_retrieval_service()` / `set_retrieval_service()` / `reset_retrieval_service()` — follows same singleton pattern
- 2 REST endpoints: `POST /ai/retrieval/search` (semantic search), `POST /ai/retrieval/rag` (retrieval-augmented generation)
- 6 retrieval settings in AISettings: `RETRIEVAL_ENABLED`, `RETRIEVAL_DEFAULT_TOP_K`, `RETRIEVAL_MAX_TOP_K`, `RETRIEVAL_DEFAULT_RERANKER`, `RETRIEVAL_MAX_CONTEXT_TOKENS`, `RETRIEVAL_ALLOW_RAG`
- Default RAG system message with context injection and citation instructions
- Context assembly with token estimation and automatic truncation at configurable max tokens
- No Medical RAG, no AI assistant — pure retrieval + RAG infrastructure
- 33 tests (exceptions, schemas, rerankers, service, pipeline, DI, API, knowledge integration)
- All 803 tests passing, no regressions

### Sprint 4.6 Volume 1 — Complete (Enterprise Medical Intelligence Platform)
- **Enterprise Medical Intelligence Platform** — query understanding, rewriting, retrieval orchestration, reasoning, citations, confidence scoring, safety validation, and structured responses
- 17 subdirectories under `app/ai/medical/` (api, citations, confidence, config, deps, exceptions, intent, interfaces, pipelines, reasoning, responses, rewriters, safety, schemas, services, utils, validators)
- 9 abstract interfaces: IntentDetectorABC, QueryRewriterABC, ContextOptimizerABC, MedicalPromptBuilderABC, MedicalReasonerABC, CitationEngineABC, ConfidenceEngineABC, SafetyValidatorABC, ResponseBuilderABC
- **IntentDetector** — rule-based detection of 10 intent types, 20 medical specialties, 5 urgency levels
- **QueryRewriter** — medical abbreviation expansion (30+), intent-specific query expansion, specialty context injection
- **CitationEngine** — builds structured CitationEntry list from retrieval results
- **ConfidenceEngine** — multi-dimensional confidence scoring (retrieval, evidence, generation, citation coverage)
- **SafetyValidator** — pattern-based detection: unsafe advice (10 patterns), hallucination indicators, contradiction detection
- **MedicalReasoner** — chain-of-thought building per intent type, differential consideration extraction
- **ResponseBuilder** — structured MedicalResponse assembly with formatted citation references
- **MedicalPipeline** — 10-stage orchestration (intent → rewrite → context → prompt → generate → citations → reason → confidence → safety → response)
- **MedicalService** — facade with `query()` and `search()`
- **MedicalSettings** — 11 configurable settings in MedicalSettings + AISettings
- DI: get/set/reset singleton pattern
- 2 REST endpoints: `POST /ai/medical/query`, `POST /ai/medical/search`
- 58 tests
- All 861 tests passing, no regressions

### Sprint 4.6 Volume 2 — Complete (Enterprise Medical Query Understanding Engine)
- **Enterprise Medical Query Understanding Engine** — transforms unstructured user questions into structured medical intelligence BEFORE retrieval/LLM
- 9 new submodules under `app/ai/medical/`: `intent/` (restructured with interfaces, services, classifiers, schemas, validators, utils, deps), `rewrite/`, `entities/`, `specialty/`, `urgency/`, `audience/`, `language/`, `context/`, `taxonomy/`
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
- 12 exceptions: `ClinicalSafetyError` hierarchy
- 7 enums: `HallucinationType`, `SupportLevel`, `RiskLevel`, `EmergencyType`, `PHIType`, `DisclaimerType`, `ApprovalDecision`
- 18 Pydantic schemas: `HallucinationReport`, `UnsupportedClaimReport`, `ClinicalRiskReport`, `EmergencyReport`, `PHIValidationReport`, `DisclaimerResult`, `ComplianceReport`, `ApprovalResult`, `SafetyState`, `PipelineResult`, `SafetyServiceResult`, etc.
- 8 ABC interfaces: `HallucinationDetector`, `UnsupportedClaimDetector`, `ClinicalRiskEngine`, `EmergencyDetector`, `PHIValidator`, `DisclaimerEngine`, `ComplianceValidator`, `SafetyApprovalEngine`
- 8 engine implementations:
  - **HallucinationDetectorService** — detects 7 hallucination types (FABRICATED_MEDICATION, FABRICATED_DISEASE, FABRICATED_CITATION, FABRICATED_GUIDELINE, FABRICATED_STATISTIC, FABRICATED_RECOMMENDATION, UNSUPPORTED_CLAIM) using built-in medication/disease lists and regex patterns; NO LLM used
  - **UnsupportedClaimDetectorService** — classifies claims as FULLY_SUPPORTED/PARTIALLY_SUPPORTED/UNSUPPORTED/CONTRADICTORY against evidence
  - **ClinicalRiskEngineService** — weighted scoring (hallucination 30%, unsupported 25%, topic sensitivity 20%, emergency 25%) → LOW/MODERATE/HIGH/CRITICAL
  - **EmergencyDetectorService** — regex patterns for 7 emergency types (chest pain, stroke, severe bleeding, suicidal ideation, anaphylaxis, respiratory distress, loss of consciousness)
  - **PHIValidatorService** — regex detection for 10 PHI types (SSN, email, phone, Aadhaar, passport, credit card, medical record number, insurance ID, DOB, patient name)
  - **DisclaimerEngineService** — 7 built-in disclaimers (GENERAL_MEDICAL, EMERGENCY, MEDICATION, MENTAL_HEALTH, PREGNANCY, PEDIATRIC, CLINICAL_UNCERTAINTY), context-aware selection
  - **ComplianceValidatorService** — 7 compliance checks (hallucination, unsupported, evidence threshold, disclaimer, prohibited terms, absolute guarantees, citation coverage)
  - **SafetyApprovalEngineService** — 4-level decision (APPROVED/APPROVED_WITH_WARNINGS/ESCALATE/REJECT) with deterministic business rules
- **ClinicalSafetyPipeline** — 8-stage sequential pipeline: hallucination → emergency → unsupported → risk → PHI → disclaimer → compliance → approval; parallel hallucination+emergency execution
- **ClinicalSafetyService** — facade with `validate()`, `detect_hallucinations()`, `detect_unsupported_claims()`, `assess_risk()`, `detect_emergency()`, `validate_phi()`, `select_disclaimer()`, `validate_compliance()`, `get_approval()`
- DI: `get_`/`set_`/`reset_` for all 8 engines + pipeline + service — follows same singleton pattern as cache, ratelimit, knowledge, embeddings, vector, retrieval, medical, evidence
- 10 REST endpoints: `GET /ai/safety/health`, `POST /ai/safety/validate`, `POST /ai/safety/hallucination`, `POST /ai/safety/unsupported`, `POST /ai/safety/risk`, `POST /ai/safety/emergency`, `POST /ai/safety/phi`, `POST /ai/safety/disclaimer`, `POST /ai/safety/compliance`, `POST /ai/safety/approval`
- **Business Rules**: Every response must pass safety validation; hallucinated content never approved; emergencies bypass normal flow; risk classifications deterministic; approval decisions auditable; safety reports immutable
- **Validation**: Missing evidence, invalid responses, missing citations, invalid disclaimer config, unsupported risk categories, empty approval reports — all return structured errors
- Independent of Retrieval and Evidence modules — pure rule-based safety validation
- 324 tests, all passing
- Total test count: 324 clinical safety tests + 308 evidence tests + 938 prior = 1,570 tests
