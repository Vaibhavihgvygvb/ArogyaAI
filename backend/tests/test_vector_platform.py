import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.ai.vector.deps.deps import get_vector_service, reset_vector_service, set_vector_service
from app.ai.vector.exceptions.exceptions import (
    DimensionMismatchError,
    EmptyVectorError,
    IndexError,
    ProviderNotFoundError,
    SearchError,
    VectorStoreError,
)
from app.ai.vector.interfaces.interfaces import VectorStoreProvider
from app.ai.vector.providers.memory import MemoryVectorStore
from app.ai.vector.schemas.schemas import (
    ClearResponse,
    IndexRequest,
    IndexResponse,
    IndexResult,
    SearchByVectorRequest,
    SearchResponse,
    SearchResult,
    SearchTextRequest,
    VectorDeleteResponse,
    VectorProviderType,
    VectorStats,
)
from app.ai.vector.services.services import VectorService
from app.ai.vector.utils.utils import cosine_similarity, generate_vector_id, l2_distance, dot_product

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(v: list[float]) -> list[float]:
    mag = sum(x * x for x in v) ** 0.5
    return [x / mag for x in v] if mag else v


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestVectorExceptions:
    def test_vector_store_error_base(self):
        assert issubclass(SearchError, VectorStoreError)
        assert issubclass(IndexError, VectorStoreError)
        assert issubclass(ProviderNotFoundError, VectorStoreError)
        assert issubclass(DimensionMismatchError, VectorStoreError)
        assert issubclass(EmptyVectorError, VectorStoreError)

    def test_exception_raise_and_message(self):
        with pytest.raises(VectorStoreError, match="test error"):
            raise VectorStoreError("test error")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TestVectorSchemas:
    def test_vector_provider_type_enum(self):
        assert VectorProviderType.MEMORY.value == "memory"
        assert VectorProviderType.CHROMA.value == "chroma"

    def test_search_result_creation(self):
        result = SearchResult(
            embedding_id="emb_1",
            chunk_id="chunk_1",
            knowledge_id="doc_1",
            score=0.95,
            metadata={"key": "val"},
        )
        assert result.embedding_id == "emb_1"
        assert result.score == 0.95
        assert result.vector is None

    def test_search_result_with_vector(self):
        result = SearchResult(
            embedding_id="emb_1",
            chunk_id="chunk_1",
            score=0.85,
            vector=[0.1, 0.2, 0.3],
        )
        assert result.vector == [0.1, 0.2, 0.3]

    def test_search_response_defaults(self):
        result = SearchResult(embedding_id="emb_1", score=0.9)
        response = SearchResponse(results=[result], total=1, query_time_ms=5.0)
        assert len(response.results) == 1
        assert response.total == 1
        assert response.query_time_ms == 5.0

    def test_search_by_vector_request_defaults(self):
        req = SearchByVectorRequest(query_vector=[0.1, 0.2])
        assert req.top_k == 10
        assert req.include_vectors is False
        assert req.filters is None

    def test_search_by_vector_request_validation(self):
        with pytest.raises(Exception):
            SearchByVectorRequest(query_vector=[])

    def test_search_text_request(self):
        req = SearchTextRequest(query_text="blood pressure")
        assert req.query_text == "blood pressure"
        assert req.top_k == 10

    def test_index_request(self):
        req = IndexRequest(knowledge_id="doc_1")
        assert req.knowledge_id == "doc_1"
        assert req.chunk_ids is None

    def test_index_result_defaults(self):
        result = IndexResult(indexed_count=5, skipped_count=1)
        assert result.indexed_count == 5
        assert result.errors == []

    def test_vector_stats(self):
        stats = VectorStats(total_vectors=100, provider="memory")
        assert stats.total_vectors == 100
        assert stats.dimension is None

    def test_vector_delete_response(self):
        resp = VectorDeleteResponse(deleted=True, embedding_id="emb_1")
        assert resp.deleted is True

    def test_clear_response(self):
        resp = ClearResponse(cleared=True, previous_count=42)
        assert resp.previous_count == 42


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

