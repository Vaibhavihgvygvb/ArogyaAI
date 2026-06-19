import time

from app.ai.embeddings.schemas.schemas import EmbeddingStatus
from app.ai.embeddings.services.services import EmbeddingService
from app.ai.knowledge.services.services import KnowledgeService
from app.ai.retrieval.exceptions.exceptions import (
    ChunkNotFoundError,
    EmbeddingQueryError,
    InvalidQueryError,
    RetrievalError,
)
from app.ai.retrieval.interfaces.interfaces import RerankerProvider
from app.ai.retrieval.rerankers.rerankers import NoOpReranker
from app.ai.retrieval.schemas.schemas import ContextAssembly, RetrievalQuery, RetrievalResult, RetrievalResponse
from app.ai.vector.services.services import VectorService


def timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


DEFAULT_RAG_SYSTEM_MESSAGE = """You are a helpful medical AI assistant. Use the provided context to answer the user's question accurately and concisely.

Context:
{context}

Instructions:
- Answer based ONLY on the provided context. If the context doesn't contain relevant information, say so.
- Cite specific sources when using information from the context.
- Do not make up medical information or diagnoses.
- Use clear, plain language.
- If you're unsure about something, say so."""


class RetrievalPipeline:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_service: VectorService,
        knowledge_service: KnowledgeService,
        reranker: RerankerProvider | None = None,
    ):
        self._embedding_service = embedding_service
        self._vector_service = vector_service
        self._knowledge_service = knowledge_service
        self._reranker = reranker or NoOpReranker()

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResponse:
        start = time.time()

        if not query.query.strip():
            raise InvalidQueryError("Query cannot be empty")

        query_vector = await self._embed_query(query.query)

        search_result = await self._vector_service.search_by_vector(
            query_vector=query_vector,
            top_k=query.top_k,
            filters=query.filters,
            include_vectors=query.include_vectors,
        )

        results = []
        for sr in search_result.results:
            result = RetrievalResult(
                chunk_id=sr.chunk_id or "",
                knowledge_id=sr.knowledge_id or "",
                score=sr.score,
                metadata=sr.metadata,
                rank=0,
            )
            if query.include_chunks and sr.chunk_id and sr.knowledge_id:
                try:
                    chunk = await self._knowledge_service.get_chunk(
                        document_id=sr.knowledge_id,
                        chunk_id=sr.chunk_id,
                    )
                    if chunk:
                        result.content = chunk.content
                        result.document_id = sr.knowledge_id
                        if chunk.metadata:
                            result.metadata["chunk_index"] = chunk.metadata.chunk_index
                            result.metadata["source_document"] = chunk.metadata.source_document
                except ChunkNotFoundError:
                    pass
            results.append(result)

        if query.min_score is not None:
            results = [r for r in results if r.score >= query.min_score]

        if query.rerank:
            results = await self._reranker.rerank(query.query, results, top_k=query.top_k)

        return RetrievalResponse(
            results=results,
            total=len(results),
            query=query.query,
            query_time_ms=timing_ms(start),
        )

    async def _embed_query(self, query: str) -> list[float]:
        try:
            mock_chunk_id = f"query_{hash(query) % (10 ** 10)}"
            vector = await self._embedding_service.generate(
                content=query,
                chunk_id=mock_chunk_id,
                document_id="__query__",
            )
            if vector.status == EmbeddingStatus.FAILED:
                raise EmbeddingQueryError("Failed to embed query")
            return vector.vector
        except EmbeddingQueryError:
            raise
        except Exception as e:
            raise EmbeddingQueryError(f"Query embedding failed: {e}")

    async def assemble_context(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        min_score: float | None = None,
        max_tokens: int = 2048,
    ) -> ContextAssembly:
        retrieval_query = RetrievalQuery(
            query=query,
            top_k=top_k,
            filters=filters,
            min_score=min_score,
            include_chunks=True,
            rerank=True,
        )
        response = await self.retrieve(retrieval_query)

        context_parts = []
        token_count = 0
        truncated = False

        for i, result in enumerate(response.results):
            if not result.content:
                continue
            part = f"[Source {i + 1}] (score: {result.score:.3f}):\n{result.content}\n"
            estimated_tokens = len(part) // 4
            if token_count + estimated_tokens > max_tokens:
                remaining_tokens = max_tokens - token_count
                if remaining_tokens > 10:
                    truncated_content = result.content[: remaining_tokens * 4]
                    part = f"[Source {i + 1}] (score: {result.score:.3f}):\n{truncated_content}\n"
                    context_parts.append(part)
                truncated = True
                break
            context_parts.append(part)
            token_count += estimated_tokens

        return ContextAssembly(
            context="\n".join(context_parts),
            token_count=token_count,
            chunk_count=len([r for r in response.results if r.content]),
            truncated=truncated,
        )

    async def rag_generate(
        self,
        query: str,
        context: str,
        system_message: str | None = None,
    ) -> tuple[str, str, str, dict | None]:
        from app.ai.gateway.deps import get_gateway as _get_gateway
        from app.ai.gateway.pipeline import GatewayRequest

        system = system_message or DEFAULT_RAG_SYSTEM_MESSAGE
        filled_system = system.replace("{context}", context)

        gateway = _get_gateway()
        gateway_request = GatewayRequest(
            messages=[
                {"role": "system", "content": filled_system},
                {"role": "user", "content": query},
            ],
        )
        response = await gateway.execute(gateway_request)
        return response.content, response.model, response.provider, response.usage
