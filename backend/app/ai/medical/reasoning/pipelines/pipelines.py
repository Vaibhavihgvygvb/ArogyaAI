import time
from typing import Any

from app.ai.medical.engine.deps import get_query_understanding_engine
from app.ai.medical.engine.schemas import QueryUnderstandingResult
from app.ai.medical.reasoning.citations.planning import CitationPlanner
from app.ai.medical.reasoning.config.config import ReasoningSettings
from app.ai.medical.reasoning.confidence.planning import ConfidencePlanner
from app.ai.medical.reasoning.context.compression import ContextCompressor
from app.ai.medical.reasoning.context.ranking import ContextRanker
from app.ai.medical.reasoning.exceptions.exceptions import ReasoningPipelineError
from app.ai.medical.reasoning.interfaces.interfaces import (
    CitationPlannerABC,
    ConfidencePlannerABC,
    ContextCompressorABC,
    ContextRankerABC,
    EvidencePlannerABC,
    PromptAssemblerABC,
    ReasoningPipelineABC,
    ReasoningPlannerABC,
    RetrievalStrategyABC,
    SafetyPlannerABC,
)
from app.ai.medical.reasoning.planners.evidence_planner import EvidencePlanner
from app.ai.medical.reasoning.planners.reasoning_planner import ReasoningPlanner
from app.ai.medical.reasoning.planners.retrieval_strategy import RetrievalStrategy
from app.ai.medical.reasoning.prompts.assembly import PromptAssembler
from app.ai.medical.reasoning.safety.planning import SafetyPlanner
from app.ai.medical.reasoning.schemas.schemas import (
    AssembledPrompt,
    CitationPlan,
    CompressedContext,
    ConfidencePlan,
    EvidencePlan,
    RankedContext,
    ReasoningPlan,
    RetrievalPlan,
    SafetyPlan,
)


def _timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


