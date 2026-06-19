import time
from typing import Any, AsyncGenerator

from app.ai.medical.response.builder.builder import StructuredResponseBuilder
from app.ai.medical.response.config.config import ResponseSettings
from app.ai.medical.response.exceptions.exceptions import ResponseOrchestrationError
from app.ai.medical.response.interfaces.interfaces import (
    PromptCompositionEngineABC,
    ResponseOrchestratorABC,
    StructuredResponseBuilderABC,
)
from app.ai.medical.response.prompts.composition import PromptCompositionEngine
from app.ai.medical.response.schemas.schemas import (
    GenerateRequest,
    GenerateResponse,
    ResponseMetadata,
    StreamChunk,
)
from app.ai.medical.reasoning.schemas.schemas import ReasoningPlan


def _timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


class ResponseOrchestrator(ResponseOrchestratorABC):
    def __init__(
        self,
        prompt_engine: PromptCompositionEngineABC | None = None,
        response_builder: StructuredResponseBuilderABC | None = None,
        settings: ResponseSettings | None = None,
    ):
        self._prompt_engine = prompt_engine or PromptCompositionEngine()
        self._response_builder = response_builder or StructuredResponseBuilder()
        self._settings = settings or ResponseSettings()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        stages: dict[str, float] = {}

        reasoning_plan = None
        if request.reasoning_plan:
            try:
                reasoning_plan = ReasoningPlan(**request.reasoning_plan)
            except Exception:
                reasoning_plan = None

        stage_start = time.time()
        try:
            composition = await self._prompt_engine.compose(
                query=request.query,
                reasoning_plan=reasoning_plan,
                assembled_prompt=request.assembled_prompt,
                temperature=request.temperature or self._settings.RESPONSE_DEFAULT_TEMPERATURE,
                max_tokens=request.max_tokens or self._settings.RESPONSE_DEFAULT_MAX_TOKENS,
                conversation_id=request.conversation_id,
            )
            stages["prompt_composition"] = _timing_ms(stage_start)
        except Exception as e:
            raise ResponseOrchestrationError(f"Prompt composition failed: {e}")

        stage_start = time.time()
        try:
            gateway_result = await self._prompt_engine.execute_gateway(
                composition["gateway_request"],
            )
            stages["llm_generation"] = _timing_ms(stage_start)
        except Exception as e:
            if self._settings.RESPONSE_FALLBACK_ON_ERROR:
                return self._build_fallback(request, str(e))
            raise ResponseOrchestrationError(f"LLM generation failed: {e}")

        stage_start = time.time()
        try:
            response = await self._response_builder.build(
                raw_content=gateway_result["content"],
                reasoning_plan=reasoning_plan,
                query=request.query,
                conversation_id=request.conversation_id,
            )
            stages["response_building"] = _timing_ms(stage_start)
        except Exception as e:
            raise ResponseOrchestrationError(f"Response building failed: {e}")

        total_time = sum(v for v in stages.values())
        response.metadata = ResponseMetadata(
            model=gateway_result.get("model", ""),
            provider=gateway_result.get("provider", ""),
            usage=gateway_result.get("usage"),
            processing_time_ms=total_time,
            generation_time_ms=stages.get("llm_generation", 0),
            pipeline_stages=stages,
            finish_reason=gateway_result.get("finish_reason"),
            streaming=False,
        )
        response.processing_time_ms = total_time
        response.metadata = response.metadata

        return response

    async def generate_stream(
        self,
        request: GenerateRequest,
    ) -> AsyncGenerator[StreamChunk, None]:
        reasoning_plan = None
        if request.reasoning_plan:
            try:
                reasoning_plan = ReasoningPlan(**request.reasoning_plan)
            except Exception:
                reasoning_plan = None

        composition = await self._prompt_engine.compose(
            query=request.query,
            reasoning_plan=reasoning_plan,
            assembled_prompt=request.assembled_prompt,
            temperature=request.temperature or self._settings.RESPONSE_DEFAULT_TEMPERATURE,
            max_tokens=request.max_tokens or self._settings.RESPONSE_DEFAULT_MAX_TOKENS,
            conversation_id=request.conversation_id,
        )

        try:
            gateway = await self._get_gateway()
            full_content = ""
            async for chunk in gateway.execute_stream(composition["gateway_request"]):
                full_content += chunk
                yield StreamChunk(content=chunk, done=False)

            try:
                response = await self._response_builder.build(
                    raw_content=full_content,
                    reasoning_plan=reasoning_plan,
                    query=request.query,
                    conversation_id=request.conversation_id,
                )
                yield StreamChunk(
                    content="",
                    done=True,
                    finish_reason="completed",
                )
            except Exception:
                yield StreamChunk(
                    content="",
                    done=True,
                    finish_reason="completed",
                )
        except Exception as e:
            if self._settings.RESPONSE_FALLBACK_ON_ERROR:
                yield StreamChunk(
                    content=self._settings.RESPONSE_FALLBACK_MESSAGE,
                    done=True,
                    finish_reason="fallback",
                )
            else:
                raise ResponseOrchestrationError(f"Streaming generation failed: {e}")

    async def _get_gateway(self):
        from app.ai.gateway.deps import get_gateway

        return get_gateway()

    def _build_fallback(self, request: GenerateRequest, reason: str) -> GenerateResponse:
        return GenerateResponse(
            query=request.query,
            answer=self._settings.RESPONSE_FALLBACK_MESSAGE,
            conversation_id=request.conversation_id,
            metadata=ResponseMetadata(
                processing_time_ms=0,
                finish_reason="fallback",
            ),
            limitations=[reason],
        )
