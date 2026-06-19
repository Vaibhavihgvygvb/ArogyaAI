import time
from typing import Any, AsyncGenerator

from app.ai.medical.response.config.config import ResponseSettings
from app.ai.medical.response.exceptions.exceptions import ResponsePipelineError
from app.ai.medical.response.interfaces.interfaces import (
    ResponseOrchestratorABC,
    ResponsePipelineABC,
)
from app.ai.medical.response.orchestrator.orchestrator import ResponseOrchestrator
from app.ai.medical.response.schemas.schemas import (
    GenerateRequest,
    GenerateResponse,
    StreamChunk,
)


def _timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


class ResponsePipeline(ResponsePipelineABC):
    def __init__(
        self,
        orchestrator: ResponseOrchestratorABC | None = None,
        settings: ResponseSettings | None = None,
    ):
        self._settings = settings or ResponseSettings()
        self._orchestrator = orchestrator or ResponseOrchestrator(settings=self._settings)

    async def run(self, request: GenerateRequest) -> GenerateResponse:
        start = time.time()

        if not request.query or not request.query.strip():
            raise ResponsePipelineError("Query cannot be empty")

        try:
            response = await self._orchestrator.generate(request)
        except Exception as e:
            if self._settings.RESPONSE_FALLBACK_ON_ERROR:
                return GenerateResponse(
                    query=request.query,
                    answer=self._settings.RESPONSE_FALLBACK_MESSAGE,
                    conversation_id=request.conversation_id,
                    processing_time_ms=_timing_ms(start),
                )
            raise ResponsePipelineError(f"Generation failed: {e}")

        response.processing_time_ms = _timing_ms(start)
        return response

    async def run_stream(
        self,
        request: GenerateRequest,
    ) -> AsyncGenerator[StreamChunk, None]:
        if not request.query or not request.query.strip():
            raise ResponsePipelineError("Query cannot be empty")

        async for chunk in self._orchestrator.generate_stream(request):
            yield chunk
