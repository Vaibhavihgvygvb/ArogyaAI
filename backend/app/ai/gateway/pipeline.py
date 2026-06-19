from typing import AsyncGenerator

from app.ai.interfaces.gateway_service import GatewayService, GatewayRequest, GatewayResponse
from app.ai.interfaces.llm_provider import LLMProvider
from app.ai.interfaces.prompt_manager import PromptManager
from app.ai.interfaces.memory_manager import MemoryManager
from app.ai.interfaces.safety_service import SafetyService
from app.ai.exceptions.exceptions import SafetyError, GatewayError, ContextWindowExceeded
from app.ai.utils.token_counter import estimate_messages_tokens
from app.core.config import settings


class GatewayPipeline(GatewayService):

    def __init__(
        self,
        provider: LLMProvider,
        prompt_manager: PromptManager,
        memory_manager: MemoryManager,
        safety_service: SafetyService,
    ):
        self._provider = provider
        self._prompt_manager = prompt_manager
        self._memory_manager = memory_manager
        self._safety_service = safety_service

    async def execute(self, request: GatewayRequest) -> GatewayResponse:
        messages = await self._build_messages(request)
        combined_text = " ".join(m.get("content", "") for m in messages if m.get("content"))
        safety_result = await self._safety_service.check_safety(combined_text)
        if not safety_result.passed:
            raise SafetyError(f"Safety check failed: {safety_result.reason}")

        if request.conversation_id:
            for msg in messages:
                await self._memory_manager.add_message(
                    request.conversation_id,
                    msg["role"],
                    msg["content"],
                )

        kwargs = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens

        response = await self._provider.generate(messages, **kwargs)

        output_check = await self._safety_service.validate_output(response.content)
        if not output_check.passed:
            raise SafetyError(f"Output safety check failed: {output_check.reason}")

        if request.conversation_id:
            await self._memory_manager.add_message(
                request.conversation_id,
                "assistant",
                response.content,
                token_count=response.usage.get("completion_tokens", 0) if response.usage else 0,
            )

        return GatewayResponse(
            content=response.content,
            conversation_id=request.conversation_id or "",
            model=response.model,
            provider=response.provider,
            usage=response.usage,
            finish_reason=response.finish_reason,
        )

    async def execute_stream(self, request: GatewayRequest) -> AsyncGenerator[str, None]:
        messages = await self._build_messages(request)
        combined_text = " ".join(m.get("content", "") for m in messages if m.get("content"))
        safety_result = await self._safety_service.check_safety(combined_text)
        if not safety_result.passed:
            raise SafetyError(f"Safety check failed: {safety_result.reason}")

        if request.conversation_id:
            for msg in messages:
                await self._memory_manager.add_message(
                    request.conversation_id,
                    msg["role"],
                    msg["content"],
                )

        kwargs = {"stream": True}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens

        full_content = ""
        async for chunk in self._provider.generate_stream(messages, **kwargs):
            full_content += chunk
            yield chunk

        output_check = await self._safety_service.validate_output(full_content)
        if not output_check.passed:
            raise SafetyError(f"Output safety check failed: {output_check.reason}")

    async def _build_messages(self, request: GatewayRequest) -> list[dict]:
        if request.messages:
            return [
                {"role": m.role if hasattr(m, "role") else m["role"], "content": m.content if hasattr(m, "content") else m["content"]}
                for m in request.messages
            ]
        if request.prompt_name and request.prompt_variables is not None:
            prompt_content = await self._prompt_manager.render_prompt(
                request.prompt_name, request.prompt_variables,
            )
            return [{"role": "user", "content": prompt_content}]
        if request.conversation_id:
            return await self._memory_manager.get_context(
                request.conversation_id,
                max_tokens=settings.AI.MEMORY_MAX_TOKENS,
            )
        raise GatewayError("No messages, prompt, or conversation provided")
