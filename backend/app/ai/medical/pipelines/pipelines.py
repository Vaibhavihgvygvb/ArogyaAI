import time
from typing import Any

from app.ai.medical.citations.citations import CitationEngine as _DefaultCitationEngine
from app.ai.medical.confidence.confidence import ConfidenceEngine as _DefaultConfidenceEngine
from app.ai.medical.config.config import MedicalSettings
from app.ai.medical.exceptions.exceptions import (
    CitationError,
    ConfidenceError,
    ContextOptimizationError,
    IntentDetectionError,
    MedicalIntelligenceError,
    MedicalPromptError,
    MedicalReasoningError,
    QueryRewriteError,
    RetrievalOrchestrationError,
    ResponseBuilderError,
    SafetyValidationError,
)
from app.ai.medical.intent.intent import IntentDetector as _DefaultIntentDetector
from app.ai.medical.interfaces.interfaces import (
    CitationEngineABC,
    ConfidenceEngineABC,
    ContextOptimizerABC,
    IntentDetectorABC,
    MedicalPromptBuilderABC,
    MedicalReasonerABC,
    QueryRewriterABC,
    ResponseBuilderABC,
    SafetyValidatorABC,
)
from app.ai.medical.reasoning.reasoning import MedicalReasoner as _DefaultReasoner
from app.ai.medical.responses.responses import ResponseBuilder as _DefaultResponseBuilder
from app.ai.medical.rewriters.rewriters import QueryRewriter as _DefaultQueryRewriter
from app.ai.medical.schemas.schemas import (
    CitationEntry,
    ConfidenceScore,
    IntentType,
    MedicalContext,
    MedicalIntent,
    MedicalMetadata,
    MedicalQuery,
    MedicalReasoning,
    MedicalResponse,
    QueryRewrite,
    SafetyCheckResult,
    Specialty,
    UrgencyLevel,
)
from app.ai.medical.validators.validators import SafetyValidator as _DefaultSafetyValidator

DEFAULT_MEDICAL_SYSTEM_MESSAGE = """You are a medical intelligence assistant providing evidence-based clinical information.
Use the provided medical context to answer questions accurately and responsibly.

Medical Context:
{context}

Guidelines:
- Answer based ONLY on the provided medical context.
- If the context lacks sufficient information, state this clearly.
- Include relevant clinical considerations when appropriate.
- Do NOT provide definitive diagnoses or treatment plans — this is informational only.
- Flag any information that requires immediate medical attention.
- Use precise medical terminology but explain complex terms.
- Cite specific sources when referencing information from the context.
- For medication information, include standard dosing context and safety considerations.
- Distinguish between established medical knowledge and emerging research."""


def timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