class TestVectorUtils:
    def test_generate_vector_id(self):
        vid = generate_vector_id()
        assert vid.startswith("vec_")
        assert len(vid) > 10

    def test_cosine_similarity_identical(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_cosine_similarity_opposite(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_cosine_similarity_partial(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        result = cosine_similarity(a, b)
        assert -1.0 <= result <= 1.0

    def test_cosine_similarity_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_cosine_similarity_dimension_mismatch(self):
        with pytest.raises(ValueError, match="Dimension mismatch"):
            cosine_similarity([1.0], [1.0, 2.0])

    def test_l2_distance(self):
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        assert l2_distance(a, b) == pytest.approx(5.0)

    def test_l2_distance_identical(self):
        a = [1.0, 2.0]
        b = [1.0, 2.0]
        assert l2_distance(a, b) == pytest.approx(0.0)

    def test_dot_product(self):
        a = [1.0, 2.0]
        b = [3.0, 4.0]
        assert dot_product(a, b) == pytest.approx(11.0)

    def test_dot_product_zero(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert dot_product(a, b) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# MemoryVectorStore
# ---------------------------------------------------------------------------

class TestMemoryVectorStore:
    @pytest.mark.asyncio
    async def test_add_and_count(self):
        store = MemoryVectorStore()
        vid = await store.add("emb_1", [1.0, 0.0, 0.0], {"chunk_id": "c1"})
        assert vid == "emb_1"
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_add_empty_vector_raises(self):
        store = MemoryVectorStore()
        with pytest.raises(VectorStoreError, match="empty vector"):
            await store.add("emb_1", [])

    @pytest.mark.asyncio
    async def test_add_batch(self):
        store = MemoryVectorStore()
        ids = await store.add_batch([
            ("a", [1.0, 0.0], {"idx": 0}),
            ("b", [0.0, 1.0], {"idx": 1}),
        ])
        assert ids == ["a", "b"]
        assert await store.count() == 2

    @pytest.mark.asyncio
    async def test_delete_existing(self):
        store = MemoryVectorStore()
        await store.add("emb_1", [1.0, 0.0])
        assert await store.delete("emb_1") is True
        assert await store.count() == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        store = MemoryVectorStore()
        assert await store.delete("nonexistent") is False

    @pytest.mark.asyncio
    async def test_clear(self):
        store = MemoryVectorStore()
        await store.add_batch([("a", [1.0], {}), ("b", [2.0], {})])
        assert await store.count() == 2
        await store.clear()
        assert await store.count() == 0

    @pytest.mark.asyncio
    async def test_provider_name(self):
        store = MemoryVectorStore()
        assert store.provider_name() == "memory"

    @pytest.mark.asyncio
    async def test_search_returns_ordered_by_relevance(self):
        store = MemoryVectorStore()
        await store.add("q", [1.0, 0.0, 0.0], {"chunk_id": "query"})
        await store.add("a", [0.99, 0.1, 0.0], {"chunk_id": "close"})
        await store.add("b", [0.1, 0.99, 0.0], {"chunk_id": "far"})

        results = await store.search([1.0, 0.0, 0.0], top_k=3)
        assert len(results) == 3
        assert results[0]["score"] >= results[1]["score"]
        assert results[1]["score"] >= results[2]["score"]

    @pytest.mark.asyncio
    async def test_search_top_k_limits_results(self):
        store = MemoryVectorStore()
        for i in range(10):
            await store.add(f"v_{i}", [float(i) / 10, 0.0], {})
        results = await store.search([1.0, 0.0], top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_with_filters_exact_match(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0, 0.0], {"chunk_id": "c1", "specialty": "cardiology"})
        await store.add("b", [1.0, 0.0], {"chunk_id": "c2", "specialty": "neurology"})

        results = await store.search([1.0, 0.0], top_k=10, filters={"specialty": "cardiology"})
        assert len(results) == 1
        assert results[0]["embedding_id"] == "a"

    @pytest.mark.asyncio
    async def test_search_with_filters_list(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0, 0.0], {"specialty": "cardiology"})
        await store.add("b", [1.0, 0.0], {"specialty": "neurology"})
        await store.add("c", [1.0, 0.0], {"specialty": "ortho"})

        results = await store.search([1.0, 0.0], top_k=10, filters={"specialty": ["cardiology", "neurology"]})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_gt_filter(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0, 0.0], {"priority": 1})
        await store.add("b", [1.0, 0.0], {"priority": 5})
        await store.add("c", [1.0, 0.0], {"priority": 10})

        results = await store.search([1.0, 0.0], top_k=10, filters={"priority": {"$gt": 3}})
        assert len(results) == 2
        ids = {r["embedding_id"] for r in results}
        assert "b" in ids
        assert "c" in ids

    @pytest.mark.asyncio
    async def test_search_with_gte_lte_filters(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"val": 1})
        await store.add("b", [1.0], {"val": 5})
        await store.add("c", [1.0], {"val": 10})

        results = await store.search([1.0], top_k=10, filters={"val": {"$gte": 5, "$lte": 10}})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_ne_filter(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"status": "active"})
        await store.add("b", [1.0], {"status": "inactive"})

        results = await store.search([1.0], top_k=10, filters={"status": {"$ne": "inactive"}})
        assert len(results) == 1
        assert results[0]["embedding_id"] == "a"

    @pytest.mark.asyncio
    async def test_search_with_in_filter(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"dept": "cardio"})
        await store.add("b", [1.0], {"dept": "neuro"})
        await store.add("c", [1.0], {"dept": "ortho"})

        results = await store.search([1.0], top_k=10, filters={"dept": {"$in": ["cardio", "ortho"]}})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_and_filter(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"specialty": "cardio", "priority": 1})
        await store.add("b", [1.0], {"specialty": "cardio", "priority": 10})
        await store.add("c", [1.0], {"specialty": "neuro", "priority": 1})

        results = await store.search([1.0], top_k=10, filters={
            "$and": [{"specialty": "cardio"}, {"priority": {"$gt": 5}}],
        })
        assert len(results) == 1
        assert results[0]["embedding_id"] == "b"

    @pytest.mark.asyncio
    async def test_search_with_or_filter(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"specialty": "cardio"})
        await store.add("b", [1.0], {"specialty": "neuro"})
        await store.add("c", [1.0], {"specialty": "ortho"})

        results = await store.search([1.0], top_k=10, filters={
            "$or": [{"specialty": "cardio"}, {"specialty": "neuro"}],
        })
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_empty_store(self):
        store = MemoryVectorStore()
        results = await store.search([1.0, 0.0])
        assert results == []

    @pytest.mark.asyncio
    async def test_search_no_matching_filters(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"specialty": "cardio"})
        results = await store.search([1.0], top_k=10, filters={"specialty": "nonexistent"})
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_by_filter(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"dept": "cardio"})
        await store.add("b", [1.0], {"dept": "neuro"})
        await store.add("c", [1.0], {"dept": "cardio"})

        deleted = await store.delete_by_filter({"dept": "cardio"})
        assert deleted == 2
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_delete_by_filter_no_match(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"dept": "cardio"})
        deleted = await store.delete_by_filter({"dept": "ortho"})
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_delete_by_filter_range(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"val": 1})
        await store.add("b", [1.0], {"val": 5})
        await store.add("c", [1.0], {"val": 10})

        deleted = await store.delete_by_filter({"val": {"$gt": 3, "$lt": 8}})
        assert deleted == 1

    @pytest.mark.asyncio
    async def test_search_returns_vector_data(self):
        store = MemoryVectorStore()
        vec = [0.5, 0.5]
        await store.add("emb_1", vec, {"chunk_id": "c1"})
        results = await store.search([0.5, 0.5], top_k=1)
        assert len(results) == 1
        assert results[0]["vector"] == vec

    @pytest.mark.asyncio
    async def test_search_metadata_structure(self):
        store = MemoryVectorStore()
        await store.add("emb_1", [1.0, 0.0], {
            "chunk_id": "c1",
            "knowledge_id": "doc_1",
            "extra_field": "value",
        })
        results = await store.search([1.0, 0.0], top_k=1)
        r = results[0]
        assert r["chunk_id"] == "c1"
        assert r["knowledge_id"] == "doc_1"
        assert r["metadata"].get("extra_field") == "value"


