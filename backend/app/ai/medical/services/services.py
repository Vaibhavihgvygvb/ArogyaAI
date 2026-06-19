import time
from typing import Any

from app.ai.medical.citations.citations import CitationEngine as _DefaultCitationEngine
from app.ai.medical.config.config import MedicalSettings
from app.ai.medical.exceptions.exceptions import (
    MedicalIntelligenceError,
    RetrievalOrchestrationError,
)
from app.ai.medical.intent.intent import IntentDetector as _DefaultIntentDetector
from app.ai.medical.interfaces.interfaces import CitationEngineABC, IntentDetectorABC
from app.ai.medical.pipelines.pipelines import MedicalPipeline
from app.ai.medical.schemas.schemas import (
    MedicalQuery,
    MedicalResponse,
    MedicalSearchRequest,
    MedicalSearchResponse,
)
from app.ai.retrieval.deps.deps import get_retrieval_service


class MedicalService:
    def __init__(
        self,
        pipeline: MedicalPipeline | None = None,
        settings: MedicalSettings | None = None,
        intent_detector: IntentDetectorABC | None = None,
        citation_engine: CitationEngineABC | None = None,
    ):
        self._pipeline = pipeline or MedicalPipeline(settings=settings)
        self._settings = settings or MedicalSettings()
        self._intent_detector = intent_detector or _DefaultIntentDetector()
        self._citation_engine = citation_engine or _DefaultCitationEngine()

    async def query(self, request: MedicalQuery) -> MedicalResponse:
        retrieval_results = None
        retrieval_context = None

        if request.query.strip():
            try:
                retrieval_results, retrieval_context = await self._retrieve(request)
            except Exception as e:
                raise RetrievalOrchestrationError(f"Retrieval failed: {e}")

        response = await self._pipeline.run(
            query=request,
            retrieval_results=retrieval_results,
            retrieval_context=retrieval_context,
        )

        return response

    async def search(self, request: MedicalSearchRequest) -> MedicalSearchResponse:
        start = time.time()

        raw_results, _ = await self._retrieve_search(request)

        results = await self._citation_engine.build_citations(raw_results)

        intent = await self._intent_detector.detect(request.query, request.specialty.value if request.specialty else None)

        query_time_ms = round((time.time() - start) * 1000, 2)
        return MedicalSearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            intent=intent,
            query_time_ms=query_time_ms,
        )

    async def _retrieve(self, request: MedicalQuery) -> tuple[list[Any], str]:
        retrieval = get_retrieval_service()
        retrieval_response = await retrieval.search(
            MedicalSearchRequest(
                query=request.query,
                top_k=request.top_k,
                filters=request.filters,
                min_score=request.min_score,
                include_chunks=True,
                rerank=True,
            )
        )

        if not retrieval_response.results:
            return [], ""

        context_parts = []
        for i, r in enumerate(retrieval_response.results):
            content = ""
            if hasattr(r, "content") and r.content:
                content = r.content
            elif hasattr(r, "evidence_text") and r.evidence_text:
                content = r.evidence_text
            if content:
                context_parts.append(f"[Source {i + 1}]:\n{content}\n")

        context = "\n".join(context_parts)

        max_chars = self._settings.MEDICAL_MAX_CONTEXT_TOKENS * 4
        if len(context) > max_chars:
            context = context[:max_chars]

        return retrieval_response.results, context

    async def _retrieve_search(self, request: MedicalSearchRequest) -> tuple[list[Any], str]:
        retrieval = get_retrieval_service()

        class _SearchRequest:
            def __init__(self, req: MedicalSearchRequest):
                self.query = req.query
                self.top_k = req.top_k
                self.filters = req.filters
                self.min_score = req.min_score
                self.include_chunks = req.include_chunks
                self.rerank = req.rerank

        response = await retrieval.search(_SearchRequest(request))

        if not response.results:
            return [], ""

        context_parts = []
        for i, r in enumerate(response.results):
            content = ""
            if hasattr(r, "content") and r.content:
                content = r.content
            elif hasattr(r, "evidence_text") and r.evidence_text:
                content = r.evidence_text
            if content:
                context_parts.append(f"[Source {i + 1}]:\n{content}\n")

        return response.results, "\n".join(context_parts)