class ReasoningPipeline(ReasoningPipelineABC):
    def __init__(
        self,
        reasoning_planner: ReasoningPlannerABC | None = None,
        evidence_planner: EvidencePlannerABC | None = None,
        retrieval_strategy: RetrievalStrategyABC | None = None,
        context_ranker: ContextRankerABC | None = None,
        context_compressor: ContextCompressorABC | None = None,
        prompt_assembler: PromptAssemblerABC | None = None,
        citation_planner: CitationPlannerABC | None = None,
        confidence_planner: ConfidencePlannerABC | None = None,
        safety_planner: SafetyPlannerABC | None = None,
        settings: ReasoningSettings | None = None,
    ):
        self._reasoning_planner = reasoning_planner or ReasoningPlanner()
        self._evidence_planner = evidence_planner or EvidencePlanner()
        self._retrieval_strategy = retrieval_strategy or RetrievalStrategy()
        self._context_ranker = context_ranker or ContextRanker()
        self._context_compressor = context_compressor or ContextCompressor()
        self._prompt_assembler = prompt_assembler or PromptAssembler()
        self._citation_planner = citation_planner or CitationPlanner()
        self._confidence_planner = confidence_planner or ConfidencePlanner()
        self._safety_planner = safety_planner or SafetyPlanner()
        self._settings = settings or ReasoningSettings()

    async def run(
        self,
        query: str,
        analysis: QueryUnderstandingResult | None = None,
        top_k: int = 15,
        filters: dict | None = None,
        min_score: float | None = None,
        max_context_tokens: int = 4096,
        approach_hint: str | None = None,
    ) -> dict[str, Any]:
        stages: dict[str, float] = {}
        pipeline_result: dict[str, Any] = {}

        if analysis is None:
            stage_start = time.time()
            engine = get_query_understanding_engine()
            result = await engine.analyze(query)
            pipeline_result["analysis"] = result
            stages["analysis"] = _timing_ms(stage_start)
            analysis = result

        stage_start = time.time()
        try:
            reasoning_plan = await self._reasoning_planner.plan(query, analysis, approach_hint)
            pipeline_result["reasoning_plan"] = reasoning_plan
            stages["reasoning_plan"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Reasoning planning failed: {e}")

        stage_start = time.time()
        try:
            evidence_plan = await self._evidence_planner.plan(query, analysis, reasoning_plan)
            pipeline_result["evidence_plan"] = evidence_plan
            stages["evidence_plan"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Evidence planning failed: {e}")

        stage_start = time.time()
        try:
            retrieval_plan = await self._retrieval_strategy.plan(
                query, evidence_plan, analysis, top_k, filters,
            )
            pipeline_result["retrieval_plan"] = retrieval_plan
            stages["retrieval_strategy"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Retrieval strategy failed: {e}")

        raw_results: list[Any] = []
        stage_start = time.time()
        try:
            raw_results = await self._execute_retrieval(retrieval_plan, min_score)
            stages["retrieval"] = _timing_ms(stage_start)
        except Exception as e:
            stages["retrieval"] = _timing_ms(stage_start)

        stage_start = time.time()
        try:
            ranked_context = await self._context_ranker.rank(raw_results, query, retrieval_plan, analysis)
            pipeline_result["ranked_context"] = ranked_context
            stages["context_ranking"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Context ranking failed: {e}")

        stage_start = time.time()
        try:
            compressed_context = await self._context_compressor.compress(
                raw_results, ranked_context, query, max_context_tokens,
            )
            pipeline_result["compressed_context"] = compressed_context
            stages["context_compression"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Context compression failed: {e}")

        stage_start = time.time()
        try:
            assembled_prompt = await self._prompt_assembler.assemble(
                query, compressed_context, reasoning_plan, evidence_plan, analysis,
            )
            pipeline_result["assembled_prompt"] = assembled_prompt
            stages["prompt_assembly"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Prompt assembly failed: {e}")

        stage_start = time.time()
        try:
            citation_plan = await self._citation_planner.plan(raw_results, ranked_context)
            pipeline_result["citation_plan"] = citation_plan
            stages["citation_planning"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Citation planning failed: {e}")

        stage_start = time.time()
        try:
            confidence_plan = await self._confidence_planner.plan(raw_results, ranked_context, analysis)
            pipeline_result["confidence_plan"] = confidence_plan
            stages["confidence_planning"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Confidence planning failed: {e}")

        stage_start = time.time()
        try:
            safety_plan = await self._safety_planner.plan(query, analysis, reasoning_plan)
            pipeline_result["safety_plan"] = safety_plan
            stages["safety_planning"] = _timing_ms(stage_start)
        except Exception as e:
            raise ReasoningPipelineError(f"Safety planning failed: {e}")

        pipeline_result["stages"] = stages
        pipeline_result["total_time_ms"] = sum(v for v in stages.values())

        return pipeline_result

    async def _execute_retrieval(
        self,
        retrieval_plan: RetrievalPlan,
        min_score: float | None = None,
    ) -> list[Any]:
        from app.ai.retrieval.deps.deps import get_retrieval_service
        from app.ai.retrieval.schemas.schemas import SearchRequest

        retrieval = get_retrieval_service()
        all_results: list[Any] = []
        seen_ids: set[str] = set()

        for i, sub_query in enumerate(retrieval_plan.sub_queries):
            if not sub_query.strip():
                continue

            try:
                response = await retrieval.search(
                    SearchRequest(
                        query=sub_query,
                        top_k=retrieval_plan.top_k_per_query,
                        filters=retrieval_plan.filters,
                        min_score=min_score,
                        include_chunks=True,
                        rerank=True,
                    )
                )
            except Exception:
                continue

            for result in response.results:
                chunk_id = getattr(result, "chunk_id", "") or str(id(result))
                if chunk_id not in seen_ids:
                    weight = retrieval_plan.weights[i] if i < len(retrieval_plan.weights) else 1.0
                    if hasattr(result, "score") and result.score is not None:
                        result.score = result.score * weight
                    all_results.append(result)
                    seen_ids.add(chunk_id)

        if retrieval_plan.merge_strategy == "max":
            all_results.sort(key=lambda r: getattr(r, "score", 0) or 0, reverse=True)
        elif retrieval_plan.merge_strategy == "score_weighted":
            all_results.sort(key=lambda r: getattr(r, "score", 0) or 0, reverse=True)
        else:
            pass

        return all_results