class MedicalPipeline:
    def __init__(
        self,
        intent_detector: IntentDetectorABC | None = None,
        query_rewriter: QueryRewriterABC | None = None,
        context_optimizer: ContextOptimizerABC | None = None,
        prompt_builder: MedicalPromptBuilderABC | None = None,
        reasoner: MedicalReasonerABC | None = None,
        citation_engine: CitationEngineABC | None = None,
        confidence_engine: ConfidenceEngineABC | None = None,
        safety_validator: SafetyValidatorABC | None = None,
        response_builder: ResponseBuilderABC | None = None,
        settings: MedicalSettings | None = None,
    ):
        self._intent_detector = intent_detector or _DefaultIntentDetector()
        self._query_rewriter = query_rewriter or _DefaultQueryRewriter()
        self._context_optimizer = context_optimizer or _DefaultContextOptimizer()
        self._prompt_builder = prompt_builder or _DefaultMedicalPromptBuilder()
        self._reasoner = reasoner or _DefaultReasoner()
        self._citation_engine = citation_engine or _DefaultCitationEngine()
        self._confidence_engine = confidence_engine or _DefaultConfidenceEngine()
        self._safety_validator = safety_validator or _DefaultSafetyValidator()
        self._response_builder = response_builder or _DefaultResponseBuilder()
        self._settings = settings or MedicalSettings()

    async def run(
        self,
        query: MedicalQuery,
        retrieval_results: list[Any] | None = None,
        retrieval_context: str | None = None,
    ) -> MedicalResponse:
        stages: dict[str, float] = {}
        stage_start = time.time()

        try:
            intent = await self._detect_intent(query)
            stages["intent_detection"] = timing_ms(stage_start)
        except Exception as e:
            raise IntentDetectionError(f"Intent detection failed: {e}")

        stage_start = time.time()
        try:
            rewrite = await self._rewrite_query(query, intent)
            stages["query_rewrite"] = timing_ms(stage_start)
        except Exception as e:
            raise QueryRewriteError(f"Query rewrite failed: {e}")

        stage_start = time.time()
        try:
            context_assembly = await self._optimize_context(query, retrieval_context, intent)
            stages["context_optimization"] = timing_ms(stage_start)
        except Exception as e:
            raise ContextOptimizationError(f"Context optimization failed: {e}")

        stage_start = time.time()
        try:
            system_message, prompt = await self._build_prompt(query, context_assembly, intent)
            stages["prompt_building"] = timing_ms(stage_start)
        except Exception as e:
            raise MedicalPromptError(f"Prompt building failed: {e}")

        stage_start = time.time()
        try:
            answer, model, provider, usage = await self._generate(query, system_message, prompt)
            stages["generation"] = timing_ms(stage_start)
        except Exception as e:
            raise MedicalIntelligenceError(f"Generation failed: {e}")

        stage_start = time.time()
        try:
            citations = await self._build_citations(retrieval_results)
            stages["citation_building"] = timing_ms(stage_start)
        except Exception as e:
            raise CitationError(f"Citation building failed: {e}")

        stage_start = time.time()
        reasoning = None
        if query.include_reasoning and self._settings.MEDICAL_REASONING_ENABLED:
            try:
                reasoning = await self._reason(query, context_assembly, answer, intent)
                stages["reasoning"] = timing_ms(stage_start)
            except Exception as e:
                raise MedicalReasoningError(f"Reasoning failed: {e}")
        else:
            stages["reasoning"] = 0.0

        stage_start = time.time()
        try:
            confidence = await self._score_confidence(query, answer, citations, intent)
            stages["confidence"] = timing_ms(stage_start)
        except Exception as e:
            raise ConfidenceError(f"Confidence scoring failed: {e}")

        stage_start = time.time()
        try:
            safety = await self._validate_safety(query, answer, citations, intent)
            stages["safety_validation"] = timing_ms(stage_start)
        except Exception as e:
            raise SafetyValidationError(f"Safety validation failed: {e}")

        stage_start = time.time()
        try:
            metadata = MedicalMetadata(
                model=model,
                provider=provider,
                usage=usage,
                processing_time_ms=sum(v for v in stages.values()),
                pipeline_stages=stages,
            )
            response = await self._build_response(answer, intent, reasoning, citations, confidence, safety, metadata, query.conversation_id)
            stages["response_building"] = timing_ms(stage_start)
        except Exception as e:
            raise ResponseBuilderError(f"Response building failed: {e}")

        return response

    async def _detect_intent(self, query: MedicalQuery) -> MedicalIntent:
        specialty_hint = query.specialty.value if query.specialty else None
        return await self._intent_detector.detect(query.query, specialty_hint)

    async def _rewrite_query(self, query: MedicalQuery, intent: MedicalIntent) -> QueryRewrite | None:
        if not self._settings.MEDICAL_REWRITE_ENABLED:
            return None
        return await self._query_rewriter.rewrite(query.query, intent)

    async def _optimize_context(
        self,
        query: MedicalQuery,
        retrieval_context: str | None,
        intent: MedicalIntent,
    ) -> MedicalContext:
        context_text = retrieval_context or ""
        return await self._context_optimizer.optimize(
            context_text,
            intent,
            max_tokens=query.max_context_tokens,
        )

    async def _build_prompt(
        self,
        query: MedicalQuery,
        context_assembly: MedicalContext,
        intent: MedicalIntent,
    ) -> tuple[str, str]:
        return await self._prompt_builder.build(
            query=query.query,
            context=context_assembly.context,
            intent=intent,
        )

    async def _generate(
        self,
        query: MedicalQuery,
        system_message: str,
        prompt: str,
    ) -> tuple[str, str, str, dict | None]:
        from app.ai.gateway.deps import get_gateway as _get_gateway
        from app.ai.gateway.pipeline import GatewayRequest

        gateway = _get_gateway()
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]
        gateway_request = GatewayRequest(
            messages=messages,
            temperature=query.temperature,
            max_tokens=query.max_tokens,
        )
        response = await gateway.execute(gateway_request)
        return response.content, response.model, response.provider, response.usage

    async def _build_citations(self, results: list[Any] | None) -> list[CitationEntry]:
        if not results:
            return []
        return await self._citation_engine.build_citations(results)

    async def _reason(
        self,
        query: MedicalQuery,
        context_assembly: MedicalContext,
        answer: str,
        intent: MedicalIntent,
    ) -> MedicalReasoning:
        return await self._reasoner.reason(
            query=query.query,
            context=context_assembly.context,
            response=answer,
            intent=intent,
        )

    async def _score_confidence(
        self,
        query: MedicalQuery,
        answer: str,
        citations: list[CitationEntry],
        intent: MedicalIntent,
    ) -> ConfidenceScore:
        return await self._confidence_engine.score(
            query=query.query,
            response=answer,
            citations=citations,
            intent=intent,
        )

    async def _validate_safety(
        self,
        query: MedicalQuery,
        answer: str,
        citations: list[CitationEntry],
        intent: MedicalIntent,
    ) -> SafetyCheckResult:
        if not self._settings.MEDICAL_SAFETY_ENABLED:
            return SafetyCheckResult(passed=True)
        return await self._safety_validator.validate(
            query=query.query,
            response=answer,
            citations=citations,
            intent=intent,
        )

    async def _build_response(
        self,
        answer: str,
        intent: MedicalIntent,
        reasoning: MedicalReasoning | None,
        citations: list[CitationEntry],
        confidence: ConfidenceScore,
        safety: SafetyCheckResult,
        metadata: MedicalMetadata,
        conversation_id: str | None,
    ) -> MedicalResponse:
        return await self._response_builder.build(
            answer=answer,
            intent=intent,
            reasoning=reasoning,
            citations=citations,
            confidence=confidence,
            safety=safety,
            metadata=metadata,
            conversation_id=conversation_id,
        )


