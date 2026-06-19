import time
from typing import AsyncGenerator

from app.ai.medical.response.config.config import ResponseSettings
from app.ai.medical.response.exceptions.exceptions import ResponseServiceError
from app.ai.medical.response.interfaces.interfaces import ResponseServiceABC
from app.ai.medical.response.pipelines.pipelines import ResponsePipeline
from app.ai.medical.response.schemas.schemas import GenerateRequest, GenerateResponse, StreamChunk


class ResponseService(ResponseServiceABC):
    def __init__(
        self,
        pipeline: ResponsePipeline | None = None,
        settings: ResponseSettings | None = None,
    ):
        self._settings = settings or ResponseSettings()
        self._pipeline = pipeline or ResponsePipeline(settings=self._settings)

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        if not request.query or not request.query.strip():
            raise ResponseServiceError("Query cannot be empty")

        try:
            response = await self._pipeline.run(request)
            return response
        except Exception as e:
            if self._settings.RESPONSE_FALLBACK_ON_ERROR:
                return GenerateResponse(
                    query=request.query,
                    answer=self._settings.RESPONSE_FALLBACK_MESSAGE,
                    conversation_id=request.conversation_id,
                )
            raise ResponseServiceError(f"Generation failed: {e}")

    async def generate_stream(
        self,
        request: GenerateRequest,
    ) -> AsyncGenerator[StreamChunk, None]:
        if not request.query or not request.query.strip():
            raise ResponseServiceError("Query cannot be empty")

        async for chunk in self._pipeline.run_stream(request):
            yield chunk