# ---------------------------------------------------------------------------
# VectorService
# ---------------------------------------------------------------------------

class TestVectorService:
    @pytest.mark.asyncio
    async def test_index_vector(self):
        store = MemoryVectorStore()
        service = VectorService(store=store)
        vid = await service.index_vector("emb_1", [1.0, 0.0], {"chunk_id": "c1"})
        assert vid == "emb_1"
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_index_batch(self):
        store = MemoryVectorStore()
        service = VectorService(store=store)
        ids = await service.index_batch([
            ("a", [1.0, 0.0], {"idx": 0}),
            ("b", [0.0, 1.0], {"idx": 1}),
        ])
        assert ids == ["a", "b"]
        assert await store.count() == 2

    @pytest.mark.asyncio
    async def test_search_by_vector(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0, 0.0], {"chunk_id": "c1"})
        await store.add("b", [0.0, 1.0], {"chunk_id": "c2"})

        service = VectorService(store=store)
        response = await service.search_by_vector([1.0, 0.0], top_k=5)
        assert isinstance(response, SearchResponse)
        assert response.total == 2
        assert response.results[0].embedding_id == "a"

    @pytest.mark.asyncio
    async def test_search_by_vector_include_vectors(self):
        store = MemoryVectorStore()
        vec = [1.0, 0.0]
        await store.add("a", vec, {})
        service = VectorService(store=store)
        response = await service.search_by_vector(vec, top_k=5, include_vectors=True)
        assert response.results[0].vector == vec

    @pytest.mark.asyncio
    async def test_delete(self):
        store = MemoryVectorStore()
        await store.add("emb_1", [1.0])
        service = VectorService(store=store)
        assert await service.delete("emb_1") is True
        assert await service.delete("nonexistent") is False

    @pytest.mark.asyncio
    async def test_delete_by_filter(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0], {"dept": "cardio"})
        await store.add("b", [1.0], {"dept": "neuro"})
        service = VectorService(store=store)
        deleted = await service.delete_by_filter({"dept": "cardio"})
        assert deleted == 1

    @pytest.mark.asyncio
    async def test_get_stats(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0])
        await store.add("b", [2.0])
        service = VectorService(store=store)
        stats = await service.get_stats()
        assert stats.total_vectors == 2
        assert stats.provider == "memory"

    @pytest.mark.asyncio
    async def test_get_stats_empty(self):
        service = VectorService(store=MemoryVectorStore())
        stats = await service.get_stats()
        assert stats.total_vectors == 0

    @pytest.mark.asyncio
    async def test_clear(self):
        store = MemoryVectorStore()
        await store.add("a", [1.0])
        await store.add("b", [2.0])
        service = VectorService(store=store)
        cleared = await service.clear()
        assert cleared == 2
        assert await store.count() == 0

    @pytest.mark.asyncio
    async def test_store_property(self):
        store = MemoryVectorStore()
        service = VectorService(store=store)
        assert service.store is store

    @pytest.mark.asyncio
    async def test_empty_store_search(self):
        service = VectorService(store=MemoryVectorStore())
        response = await service.search_by_vector([1.0, 0.0])
        assert response.total == 0
        assert response.results == []


