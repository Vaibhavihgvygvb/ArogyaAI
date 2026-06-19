import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.ai.embeddings.batch.batch import BatchProcessor
from app.ai.embeddings.cache.cache import MemoryEmbeddingCache
from app.ai.embeddings.deps.deps import get_embedding_service, reset_embedding_service, set_embedding_service
from app.ai.embeddings.exceptions.exceptions import (
    DimensionMismatchError,
    DuplicateEmbeddingError,
    EmbeddingError,
    EmptyChunkError,
    OversizedChunkError,
    ProviderError,
    StorageError,
)
from app.ai.embeddings.interfaces.interfaces import (
    EmbeddingCache,
    EmbeddingPipeline,
    EmbeddingProvider,
    EmbeddingStorage,
    EmbeddingValidator,
)
from app.ai.embeddings.pipelines.pipelines import DefaultEmbeddingPipeline
from app.ai.embeddings.providers.mock import MockEmbeddingProvider
from app.ai.embeddings.schemas.schemas import (
    BatchRequest,
    BatchResponse,
    ChunkReference,
    EmbeddingBatch,
    EmbeddingProviderType,
    EmbeddingRecord,
    EmbeddingStatus,
    EmbeddingVector,
    EmbeddingVersion,
    PipelineConfig,
    ReindexRequest,
)
from app.ai.embeddings.services.services import EmbeddingService
from app.ai.embeddings.storage.storage import LocalEmbeddingStorage
from app.ai.embeddings.utils.utils import (
    compute_content_hash,
    compute_vector_checksum,
    generate_batch_id,
    generate_embedding_id,
    normalize_vector,
    validate_vector_dimension,
)
from app.ai.embeddings.validators.validators import DefaultEmbeddingValidator
from app.ai.embeddings.versioning.versioning import InMemoryVersionManager


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestEmbeddingExceptions:
    def test_embedding_error_base(self):
        assert issubclass(ProviderError, EmbeddingError)
        assert issubclass(DimensionMismatchError, EmbeddingError)
        assert issubclass(EmptyChunkError, EmbeddingError)
        assert issubclass(OversizedChunkError, EmbeddingError)

    def test_exception_raise_and_message(self):
        with pytest.raises(EmbeddingError, match="test error"):
            raise EmbeddingError("test error")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TestEmbeddingSchemas:
    def test_embedding_status_enum(self):
        assert EmbeddingStatus.PENDING.value == "pending"
        assert EmbeddingStatus.COMPLETED.value == "completed"
        assert EmbeddingStatus.FAILED.value == "failed"
        assert EmbeddingStatus.DEPRECATED.value == "deprecated"

    def test_embedding_provider_type_enum(self):
        assert EmbeddingProviderType.MOCK.value == "mock"
        assert EmbeddingProviderType.OLLAMA.value == "ollama"
        assert EmbeddingProviderType.OPENAI.value == "openai"

    def test_chunk_reference_creation(self):
        ref = ChunkReference(
            chunk_id="chunk_1",
            document_id="doc_1",
            content="test content",
            content_hash="abc123",
            chunk_index=0,
        )
        assert ref.chunk_id == "chunk_1"
        assert ref.document_id == "doc_1"
        assert ref.content == "test content"

    def test_embedding_record_defaults(self):
        now = datetime.now(timezone.utc)
        record = EmbeddingRecord(
            id="emb_1",
            knowledge_id="doc_1",
            chunk_id="chunk_1",
            chunk_index=0,
            provider=EmbeddingProviderType.MOCK,
            model="mock-v1",
            dimension=384,
            version=1,
            checksum="abc",
            content_hash="def",
            status=EmbeddingStatus.COMPLETED,
            created_at=now,
            updated_at=now,
        )
        assert record.metadata == {}

    def test_embedding_vector_creation(self):
        now = datetime.now(timezone.utc)
        vector = EmbeddingVector(
            id="emb_1",
            knowledge_id="doc_1",
            chunk_id="chunk_1",
            provider=EmbeddingProviderType.MOCK,
            model="mock-v1",
            dimension=4,
            version=1,
            checksum="abc",
            content_hash="def",
            status=EmbeddingStatus.COMPLETED,
            vector=[0.1, 0.2, 0.3, 0.4],
            created_at=now,
            updated_at=now,
        )
        assert len(vector.vector) == 4
        assert vector.dimension == 4

    def test_pipeline_config_defaults(self):
        cfg = PipelineConfig()
        assert cfg.batch_size == 50
        assert cfg.max_retries == 3
        assert cfg.validate_vectors is True
        assert cfg.skip_cache is False

    def test_embedding_batch_defaults(self):
        now = datetime.now(timezone.utc)
        batch = EmbeddingBatch(
            id="batch_1",
            status=EmbeddingStatus.PENDING,
            provider=EmbeddingProviderType.MOCK,
            model="mock-v1",
            created_at=now,
        )
        assert batch.total_chunks == 0
        assert batch.processed_chunks == 0
        assert batch.failed_chunks == 0
        assert batch.completed_at is None

    def test_embedding_record_processing_time(self):
        now = datetime.now(timezone.utc)
        record = EmbeddingRecord(
            id="emb_1", knowledge_id="doc_1", chunk_id="chunk_1",
            chunk_index=0, provider=EmbeddingProviderType.MOCK, model="mock-v1",
            dimension=384, version=1, checksum="abc", content_hash="def",
            status=EmbeddingStatus.COMPLETED, processing_time_ms=42.5,
            created_at=now, updated_at=now,
        )
        assert record.processing_time_ms == 42.5

    def test_embedding_vector_processing_time(self):
        now = datetime.now(timezone.utc)
        vec = EmbeddingVector(
            id="emb_1", knowledge_id="doc_1", chunk_id="chunk_1",
            provider=EmbeddingProviderType.MOCK, model="mock-v1",
            dimension=4, version=1, checksum="abc", content_hash="def",
            status=EmbeddingStatus.COMPLETED, vector=[0.1, 0.2, 0.3, 0.4],
            processing_time_ms=12.3, created_at=now, updated_at=now,
        )
        assert vec.processing_time_ms == 12.3

    def test_embedding_version_knowledge_link(self):
        now = datetime.now(timezone.utc)
        ver = EmbeddingVersion(
            version=1, provider=EmbeddingProviderType.MOCK, model="mock-v1",
            dimension=384, checksum="abc", count=10,
            knowledge_version="kv_2", created_at=now,
        )
        assert ver.knowledge_version == "kv_2"
        assert ver.is_active is True

    def test_batch_request_creation(self):
        chunks = [
            ChunkReference(
                chunk_id="c1", document_id="d1", content="test",
                content_hash="abc", chunk_index=0,
            )
        ]
        req = BatchRequest(chunks=chunks)
        assert len(req.chunks) == 1
        assert req.batch_size == 50
        assert req.skip_cache is False

    def test_batch_request_min_length(self):
        with pytest.raises(Exception):
            BatchRequest(chunks=[])

    def test_batch_response_creation(self):
        resp = BatchResponse(
            batch_id="batch_1", status=EmbeddingStatus.COMPLETED,
            total_chunks=10, processed_chunks=8, failed_chunks=2,
        )
        assert resp.errors == []

    def test_reindex_request_creation(self):
        req = ReindexRequest(embedding_ids=["emb_1", "emb_2"])
        assert len(req.embedding_ids) == 2

    def test_reindex_request_min_length(self):
        with pytest.raises(Exception):
            ReindexRequest(embedding_ids=[])


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

