from app.ai.gateway.deps import get_gateway
from app.ai.interfaces.gateway_service import GatewayRequest
from app.ai.medical.response.exceptions.exceptions import PromptCompositionError
from app.ai.medical.response.interfaces.interfaces import PromptCompositionEngineABC
from app.ai.medical.reasoning.schemas.schemas import ReasoningPlan


class PromptCompositionEngine(PromptCompositionEngineABC):
    async def compose(
        self,
        query: str,
        reasoning_plan: ReasoningPlan | None = None,
        assembled_prompt: dict | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        if not query or not query.strip():
            raise PromptCompositionError("Query cannot be empty")

        messages: list[dict] = []
        kw_temperature = temperature
        kw_max_tokens = max_tokens

        if assembled_prompt:
            system_message = assembled_prompt.get("system_message", "")
            user_prompt = assembled_prompt.get("user_prompt", "")
            if system_message:
                messages.append({"role": "system", "content": system_message})
            if user_prompt:
                messages.append({"role": "user", "content": user_prompt})

        if not messages:
            messages.append({"role": "user", "content": query})

        if reasoning_plan and reasoning_plan.disclaimer:
            if messages and messages[-1]["role"] == "user":
                existing = messages[-1]["content"]
                messages[-1]["content"] = f"{existing}\n\nNote: {reasoning_plan.disclaimer}"

        gateway_request = GatewayRequest(
            conversation_id=conversation_id,
            messages=messages,
            stream=False,
            temperature=kw_temperature,
            max_tokens=kw_max_tokens,
        )

        return {
            "gateway_request": gateway_request,
            "messages": messages,
            "temperature": kw_temperature,
            "max_tokens": kw_max_tokens,
        }

    async def execute_gateway(self, gateway_request: GatewayRequest) -> dict:
        try:
            gateway = get_gateway()
            response = await gateway.execute(gateway_request)
            return {
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "usage": response.usage,
                "finish_reason": response.finish_reason,
            }
        except Exception as e:
            raise PromptCompositionError(f"Gateway execution failed: {e}")
