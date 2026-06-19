import time
from typing import Any

from app.ai.medical.reasoning.config.config import ReasoningSettings
from app.ai.medical.reasoning.exceptions.exceptions import ReasoningServiceError
from app.ai.medical.reasoning.interfaces.interfaces import ReasoningServiceABC
from app.ai.medical.reasoning.pipelines.pipelines import ReasoningPipeline
from app.ai.medical.reasoning.schemas.schemas import ReasoningRequest, ReasoningResponse


class ReasoningService(ReasoningServiceABC):
    def __init__(
        self,
        pipeline: ReasoningPipeline | None = None,
        settings: ReasoningSettings | None = None,
    ):
        self._pipeline = pipeline or ReasoningPipeline()
        self._settings = settings or ReasoningSettings()

    async def reason(
        self,
        query: str,
        conversation_id: str | None = None,
        approach_hint: str | None = None,
        top_k: int = 15,
        filters: dict | None = None,
        min_score: float | None = None,
        max_context_tokens: int = 4096,
        include_reasoning_plan: bool = True,
        include_evidence_plan: bool = True,
        include_retrieval_plan: bool = True,
        include_context_ranking: bool = True,
        include_context_compression: bool = True,
        include_prompt_assembly: bool = True,
        include_citation_plan: bool = True,
        include_confidence_plan: bool = True,
        include_safety_plan: bool = True,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ReasoningResponse:
        start = time.time()

        if not query or not query.strip():
            raise ReasoningServiceError("Query cannot be empty")

        request = ReasoningRequest(
            original_query=query,
            conversation_id=conversation_id,
            approach_hint=approach_hint,
            top_k=top_k,
            filters=filters,
            min_score=min_score,
            include_reasoning_plan=include_reasoning_plan,
            include_evidence_plan=include_evidence_plan,
            include_retrieval_plan=include_retrieval_plan,
            include_context_ranking=include_context_ranking,
            include_context_compression=include_context_compression,
            include_prompt_assembly=include_prompt_assembly,
            include_citation_plan=include_citation_plan,
            include_confidence_plan=include_confidence_plan,
            include_safety_plan=include_safety_plan,
            max_context_tokens=max_context_tokens,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            pipeline_result = await self._pipeline.run(
                query=query,
                top_k=top_k,
                filters=filters,
                min_score=min_score,
                max_context_tokens=max_context_tokens,
                approach_hint=approach_hint,
            )
        except Exception as e:
            raise ReasoningServiceError(f"Reasoning pipeline failed: {e}")

        processing_time_ms = round((time.time() - start) * 1000, 2)

        reasoning_plan = pipeline_result.get("reasoning_plan") if include_reasoning_plan else None
        evidence_plan = pipeline_result.get("evidence_plan") if include_evidence_plan else None
        retrieval_plan = pipeline_result.get("retrieval_plan") if include_retrieval_plan else None
        ranked_context = pipeline_result.get("ranked_context") if include_context_ranking else None
        compressed_context = pipeline_result.get("compressed_context") if include_context_compression else None
        assembled_prompt = pipeline_result.get("assembled_prompt") if include_prompt_assembly else None
        citation_plan = pipeline_result.get("citation_plan") if include_citation_plan else None
        confidence_plan = pipeline_result.get("confidence_plan") if include_confidence_plan else None
        safety_plan = pipeline_result.get("safety_plan") if include_safety_plan else None

        analysis_raw = pipeline_result.get("analysis")
        analysis = analysis_raw.model_dump() if hasattr(analysis_raw, "model_dump") else analysis_raw

        full_response = {}
        for key, value in pipeline_result.items():
            if key in ("stages", "total_time_ms"):
                full_response[key] = value
            elif hasattr(value, "model_dump"):
                full_response[key] = value.model_dump()
            elif isinstance(value, list):
                full_response[key] = [
                    v.model_dump() if hasattr(v, "model_dump") else v
                    for v in value
                ]
            else:
                full_response[key] = value

        return ReasoningResponse(
            request=request,
            analysis=analysis,
            reasoning_plan=reasoning_plan,
            evidence_plan=evidence_plan,
            retrieval_plan=retrieval_plan,
            ranked_context=ranked_context,
            compressed_context=compressed_context,
            assembled_prompt=assembled_prompt,
            citation_plan=citation_plan,
            confidence_plan=confidence_plan,
            safety_plan=safety_plan,
            full_response=full_response,
            processing_time_ms=processing_time_ms,
            stages=pipeline_result.get("stages", {}),
        )
