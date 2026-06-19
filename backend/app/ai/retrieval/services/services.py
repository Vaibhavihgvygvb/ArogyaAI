from app.ai.embeddings.services.services import EmbeddingService
from app.ai.knowledge.services.services import KnowledgeService
from app.ai.retrieval.exceptions.exceptions import RetrievalError
from app.ai.retrieval.interfaces.interfaces import RerankerProvider
from app.ai.retrieval.pipelines.pipelines import RetrievalPipeline
from app.ai.retrieval.rerankers.rerankers import MockReranker, NoOpReranker
from app.ai.retrieval.schemas.schemas import (
    ContextAssembly,
    RAGRequest,
    RAGResponse,
    RetrievalQuery,
    RetrievalResponse,
    SearchRequest,
    SearchResponse,
)
from app.ai.vector.services.services import VectorService


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_service: VectorService,
        knowledge_service: KnowledgeService,
        reranker: RerankerProvider | None = None,
    ):
        self._pipeline = RetrievalPipeline(
            embedding_service=embedding_service,
            vector_service=vector_service,
            knowledge_service=knowledge_service,
            reranker=reranker or MockReranker(),
        )

    async def search(self, request: SearchRequest) -> SearchResponse:
        query = RetrievalQuery(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            min_score=request.min_score,
            include_chunks=request.include_chunks,
            rerank=request.rerank,
        )
        response = await self._pipeline.retrieve(query)
        return SearchResponse(
            results=response.results,
            total=response.total,
            query=response.query,
            query_time_ms=response.query_time_ms,
        )

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResponse:
        return await self._pipeline.retrieve(query)

    async def assemble_context(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        min_score: float | None = None,
        max_tokens: int = 2048,
    ) -> ContextAssembly:
        return await self._pipeline.assemble_context(
            query=query,
            top_k=top_k,
            filters=filters,
            min_score=min_score,
            max_tokens=max_tokens,
        )

    async def rag_generate(self, request: RAGRequest) -> RAGResponse:
        import time

        retrieval_start = time.time()
        context_assembly = await self._pipeline.assemble_context(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            min_score=request.min_score,
            max_tokens=request.max_context_tokens,
        )
        retrieval_time_ms = round((time.time() - retrieval_start) * 1000, 2)

        from app.ai.retrieval.pipelines.pipelines import DEFAULT_RAG_SYSTEM_MESSAGE

        system = request.system_message or DEFAULT_RAG_SYSTEM_MESSAGE

        generation_start = time.time()
        try:
            answer, model, provider, usage = await self._pipeline.rag_generate(
                query=request.query,
                context=context_assembly.context,
                system_message=system,
            )
        except Exception as e:
            raise RetrievalError(f"RAG generation failed: {e}")

        generation_time_ms = round((time.time() - generation_start) * 1000, 2)

        retrieval_query = RetrievalQuery(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            min_score=request.min_score,
            include_chunks=False,
            rerank=True,
        )
        retrieval_response = await self._pipeline.retrieve(retrieval_query)

        return RAGResponse(
            answer=answer,
            conversation_id=request.conversation_id,
            sources=retrieval_response.results,
            model=model,
            provider=provider,
            usage=usage,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
        )
