import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.ai.embeddings.schemas.schemas import EmbeddingStatus, EmbeddingVector
from app.ai.knowledge.schemas.schemas import ChunkMetadata, DocumentChunk
from app.ai.retrieval.deps.deps import get_retrieval_service, reset_retrieval_service, set_retrieval_service
from app.ai.retrieval.exceptions.exceptions import (
    ChunkNotFoundError,
    EmbeddingQueryError,
    InvalidQueryError,
    RetrievalError,
    RAGGenerationError,
    RerankerError,
)
from app.ai.retrieval.interfaces.interfaces import RerankerProvider
from app.ai.retrieval.rerankers.rerankers import MockReranker, NoOpReranker, TimeReranker
from app.ai.retrieval.schemas.schemas import (
    ContextAssembly,
    RAGRequest,
    RAGResponse,
    RetrievalQuery,
    RetrievalResult,
    RetrievalResponse,
    SearchRequest,
    SearchResponse,
)
from app.ai.retrieval.services.services import RetrievalService
from app.ai.vector.schemas.schemas import SearchResult as VectorSearchResult
from app.ai.vector.schemas.schemas import SearchResponse as VectorSearchResponse
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_mock_embedding_vector(vector: list[float] | None = None) -> EmbeddingVector:
    return EmbeddingVector(
        id="emb_test",
        knowledge_id="doc_test",
        chunk_id="chunk_test",
        provider="mock",
        model="mock-embedding-v1",
        dimension=384,
        version=1,
        checksum="abc123",
        content_hash="def456",
        status=EmbeddingStatus.COMPLETED,
        vector=vector or [0.1] * 384,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_mock_vector_search_results(count: int = 3) -> VectorSearchResponse:
    results = []
    for i in range(count):
        results.append(
            VectorSearchResult(
                embedding_id=f"emb_{i}",
                chunk_id=f"chunk_{i}",
                knowledge_id="doc_test",
                score=1.0 - (i * 0.1),
                metadata={"source": "test"},
                vector=[0.1] * 384 if i == 0 else None,
            )
        )
    return VectorSearchResponse(results=results, total=count, query_time_ms=5.0)


def make_mock_chunk(chunk_id: str, content: str) -> DocumentChunk:
    return DocumentChunk(
        id=chunk_id,
        content=content,
        metadata=ChunkMetadata(
            source_document="doc_test",
            chunk_index=0,
        ),
    )


@pytest.fixture
def mock_services():
    emb_mock = MagicMock()
    emb_mock.generate = AsyncMock(return_value=make_mock_embedding_vector())

    vec_mock = MagicMock()
    vec_mock.search_by_vector = AsyncMock(return_value=make_mock_vector_search_results(3))

    know_mock = MagicMock()
    know_mock.get_chunk = AsyncMock(side_effect=lambda document_id, chunk_id: make_mock_chunk(
        chunk_id, f"Content for {chunk_id} in document {document_id}"
    ))

    return emb_mock, vec_mock, know_mock


@pytest.fixture(autouse=True)
def setup_retrieval_service(mock_services):
    emb_mock, vec_mock, know_mock = mock_services
    reranker = MockReranker()
    service = RetrievalService(
        embedding_service=emb_mock,
        vector_service=vec_mock,
        knowledge_service=know_mock,
        reranker=reranker,
    )
    set_retrieval_service(service)
    yield
    reset_retrieval_service()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TestRetrievalExceptions:
    def test_retrieval_error_base(self):
        assert issubclass(EmbeddingQueryError, RetrievalError)
        assert issubclass(ChunkNotFoundError, RetrievalError)
        assert issubclass(RAGGenerationError, RetrievalError)
        assert issubclass(RerankerError, RetrievalError)
        assert issubclass(InvalidQueryError, RetrievalError)

    def test_exception_raise_and_message(self):
        with pytest.raises(RetrievalError, match="test error"):
            raise RetrievalError("test error")
        with pytest.raises(InvalidQueryError, match="invalid"):
            raise InvalidQueryError("invalid")
        with pytest.raises(ChunkNotFoundError, match="not found"):
            raise ChunkNotFoundError("not found")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TestRetrievalSchemas:
    def test_retrieval_result_defaults(self):
        r = RetrievalResult(chunk_id="c1", knowledge_id="d1")
        assert r.score == 0.0
        assert r.rank == 0
        assert r.metadata == {}
        assert r.content is None

    def test_retrieval_result_full(self):
        r = RetrievalResult(
            chunk_id="c1",
            knowledge_id="d1",
            document_id="d1",
            content="test content",
            score=0.95,
            metadata={"key": "val"},
            rank=1,
        )
        assert r.content == "test content"
        assert r.score == 0.95
        assert r.rank == 1

    def test_retrieval_query_defaults(self):
        q = RetrievalQuery(query="test query")
        assert q.top_k == 10
        assert q.filters is None
        assert q.min_score is None
        assert q.rerank is True

    def test_retrieval_query_validation(self):
        with pytest.raises(ValueError):
            RetrievalQuery(query="", top_k=10)

    def test_retrieval_response(self):
        results = [
            RetrievalResult(chunk_id="c1", knowledge_id="d1", content="c", score=0.9, rank=1),
        ]
        r = RetrievalResponse(results=results, total=1, query="test", query_time_ms=10.0)
        assert r.total == 1
        assert r.query_time_ms == 10.0

    def test_context_assembly(self):
        ca = ContextAssembly(context="test context", token_count=50, chunk_count=3)
        assert ca.context == "test context"
        assert not ca.truncated

    def test_search_request_defaults(self):
        r = SearchRequest(query="test")
        assert r.top_k == 10
        assert r.rerank is True
        assert r.include_chunks is True

    def test_rag_request_defaults(self):
        r = RAGRequest(query="test")
        assert r.top_k == 5
        assert r.stream is False
        assert r.max_context_tokens == 2048

    def test_rag_response_defaults(self):
        r = RAGResponse(answer="test answer")
        assert r.sources == []
        assert r.model == ""
        assert r.provider == ""
        assert r.retrieval_time_ms == 0.0


# ---------------------------------------------------------------------------
# Rerankers
# ---------------------------------------------------------------------------


class TestRerankers:
    @pytest.mark.asyncio
    async def test_noop_reranker_assigns_ranks(self):
        reranker = NoOpReranker()
        results = [
            RetrievalResult(chunk_id="c1", knowledge_id="d1", score=0.5, rank=0),
            RetrievalResult(chunk_id="c2", knowledge_id="d1", score=0.9, rank=0),
        ]
        ranked = await reranker.rerank("query", results)
        assert len(ranked) == 2
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    @pytest.mark.asyncio
    async def test_noop_reranker_respects_top_k(self):
        reranker = NoOpReranker()
        results = [
            RetrievalResult(chunk_id=f"c{i}", knowledge_id="d1", score=0.5, rank=0)
            for i in range(5)
        ]
        ranked = await reranker.rerank("query", results, top_k=3)
        assert len(ranked) == 3
        assert ranked[-1].rank == 3

    @pytest.mark.asyncio
    async def test_mock_reranker_sorts_by_score(self):
        reranker = MockReranker()
        results = [
            RetrievalResult(chunk_id="c1", knowledge_id="d1", score=0.3, rank=0),
            RetrievalResult(chunk_id="c2", knowledge_id="d1", score=0.9, rank=0),
            RetrievalResult(chunk_id="c3", knowledge_id="d1", score=0.6, rank=0),
        ]
        ranked = await reranker.rerank("query", results)
        assert [r.chunk_id for r in ranked] == ["c2", "c3", "c1"]
        assert [r.score for r in ranked] == [0.9, 0.6, 0.3]
        assert [r.rank for r in ranked] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_time_reranker(self):
        reranker = TimeReranker()
        results = [
            RetrievalResult(
                chunk_id="c1", knowledge_id="d1", score=0.5, rank=0,
                metadata={"created_at": "2024-01-01"},
            ),
            RetrievalResult(
                chunk_id="c2", knowledge_id="d1", score=0.5, rank=0,
                metadata={"created_at": "2024-06-01"},
            ),
        ]
        ranked = await reranker.rerank("query", results)
        assert ranked[0].chunk_id == "c2"
        assert ranked[1].chunk_id == "c1"


# ---------------------------------------------------------------------------
# RetrievalService
# ---------------------------------------------------------------------------


class TestRetrievalService:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        response = await service.search(SearchRequest(query="test query", top_k=3))
        assert isinstance(response, SearchResponse)
        assert len(response.results) == 3
        assert response.query == "test query"

    @pytest.mark.asyncio
    async def test_search_includes_chunk_content(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        response = await service.search(SearchRequest(query="test", include_chunks=True))
        for r in response.results:
            assert r.content is not None
            assert r.document_id is not None

    @pytest.mark.asyncio
    async def test_search_without_chunks(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        response = await service.search(SearchRequest(query="test", include_chunks=False))
        for r in response.results:
            assert r.content is None

    @pytest.mark.asyncio
    async def test_search_filters_by_min_score(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        response = await service.search(SearchRequest(query="test", min_score=0.95))
        filtered = [r for r in response.results if r.score >= 0.95]
        assert len(filtered) <= len(response.results)

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        vec_mock.search_by_vector = AsyncMock(return_value=make_mock_vector_search_results(2))
        response = await service.search(
            SearchRequest(query="test", filters={"source": "test"})
        )
        assert len(response.results) == 2

    @pytest.mark.asyncio
    async def test_assemble_context(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        ctx = await service.assemble_context(
            query="test query",
            top_k=3,
            max_tokens=500,
        )
        assert isinstance(ctx, ContextAssembly)
        assert ctx.chunk_count > 0
        assert len(ctx.context) > 0

    @pytest.mark.asyncio
    async def test_assemble_context_empty_results(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        vec_mock.search_by_vector = AsyncMock(
            return_value=VectorSearchResponse(results=[], total=0, query_time_ms=1.0)
        )
        ctx = await service.assemble_context(query="no results", top_k=3)
        assert ctx.chunk_count == 0
        assert ctx.context == ""

    @pytest.mark.asyncio
    async def test_handle_embedding_failure(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        emb_mock.generate = AsyncMock(
            return_value=make_mock_embedding_vector()
        )
        emb_mock.generate.side_effect = None

        class FailedVector:
            id = "emb_fail"
            knowledge_id = "doc_fail"
            chunk_id = "chunk_fail"
            provider = "mock"
            model = "mock-embedding-v1"
            dimension = 384
            version = 1
            checksum = "abc"
            content_hash = "def"
            status = EmbeddingStatus.FAILED
            vector = [0.0] * 384
            processing_time_ms = 0.0
            metadata = {}
            created_at = datetime.now(timezone.utc)
            updated_at = datetime.now(timezone.utc)

        emb_mock.generate = AsyncMock(return_value=FailedVector())
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        with pytest.raises(EmbeddingQueryError):
            await service.search(SearchRequest(query="fail"))


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


class TestRetrievalAPI:
    def test_search_endpoint_returns_200(self, client, doctor_token, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        reset_retrieval_service()
        set_retrieval_service(service)

        response = client.post(
            "/ai/retrieval/search",
            json={"query": "test query", "top_k": 3},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["query"] == "test query"

    def test_search_endpoint_requires_auth(self, client):
        response = client.post(
            "/ai/retrieval/search",
            json={"query": "test"},
        )
        assert response.status_code == 401

    def test_search_endpoint_422_on_empty_query(self, client, doctor_token):
        response = client.post(
            "/ai/retrieval/search",
            json={"query": ""},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 422

    def test_rag_endpoint_returns_200(self, client, doctor_token, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        reset_retrieval_service()
        set_retrieval_service(service)

        with patch("app.ai.gateway.deps.get_gateway") as mock_get_gateway:
            mock_gateway = AsyncMock()
            mock_gateway.execute = AsyncMock()
            mock_gateway.execute.return_value.content = "RAG answer"
            mock_gateway.execute.return_value.model = "mock-model"
            mock_gateway.execute.return_value.provider = "mock"
            mock_gateway.execute.return_value.usage = {"total_tokens": 50}
            mock_get_gateway.return_value = mock_gateway

            response = client.post(
                "/ai/retrieval/rag",
                json={"query": "test query", "top_k": 2},
                headers={"Authorization": f"Bearer {doctor_token}"},
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert "answer" in data
            assert data["answer"] == "RAG answer"
            assert "sources" in data
            assert "retrieval_time_ms" in data
            assert "generation_time_ms" in data

    def test_rag_endpoint_requires_auth(self, client):
        response = client.post(
            "/ai/retrieval/rag",
            json={"query": "test"},
        )
        assert response.status_code == 401

    def test_search_response_shape(self, client, doctor_token, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        reset_retrieval_service()
        set_retrieval_service(service)

        response = client.post(
            "/ai/retrieval/search",
            json={"query": "heart disease treatment", "top_k": 2},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert "total" in data
        assert "query" in data
        assert "query_time_ms" in data
        if data["results"]:
            r = data["results"][0]
            assert "chunk_id" in r
            assert "knowledge_id" in r
            assert "score" in r
            assert "rank" in r

    def test_rag_response_shape(self, client, doctor_token, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )
        reset_retrieval_service()
        set_retrieval_service(service)

        with patch("app.ai.gateway.deps.get_gateway") as mock_get_gateway:
            mock_gateway = AsyncMock()
            mock_gateway.execute = AsyncMock()
            mock_gateway.execute.return_value.content = "Answer about heart disease"
            mock_gateway.execute.return_value.model = "mock-model"
            mock_gateway.execute.return_value.provider = "mock"
            mock_gateway.execute.return_value.usage = {"total_tokens": 100}
            mock_get_gateway.return_value = mock_gateway

            response = client.post(
                "/ai/retrieval/rag",
                json={"query": "heart disease treatment"},
                headers={"Authorization": f"Bearer {doctor_token}"},
            )
            assert response.status_code == 200
            data = response.json()
            expected_keys = {"answer", "conversation_id", "sources", "model", "provider", "usage", "retrieval_time_ms", "generation_time_ms"}
            assert expected_keys.issubset(data.keys())
            assert isinstance(data["sources"], list)


# ---------------------------------------------------------------------------
# DI (Singleton pattern)
# ---------------------------------------------------------------------------


class TestRetrievalDI:
    def test_get_set_reset(self, mock_services):
        emb_mock, vec_mock, know_mock = mock_services
        service = RetrievalService(
            embedding_service=emb_mock,
            vector_service=vec_mock,
            knowledge_service=know_mock,
            reranker=MockReranker(),
        )

        reset_retrieval_service()
        set_retrieval_service(service)

        retrieved = get_retrieval_service()
        assert retrieved is service

        reset_retrieval_service()
        new_service = get_retrieval_service()
        assert new_service is not None
        assert isinstance(new_service, RetrievalService)
        assert new_service is not service

    def test_singleton_creates_default(self):
        reset_retrieval_service()
        service = get_retrieval_service()
        assert service is not None
        assert isinstance(service, RetrievalService)
        reset_retrieval_service()


# ---------------------------------------------------------------------------
# KnowledgeService get_chunk integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_knowledge_service_get_chunk():
    from app.ai.knowledge.schemas.schemas import (
        ChunkMetadata,
        DocumentChunk,
        DocumentFormat,
        DocumentMetadata,
        DocumentStatus,
        KnowledgeDocument,
    )
    from app.ai.knowledge.services.services import KnowledgeService
    from app.ai.knowledge.storage.storage import LocalFileStorage
    from app.ai.knowledge.catalog.catalog import KnowledgeCatalog

    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
        catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
        svc = KnowledgeService(storage=storage, catalog=catalog)

        chunk = DocumentChunk(
            id="chunk_1",
            content="test content",
            metadata=ChunkMetadata(source_document="doc_1", chunk_index=0),
        )
        doc = KnowledgeDocument(
            id="doc_1",
            filename="test.md",
            format=DocumentFormat.MD,
            size_bytes=100,
            checksum="abc",
            status=DocumentStatus.COMPLETED,
            chunks=[chunk],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await storage.store(doc)

        result = await svc.get_chunk("doc_1", "chunk_1")
        assert result is not None
        assert result.id == "chunk_1"
        assert result.content == "test content"

        missing = await svc.get_chunk("doc_1", "nonexistent")
        assert missing is None

        no_doc = await svc.get_chunk("no_doc", "chunk_1")
        assert no_doc is None