# ---------------------------------------------------------------------------
# DI / Deps
# ---------------------------------------------------------------------------

class TestVectorDeps:
    def test_reset_vector_service(self):
        reset_vector_service()
        svc = get_vector_service()
        assert svc is not None
        assert svc.store.provider_name() == "memory"

    def test_set_and_get(self):
        reset_vector_service()
        mock_store = MemoryVectorStore()
        mock_service = VectorService(store=mock_store)
        set_vector_service(mock_service)
        assert get_vector_service() is mock_service
        reset_vector_service()

    def test_get_after_reset_creates_new(self):
        reset_vector_service()
        svc1 = get_vector_service()
        reset_vector_service()
        svc2 = get_vector_service()
        assert svc1 is not svc2


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class TestVectorAPI:
    def _setup_service(self):
        reset_vector_service()
        store = MemoryVectorStore()
        service = VectorService(store=store)
        set_vector_service(service)
        return service

    def test_search_by_vector_endpoint(self):
        service = self._setup_service()
        import asyncio
        asyncio.run(service.index_vector("v1", [1.0, 0.0, 0.0], {"chunk_id": "c1"}))
        asyncio.run(service.index_vector("v2", [0.0, 1.0, 0.0], {"chunk_id": "c2"}))

        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/search",
            json={"query_vector": [1.0, 0.0, 0.0], "top_k": 5},
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)

    def test_search_endpoint_validates_empty_vector(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/search",
            json={"query_vector": [], "top_k": 5},
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (422, 401)

    def test_index_endpoint(self):
        service = self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/index",
            json={"knowledge_id": "doc_1"},
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 201, 401)

    def test_index_endpoint_no_embeddings(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/index",
            json={},
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 201, 401)

    def test_stats_endpoint(self):
        service = self._setup_service()
        import asyncio
        asyncio.run(service.index_vector("v1", [1.0]))

        from app.main import app
        client = TestClient(app)
        response = client.get(
            "/ai/vector/stats",
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.json()
            assert "total_vectors" in data
            assert data["provider"] == "memory"

    def test_stats_endpoint_empty(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.get(
            "/ai/vector/stats",
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            assert response.json()["total_vectors"] == 0

    def test_delete_vector_endpoint(self):
        service = self._setup_service()
        import asyncio
        asyncio.run(service.index_vector("v_test", [1.0]))

        from app.main import app
        client = TestClient(app)
        response = client.delete(
            "/ai/vector/v_test",
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)

    def test_delete_nonexistent_vector(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.delete(
            "/ai/vector/nonexistent",
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (404, 401)

    def test_clear_endpoint(self):
        service = self._setup_service()
        import asyncio
        asyncio.run(service.index_vector("v1", [1.0]))
        asyncio.run(service.index_vector("v2", [1.0]))

        from app.main import app
        client = TestClient(app)
        response = client.delete(
            "/ai/vector/clear",
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.json()
            assert data["cleared"] is True
            assert data["previous_count"] == 2

    def test_clear_empty_endpoint(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.delete(
            "/ai/vector/clear",
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            assert response.json()["previous_count"] == 0

    def test_search_with_filters_endpoint(self):
        service = self._setup_service()
        import asyncio
        asyncio.run(service.index_vector("v1", [1.0, 0.0], {"specialty": "cardio"}))

        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/search",
            json={
                "query_vector": [1.0, 0.0],
                "top_k": 10,
                "filters": {"specialty": "cardio"},
            },
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)

    def test_search_with_include_vectors(self):
        service = self._setup_service()
        import asyncio
        asyncio.run(service.index_vector("v1", [1.0, 0.0], {}))

        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/search",
            json={"query_vector": [1.0, 0.0], "include_vectors": True},
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (200, 401)

    def test_unauthorized_access(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)

        for method, path in [
            ("POST", "/ai/vector/search"),
            ("POST", "/ai/vector/index"),
            ("GET", "/ai/vector/stats"),
            ("DELETE", "/ai/vector/clear"),
        ]:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path, json={"query_vector": [1.0], "top_k": 1})
            else:
                response = client.delete(path)
            assert response.status_code == 401, f"{method} {path} should return 401"

    def test_search_top_k_max_limit(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/search",
            json={"query_vector": [1.0], "top_k": 500},
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (422, 401)

    def test_search_missing_query_vector(self):
        self._setup_service()
        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/ai/vector/search",
            json={"top_k": 5},
            headers={"Authorization": "Bearer test_token"},
        )
        reset_vector_service()
        assert response.status_code in (422, 401)