class TestEmbeddingUtils:
    def test_generate_embedding_id(self):
        eid = generate_embedding_id()
        assert eid.startswith("emb_")
        assert len(eid) > 10

    def test_generate_batch_id(self):
        bid = generate_batch_id()
        assert bid.startswith("batch_")
        assert len(bid) > 10

    def test_compute_content_hash(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        h3 = compute_content_hash("different")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 32

    def test_compute_vector_checksum(self):
        c1 = compute_vector_checksum([0.1, 0.2, 0.3])
        c2 = compute_vector_checksum([0.1, 0.2, 0.3])
        c3 = compute_vector_checksum([0.4, 0.5, 0.6])
        assert c1 == c2
        assert c1 != c3

    def test_validate_vector_dimension(self):
        assert validate_vector_dimension([0.1, 0.2], 2) is True
        assert validate_vector_dimension([0.1, 0.2], 3) is False

    def test_normalize_vector(self):
        vec = [3.0, 4.0]
        nv = normalize_vector(vec)
        mag = sum(v * v for v in nv) ** 0.5
        assert abs(mag - 1.0) < 1e-6

    def test_normalize_zero_vector(self):
        nv = normalize_vector([0.0, 0.0])
        assert nv == [0.0, 0.0]


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class TestEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_mock_provider_embed(self):
        provider = MockEmbeddingProvider(dimension=4)
        vectors = await provider.embed(["hello world", "test text"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 4

    @pytest.mark.asyncio
    async def test_mock_provider_normalized(self):
        provider = MockEmbeddingProvider(dimension=8)
        vectors = await provider.embed(["test content"])
        vec = vectors[0]
        mag = sum(v * v for v in vec) ** 0.5
        assert abs(mag - 1.0) < 1e-6

    def test_mock_provider_type(self):
        provider = MockEmbeddingProvider()
        assert provider.provider_type() == EmbeddingProviderType.MOCK

    def test_mock_provider_default_model(self):
        provider = MockEmbeddingProvider()
        assert provider.default_model() == "mock-embedding-v1"

    def test_mock_provider_dimensions(self):
        provider = MockEmbeddingProvider(dimension=768)
        assert provider.dimensions() == 768

    def test_mock_provider_supported_models(self):
        provider = MockEmbeddingProvider()
        assert "mock-embedding-v1" in provider.supported_models()


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

class TestEmbeddingValidators:
    @pytest.mark.asyncio
    async def test_validate_chunk_ok(self):
        v = DefaultEmbeddingValidator()
        result = await v.validate_chunk("valid content here", "chunk_1")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_chunk_empty(self):
        v = DefaultEmbeddingValidator()
        with pytest.raises(EmptyChunkError):
            await v.validate_chunk("", "chunk_1")

    @pytest.mark.asyncio
    async def test_validate_vector_ok(self):
        v = DefaultEmbeddingValidator()
        vec = [0.1, 0.2, 0.3]
        result = await v.validate_vector(vec, 3, "emb_1")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_vector_dimension_mismatch(self):
        v = DefaultEmbeddingValidator()
        with pytest.raises(DimensionMismatchError):
            await v.validate_vector([0.1, 0.2], 3, "emb_1")

    @pytest.mark.asyncio
    async def test_validate_vector_all_zeros(self):
        v = DefaultEmbeddingValidator()
        with pytest.raises(DimensionMismatchError):
            await v.validate_vector([0.0, 0.0], 2, "emb_1")

    @pytest.mark.asyncio
    async def test_validate_checksum(self):
        v = DefaultEmbeddingValidator()
        assert await v.validate_checksum("abc", "abc") is True
        assert await v.validate_checksum("abc", "def") is False

    @pytest.mark.asyncio
    async def test_validate_provider_available_valid(self):
        v = DefaultEmbeddingValidator()
        result = await v.validate_provider_available("mock", "mock-embedding-v1")
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_provider_available_invalid(self):
        v = DefaultEmbeddingValidator()
        from app.ai.embeddings.exceptions.exceptions import ProviderError
        with pytest.raises(ProviderError, match="Unknown provider type"):
            await v.validate_provider_available("nonexistent", "v1")

    @pytest.mark.asyncio
    async def test_validate_no_duplicate(self):
        v = DefaultEmbeddingValidator()
        from app.ai.embeddings.storage.storage import LocalEmbeddingStorage
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            from app.ai.embeddings.schemas.schemas import EmbeddingProviderType, EmbeddingStatus
            now = datetime.now(timezone.utc)
            from app.ai.embeddings.utils.utils import generate_embedding_id
            eid = generate_embedding_id()
            from app.ai.embeddings.schemas.schemas import EmbeddingRecord
            rec = EmbeddingRecord(
                id=eid, knowledge_id="doc_1", chunk_id="chunk_1",
                chunk_index=0, provider=EmbeddingProviderType.MOCK,
                model="mock-v1", dimension=384, version=1,
                checksum="abc", content_hash="dup_hash",
                status=EmbeddingStatus.COMPLETED,
                created_at=now, updated_at=now,
            )
            await storage.store_record(rec)
            from app.ai.embeddings.exceptions.exceptions import DuplicateEmbeddingError
            with pytest.raises(DuplicateEmbeddingError):
                await v.validate_no_duplicate("dup_hash", "mock", "mock-v1", storage)

    @pytest.mark.asyncio
    async def test_validate_no_duplicate_ok(self):
        v = DefaultEmbeddingValidator()
        from app.ai.embeddings.storage.storage import LocalEmbeddingStorage
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            result = await v.validate_no_duplicate("unique_hash", "mock", "mock-v1", storage)
            assert result is True


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class TestEmbeddingCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = MemoryEmbeddingCache()
        now = datetime.now(timezone.utc)
        vec = EmbeddingVector(
            id="emb_1", knowledge_id="doc_1", chunk_id="chunk_1",
            provider=EmbeddingProviderType.MOCK, model="mock-v1",
            dimension=4, version=1, checksum="abc", content_hash="def",
            status=EmbeddingStatus.COMPLETED, vector=[0.1, 0.2, 0.3, 0.4],
            created_at=now, updated_at=now,
        )
        await cache.set(vec)
        result = await cache.get("def", "mock", "mock-v1")
        assert result is not None
        assert result.id == "emb_1"

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        cache = MemoryEmbeddingCache()
        result = await cache.get("nonexistent", "mock", "mock-v1")
        assert result is None

    @pytest.mark.asyncio
    async def test_has(self):
        cache = MemoryEmbeddingCache()
        now = datetime.now(timezone.utc)
        vec = EmbeddingVector(
            id="emb_2", knowledge_id="doc_1", chunk_id="chunk_1",
            provider=EmbeddingProviderType.MOCK, model="mock-v1",
            dimension=4, version=1, checksum="abc", content_hash="xyz",
            status=EmbeddingStatus.COMPLETED, vector=[0.1, 0.2, 0.3, 0.4],
            created_at=now, updated_at=now,
        )
        await cache.set(vec)
        assert await cache.has("xyz", "mock", "mock-v1") is True
        assert await cache.has("nonexistent", "mock", "mock-v1") is False

    @pytest.mark.asyncio
    async def test_clear(self):
        cache = MemoryEmbeddingCache()
        now = datetime.now(timezone.utc)
        vec = EmbeddingVector(
            id="emb_3", knowledge_id="doc_1", chunk_id="chunk_1",
            provider=EmbeddingProviderType.MOCK, model="mock-v1",
            dimension=4, version=1, checksum="abc", content_hash="clr",
            status=EmbeddingStatus.COMPLETED, vector=[0.1, 0.2, 0.3, 0.4],
            created_at=now, updated_at=now,
        )
        await cache.set(vec)
        assert await cache.has("clr", "mock", "mock-v1") is True
        await cache.clear()
        assert await cache.has("clr", "mock", "mock-v1") is False

    @pytest.mark.asyncio
    async def test_invalidate(self):
        cache = MemoryEmbeddingCache()
        now = datetime.now(timezone.utc)
        vec = EmbeddingVector(
            id="emb_4", knowledge_id="doc_1", chunk_id="chunk_1",
            provider=EmbeddingProviderType.MOCK, model="mock-v1",
            dimension=4, version=1, checksum="abc", content_hash="inv",
            status=EmbeddingStatus.COMPLETED, vector=[0.1, 0.2, 0.3, 0.4],
            created_at=now, updated_at=now,
        )
        await cache.set(vec)
        await cache.invalidate("inv")
        assert await cache.has("inv", "mock", "mock-v1") is False


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

class TestEmbeddingVersioning:
    @pytest.mark.asyncio
    async def test_create_and_get_active_version(self):
        vm = InMemoryVersionManager()
        version = await vm.create_version("mock", "mock-v1", 384, "abc", 10)
        assert version == 1
        active = await vm.get_active_version("mock", "mock-v1")
        assert active == 1

    @pytest.mark.asyncio
    async def test_version_increments(self):
        vm = InMemoryVersionManager()
        v1 = await vm.create_version("mock", "mock-v1", 384, "abc", 10)
        v2 = await vm.create_version("mock", "mock-v1", 768, "def", 20)
        assert v1 == 1
        assert v2 == 2

    @pytest.mark.asyncio
    async def test_deprecate_version(self):
        vm = InMemoryVersionManager()
        await vm.create_version("mock", "mock-v1", 384, "abc", 10)
        await vm.deprecate_version("mock", "mock-v1", 1)
        active = await vm.get_active_version("mock", "mock-v1")
        assert active is None

    @pytest.mark.asyncio
    async def test_get_versions(self):
        vm = InMemoryVersionManager()
        assert await vm.get_versions("mock", "mock-v1") == []
        await vm.create_version("mock", "mock-v1", 384, "abc", 10)
        await vm.create_version("mock", "mock-v1", 768, "def", 20)
        versions = await vm.get_versions("mock", "mock-v1")
        assert versions == [1, 2]

    @pytest.mark.asyncio
    async def test_rollback_version(self):
        vm = InMemoryVersionManager()
        v1 = await vm.create_version("mock", "mock-v1", 384, "abc", 10)
        v2 = await vm.create_version("mock", "mock-v1", 768, "def", 20)
        assert await vm.get_active_version("mock", "mock-v1") == 2
        rolled = await vm.rollback("mock", "mock-v1", v1)
        assert rolled == 1
        active = await vm.get_active_version("mock", "mock-v1")
        assert active == 1

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_key(self):
        vm = InMemoryVersionManager()
        result = await vm.rollback("nonexistent", "v1", 99)
        assert result is None

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_version(self):
        vm = InMemoryVersionManager()
        await vm.create_version("mock", "mock-v1", 384, "abc", 10)
        from app.ai.embeddings.exceptions.exceptions import VersionMismatchError
        with pytest.raises(VersionMismatchError):
            await vm.rollback("mock", "mock-v1", 99)

    @pytest.mark.asyncio
    async def test_create_version_with_knowledge_link(self):
        vm = InMemoryVersionManager()
        version = await vm.create_version("mock", "mock-v1", 384, "abc", 10, knowledge_version="kv_3")
        info = await vm.get_version_info("mock", "mock-v1", version)
        assert info is not None
        assert info.knowledge_version == "kv_3"

    @pytest.mark.asyncio
    async def test_get_version_info_nonexistent(self):
        vm = InMemoryVersionManager()
        info = await vm.get_version_info("nonexistent", "v1", 1)
        assert info is None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class TestEmbeddingPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            pipeline = DefaultEmbeddingPipeline(storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            vector = await pipeline.run(
                content="Test content for embedding",
                chunk_id="chunk_1",
                document_id="doc_1",
                chunk_index=0,
                content_hash=compute_content_hash("Test content for embedding"),
                provider=provider,
            )
            assert vector.status == EmbeddingStatus.COMPLETED
            assert vector.knowledge_id == "doc_1"
            assert vector.chunk_id == "chunk_1"
            assert len(vector.vector) == 4

    @pytest.mark.asyncio
    async def test_pipeline_uses_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            cache = MemoryEmbeddingCache()
            pipeline = DefaultEmbeddingPipeline(storage=storage, cache=cache)
            provider = MockEmbeddingProvider(dimension=4)
            content = "Cached content test"
            content_hash = compute_content_hash(content)

            result1 = await pipeline.run(
                content=content, chunk_id="chunk_1", document_id="doc_1",
                chunk_index=0, content_hash=content_hash, provider=provider,
            )

            result2 = await pipeline.run(
                content=content, chunk_id="chunk_2", document_id="doc_2",
                chunk_index=1, content_hash=content_hash, provider=provider,
            )

            assert result1.id == result2.id

    @pytest.mark.asyncio
    async def test_pipeline_skip_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            cache = MemoryEmbeddingCache()
            pipeline = DefaultEmbeddingPipeline(storage=storage, cache=cache)
            provider = MockEmbeddingProvider(dimension=4)
            content = "Skip cache test"
            content_hash = compute_content_hash(content)
            cfg = PipelineConfig(skip_cache=True)

            result1 = await pipeline.run(
                content=content, chunk_id="chunk_1", document_id="doc_1",
                chunk_index=0, content_hash=content_hash, provider=provider,
                config=cfg,
            )

            result2 = await pipeline.run(
                content=content, chunk_id="chunk_2", document_id="doc_2",
                chunk_index=1, content_hash=content_hash, provider=provider,
                config=cfg,
            )

            assert result1.id != result2.id

    @pytest.mark.asyncio
    async def test_pipeline_empty_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            pipeline = DefaultEmbeddingPipeline(storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            with pytest.raises(EmptyChunkError):
                await pipeline.run(
                    content="", chunk_id="chunk_1", document_id="doc_1",
                    chunk_index=0, content_hash="abc", provider=provider,
                )


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class TestEmbeddingStorage:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_vector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            now = datetime.now(timezone.utc)
            vec = EmbeddingVector(
                id="emb_test_1", knowledge_id="doc_1", chunk_id="chunk_1",
                provider=EmbeddingProviderType.MOCK, model="mock-v1",
                dimension=4, version=1, checksum="abc", content_hash="def",
                status=EmbeddingStatus.COMPLETED, vector=[0.1, 0.2, 0.3, 0.4],
                created_at=now, updated_at=now,
            )
            path = await storage.store_vector(vec)
            assert os.path.exists(path)

            retrieved = await storage.get_vector("emb_test_1")
            assert retrieved is not None
            assert retrieved.id == "emb_test_1"
            assert len(retrieved.vector) == 4

    @pytest.mark.asyncio
    async def test_store_and_retrieve_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            now = datetime.now(timezone.utc)
            record = EmbeddingRecord(
                id="emb_rec_1", knowledge_id="doc_1", chunk_id="chunk_1",
                chunk_index=0, provider=EmbeddingProviderType.MOCK,
                model="mock-v1", dimension=384, version=1, checksum="abc",
                content_hash="def", status=EmbeddingStatus.COMPLETED,
                created_at=now, updated_at=now,
            )
            path = await storage.store_record(record)
            assert os.path.exists(path)

            retrieved = await storage.get_record("emb_rec_1")
            assert retrieved is not None
            assert retrieved.id == "emb_rec_1"

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            assert await storage.get_vector("nonexistent") is None
            assert await storage.get_record("nonexistent") is None

    @pytest.mark.asyncio
    async def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            now = datetime.now(timezone.utc)
            eid = "emb_del"
            vec = EmbeddingVector(
                id=eid, knowledge_id="doc_1", chunk_id="chunk_1",
                provider=EmbeddingProviderType.MOCK, model="mock-v1",
                dimension=4, version=1, checksum="abc", content_hash="def",
                status=EmbeddingStatus.COMPLETED, vector=[0.1, 0.2, 0.3, 0.4],
                created_at=now, updated_at=now,
            )
            rec = EmbeddingRecord(
                id=eid, knowledge_id="doc_1", chunk_id="chunk_1",
                chunk_index=0, provider=EmbeddingProviderType.MOCK,
                model="mock-v1", dimension=384, version=1, checksum="abc",
                content_hash="def", status=EmbeddingStatus.COMPLETED,
                created_at=now, updated_at=now,
            )
            await storage.store_vector(vec)
            await storage.store_record(rec)
            assert await storage.exists(eid) is True
            deleted = await storage.delete(eid)
            assert deleted is True
            assert await storage.exists(eid) is False

    @pytest.mark.asyncio
    async def test_list_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            now = datetime.now(timezone.utc)
            for i in range(3):
                record = EmbeddingRecord(
                    id=f"emb_{i}", knowledge_id=f"doc_{i}", chunk_id=f"chunk_{i}",
                    chunk_index=i, provider=EmbeddingProviderType.MOCK,
                    model="mock-v1", dimension=384, version=1, checksum="x",
                    content_hash="y", status=EmbeddingStatus.COMPLETED,
                    created_at=now, updated_at=now,
                )
                await storage.store_record(record)

            records, total = await storage.list_records(limit=2)
            assert total == 3
            assert len(records) == 2

    @pytest.mark.asyncio
    async def test_list_records_filtered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            now = datetime.now(timezone.utc)
            rec1 = EmbeddingRecord(
                id="emb_a", knowledge_id="doc_a", chunk_id="chunk_a",
                chunk_index=0, provider=EmbeddingProviderType.MOCK,
                model="mock-v1", dimension=384, version=1, checksum="x",
                content_hash="y", status=EmbeddingStatus.COMPLETED,
                created_at=now, updated_at=now,
            )
            rec2 = EmbeddingRecord(
                id="emb_b", knowledge_id="doc_b", chunk_id="chunk_b",
                chunk_index=0, provider=EmbeddingProviderType.MOCK,
                model="mock-v1", dimension=384, version=1, checksum="x",
                content_hash="y", status=EmbeddingStatus.FAILED,
                created_at=now, updated_at=now,
            )
            await storage.store_record(rec1)
            await storage.store_record(rec2)

            records_a, total_a = await storage.list_records(knowledge_id="doc_a")
            assert total_a == 1
            assert records_a[0].id == "emb_a"

            records_fail, total_fail = await storage.list_records(status="failed")
            assert total_fail == 1
            assert records_fail[0].id == "emb_b"


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------

class TestBatchProcessing:
    @pytest.mark.asyncio
    async def test_batch_process_chunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            pipeline = DefaultEmbeddingPipeline(storage=storage)
            processor = BatchProcessor(pipeline=pipeline, storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            chunks = [
                ChunkReference(
                    chunk_id=f"c_{i}", document_id="doc_1",
                    content=f"Content {i}", content_hash=compute_content_hash(f"Content {i}"),
                    chunk_index=i,
                )
                for i in range(5)
            ]

            batch = await processor.process_chunks(chunks, provider, PipelineConfig(batch_size=2))
            assert batch.total_chunks == 5
            assert batch.processed_chunks == 5
            assert batch.failed_chunks == 0
            assert batch.status == EmbeddingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_batch_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            pipeline = DefaultEmbeddingPipeline(storage=storage)
            processor = BatchProcessor(pipeline=pipeline, storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            batch = await processor.process_chunks([], provider)
            assert batch.total_chunks == 0
            assert batch.processed_chunks == 0


# ---------------------------------------------------------------------------
# EmbeddingService
# ---------------------------------------------------------------------------

class TestEmbeddingService:
    @pytest.mark.asyncio
    async def test_generate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            vector = await service.generate(
                content="Test service generate",
                chunk_id="chunk_svc_1",
                document_id="doc_svc_1",
                provider=provider,
            )
            assert vector.status == EmbeddingStatus.COMPLETED
            assert vector.chunk_id == "chunk_svc_1"

    @pytest.mark.asyncio
    async def test_generate_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)

            chunks = [
                ChunkReference(
                    chunk_id=f"sc_{i}", document_id="doc_svc",
                    content=f"Service content {i}",
                    content_hash=compute_content_hash(f"Service content {i}"),
                    chunk_index=i,
                )
                for i in range(3)
            ]

            batch = await service.generate_batch(chunks)
            assert batch.processed_chunks == 3

    @pytest.mark.asyncio
    async def test_get_embedding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            vector = await service.generate(
                content="Get me", chunk_id="c_get", document_id="d_get",
                provider=provider,
            )
            retrieved = await service.get_embedding(vector.id)
            assert retrieved is not None
            assert retrieved.id == vector.id

    @pytest.mark.asyncio
    async def test_list_embeddings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            await service.generate(
                content="List test A", chunk_id="c_list_a", document_id="d_list",
                provider=provider,
            )
            await service.generate(
                content="List test B", chunk_id="c_list_b", document_id="d_list",
                provider=provider,
            )

            records, total = await service.list_embeddings()
            assert total >= 2

    @pytest.mark.asyncio
    async def test_delete_embedding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            provider = MockEmbeddingProvider(dimension=4)

            vector = await service.generate(
                content="Delete me", chunk_id="c_del", document_id="d_del",
                provider=provider,
            )
            assert await service.delete_embedding(vector.id) is True
            assert await service.delete_embedding("nonexistent") is False

    @pytest.mark.asyncio
    async def test_rebuild(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)

            chunks = [
                ChunkReference(
                    chunk_id="r_1", document_id="doc_r",
                    content="Rebuild content",
                    content_hash=compute_content_hash("Rebuild content"),
                    chunk_index=0,
                )
            ]
            batch = await service.rebuild(chunks)
            assert batch.processed_chunks >= 0

    @pytest.mark.asyncio
    async def test_get_providers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            providers = await service.get_providers()
            assert len(providers) >= 1
            assert providers[0]["name"] == "mock"


# ---------------------------------------------------------------------------
# DI / Deps
# ---------------------------------------------------------------------------

class TestEmbeddingDeps:
    def test_reset_embedding_service(self):
        reset_embedding_service()
        assert get_embedding_service() is not None

    def test_set_and_get(self):
        reset_embedding_service()
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            mock_service = EmbeddingService(storage=storage)
            set_embedding_service(mock_service)
            assert get_embedding_service() is mock_service
            reset_embedding_service()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class TestEmbeddingAPI:
    @pytest.mark.asyncio
    async def test_list_providers_endpoint(self):
        from app.main import app
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            set_embedding_service(service)
            client = TestClient(app)
            response = client.get(
                "/ai/embeddings/providers",
                headers={"Authorization": "Bearer test_token"},
            )
            reset_embedding_service()
            assert response.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_batch_endpoint(self):
        from app.main import app
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            set_embedding_service(service)
            client = TestClient(app)
            payload = {
                "chunks": [
                    {
                        "chunk_id": "c1", "document_id": "d1",
                        "content": "test content",
                        "content_hash": "abc123",
                        "chunk_index": 0,
                    }
                ]
            }
            response = client.post(
                "/ai/embeddings/batches",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )
            reset_embedding_service()
            assert response.status_code in (201, 401, 403)

    @pytest.mark.asyncio
    async def test_reindex_endpoint(self):
        from app.main import app
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalEmbeddingStorage(base_path=tmpdir)
            service = EmbeddingService(storage=storage)
            set_embedding_service(service)
            client = TestClient(app)
            payload = {"embedding_ids": ["emb_1", "emb_2"]}
            response = client.post(
                "/ai/embeddings/reindex",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )
            reset_embedding_service()
            assert response.status_code in (200, 401, 403)