class _DefaultContextOptimizer(ContextOptimizerABC):
    async def optimize(
        self,
        context: str,
        intent: MedicalIntent,
        max_tokens: int = 2048,
    ) -> MedicalContext:
        if not context:
            return MedicalContext(
                context="",
                token_count=0,
                chunk_count=0,
                truncated=False,
            )
        estimated_tokens = len(context) // 4
        truncated = estimated_tokens > max_tokens

        if truncated:
            max_chars = max_tokens * 4
            context = context[:max_chars]

        return MedicalContext(
            context=context,
            token_count=min(estimated_tokens, max_tokens),
            chunk_count=context.count("[Source"),
            truncated=truncated,
        )


class _DefaultMedicalPromptBuilder(MedicalPromptBuilderABC):
    async def build(
        self,
        query: str,
        context: str,
        intent: MedicalIntent,
    ) -> tuple[str, str]:
        system_message = DEFAULT_MEDICAL_SYSTEM_MESSAGE.replace("{context}", context)
        prompt_parts = [f"**Medical Query**: {query}"]
        prompt_parts.append(f"**Specialty Context**: {intent.specialty.value.replace('_', ' ')}")
        prompt_parts.append(f"**Urgency Level**: {intent.urgency.value}")

        if intent.intent_type != IntentType.GENERAL_INQUIRY:
            prompt_parts.append(
                f"**Intent**: This is a {intent.intent_type.value.replace('_', ' ')} query. "
                f"Tailor your response accordingly with appropriate clinical detail."
            )

        prompt = "\n\n".join(prompt_parts)
        return system_message, prompt
