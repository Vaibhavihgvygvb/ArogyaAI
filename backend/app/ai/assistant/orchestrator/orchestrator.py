import time
from typing import Any

from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.exceptions.exceptions import (
    EmergencyEscalationError,
    OrchestratorError,
)
from app.ai.assistant.interfaces.interfaces import (
    AssistantOrchestratorABC,
    ContextManagerABC,
    ConversationManagerABC,
    PersonalizationManagerABC,
    ResponseFormatterABC,
    SessionManagerABC,
)
from app.ai.assistant.prompts.templates import (
    ASSISTANT_SYSTEM_MESSAGE,
    CONTINUATION_MESSAGE,
    EXPLAIN_TERM_MESSAGE,
    SUMMARIZE_CONVERSATION_MESSAGE,
)
from app.ai.assistant.schemas.schemas import (
    AssistantMessage,
    ChatRequest,
    ChatResponse,
    ContinueRequest,
    ConversationState,
    ExplainRequest,
    ExplainResponse,
    HistoryRequest,
    HistoryResponse,
    MessageRole,
    PersonalizationPreferences,
    ResetRequest,
    ResetResponse,
    SessionMetadata,
    SummarizeRequest,
    SummarizeResponse,
)
from app.ai.assistant.utils.utils import extract_topics, timing_ms
from app.ai.assistant.validators.validators import AssistantValidator
from app.ai.exceptions.exceptions import SafetyError
from app.ai.gateway.deps import get_gateway
from app.ai.gateway.pipeline import GatewayRequest
from app.ai.interfaces.gateway_service import GatewayService


class AssistantOrchestrator(AssistantOrchestratorABC):

    def __init__(
        self,
        conversation_manager: ConversationManagerABC,
        session_manager: SessionManagerABC,
        context_manager: ContextManagerABC,
        personalization_manager: PersonalizationManagerABC,
        response_formatter: ResponseFormatterABC,
        gateway: GatewayService | None = None,
        settings: AssistantSettings | None = None,
        validator: AssistantValidator | None = None,
    ):
        self._conversation_manager = conversation_manager
        self._session_manager = session_manager
        self._context_manager = context_manager
        self._personalization_manager = personalization_manager
        self._response_formatter = response_formatter
        self._gateway = gateway or get_gateway()
        self._settings = settings or AssistantSettings()
        self._validator = validator or AssistantValidator(settings=settings)

    async def chat(self, request: ChatRequest, user_id: int) -> ChatResponse:
        start = time.time()

        await self._validator.validate_chat_request(request)

        session, is_new_session = await self._resolve_session(request.session_id, user_id)
        conversation_id, is_new_conversation = await self._resolve_conversation(
            request.conversation_id, session, user_id
        )

        await self._session_manager.update_session(session.session_id, {
            "conversation_id": conversation_id,
        })

        topics = extract_topics(request.message)

        user_message = await self._conversation_manager.add_message(
            conversation_id, "user", request.message,
            metadata={"topics": topics, "session_id": session.session_id},
        )
        await self._context_manager.update_context(conversation_id, user_message)

        personalization_prefs = await self._personalization_manager.get_preferences(session.session_id)
        if request.audience:
            personalization_prefs.audience = request.audience
        if request.language:
            personalization_prefs.language = request.language

        personalized_query = await self._personalization_manager.personalize_query(
            session.session_id, request.message
        )

        if self._settings.ASSISTANT_ENABLE_EMERGENCY_DETECTION:
            emergency_result = await self._detect_emergency(request.message)
            if emergency_result:
                emergency_response = await self._build_emergency_response(
                    conversation_id, session, emergency_result, start
                )
                return emergency_response

        context = await self._context_manager.build_medical_context(conversation_id, session)

        messages = self._build_chat_messages(personalized_query, conversation_id, context, session)

        temperature = request.temperature or self._settings.ASSISTANT_DEFAULT_TEMPERATURE
        max_tokens = request.max_tokens or self._settings.ASSISTANT_DEFAULT_MAX_TOKENS

        gateway_request = GatewayRequest(
            messages=messages,
            conversation_id=conversation_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            gateway_response = await self._gateway.execute(gateway_request)
        except SafetyError as e:
            raise OrchestratorError(f"Safety check failed: {e}")
        except Exception as e:
            return await self._build_fallback_response(
                conversation_id, session, str(e), start
            )

        answer = gateway_response.content

        citations_list = []
        if self._settings.ASSISTANT_REQUIRE_CITATIONS:
            citations_list = self._extract_citations(answer)

        assistant_message = await self._conversation_manager.add_message(
            conversation_id, "assistant", answer,
            metadata={"citations": citations_list, "session_id": session.session_id},
        )
        await self._context_manager.update_context(conversation_id, assistant_message)

        formatted = await self._response_formatter.format_chat_response(
            ChatResponse(conversation_id=conversation_id, session_id=session.session_id, message=answer),
            personalization_prefs,
        )

        if personalization_prefs.audience != "doctor":
            answer = await self._response_formatter.simplify_for_audience(answer, personalization_prefs.audience)

        takeways = await self._response_formatter.extract_key_takeaways(answer)
        follow_ups = await self._response_formatter.generate_follow_up_questions(answer)
        actions = await self._response_formatter.generate_recommended_actions(answer)

        await self._session_manager.touch_session(session.session_id)

        disclaimers = []
        if personalization_prefs.include_disclaimers:
            disclaimers.append("This information is for educational purposes only. Consult a healthcare professional for medical advice.")

        elapsed = timing_ms(start)

        return ChatResponse(
            conversation_id=conversation_id,
            session_id=session.session_id,
            message=answer,
            formatted_response=formatted,
            topics=topics,
            citations=citations_list,
            disclaimers=disclaimers,
            key_takeaways=takeways,
            follow_up_questions=follow_ups,
            recommended_actions=actions,
            has_emergency=False,
            processing_time_ms=elapsed,
            safety_passed=True,
        )

    async def continue_conversation(self, request: ContinueRequest, user_id: int) -> ChatResponse:
        start = time.time()

        await self._validator.validate_continue_request(request)

        conversation = await self._conversation_manager.get_conversation(request.conversation_id)
        if not conversation:
            raise OrchestratorError(f"Conversation '{request.conversation_id}' not found")

        session_id = request.session_id
        if session_id:
            session = await self._session_manager.get_session(session_id)
            if not session or session.user_id != user_id:
                raise OrchestratorError("Invalid session")
        else:
            sessions = await self._session_manager.list_sessions(user_id)
            matching = [s for s in sessions if s.conversation_id == request.conversation_id]
            if matching:
                session = matching[0]
                session_id = session.session_id
            else:
                session = await self._session_manager.create_session(user_id, {"conversation_id": request.conversation_id})
                session_id = session.session_id

        instructions = request.instructions or "Please continue your response."
        context = await self._context_manager.build_medical_context(request.conversation_id, session)
        continuation_prompt = CONTINUATION_MESSAGE.format(context=context, instructions=instructions)

        temperature = request.temperature or self._settings.ASSISTANT_DEFAULT_TEMPERATURE
        max_tokens = request.max_tokens or self._settings.ASSISTANT_DEFAULT_MAX_TOKENS

        gateway_request = GatewayRequest(
            messages=[{"role": "user", "content": continuation_prompt}],
            conversation_id=request.conversation_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            gateway_response = await self._gateway.execute(gateway_request)
        except Exception as e:
            return await self._build_fallback_response(
                request.conversation_id, session, str(e), start
            )

        answer = gateway_response.content

        assistant_message = await self._conversation_manager.add_message(
            request.conversation_id, "assistant", answer,
        )

        formatted = await self._response_formatter.format_chat_response(
            ChatResponse(conversation_id=request.conversation_id, session_id=session_id, message=answer),
        )

        await self._session_manager.touch_session(session_id)

        elapsed = timing_ms(start)
        return ChatResponse(
            conversation_id=request.conversation_id,
            session_id=session_id,
            message=answer,
            formatted_response=formatted,
            processing_time_ms=elapsed,
        )

    async def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        start = time.time()

        conversation = await self._conversation_manager.get_conversation(request.conversation_id)
        if not conversation:
            raise OrchestratorError(f"Conversation '{request.conversation_id}' not found")

        messages = await self._conversation_manager.get_messages(request.conversation_id)
        if not messages:
            return SummarizeResponse(
                conversation_id=request.conversation_id,
                summary="No messages in this conversation.",
                title=conversation.title,
                message_count=0,
                processing_time_ms=timing_ms(start),
            )

        messages_text = "\n".join(
            f"{m.role.value}: {m.content[:200]}"
            for m in messages[-20:]
        )
        summary_prompt = SUMMARIZE_CONVERSATION_MESSAGE.format(messages=messages_text)

        gateway_request = GatewayRequest(
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.5,
            max_tokens=512,
        )

        try:
            gateway_response = await self._gateway.execute(gateway_request)
            summary = gateway_response.content
        except Exception:
            conversation_summary = await self._conversation_manager.generate_summary(request.conversation_id)
            summary = conversation_summary.summary or "Summary unavailable."

        user_messages = [m for m in messages if m.role == MessageRole.USER]
        topics = set()
        for m in user_messages:
            if m.metadata and "topics" in m.metadata:
                topics.update(m.metadata["topics"])

        title = user_messages[0].content[:80] + "..." if user_messages else "Conversation"
        key_points = []
        for m in messages[-5:]:
            if m.role == MessageRole.ASSISTANT:
                lines = m.content.split("\n")
                for line in lines[:3]:
                    stripped = line.strip().strip("*").strip("-").strip()
                    if stripped and len(stripped) > 20 and len(stripped) < 200:
                        key_points.append(stripped)
                        break

        elapsed = timing_ms(start)
        return SummarizeResponse(
            conversation_id=request.conversation_id,
            summary=summary,
            title=title,
            message_count=len(messages),
            topics=list(topics),
            key_points=key_points[:5],
            processing_time_ms=elapsed,
        )

    async def explain_term(self, request: ExplainRequest) -> ExplainResponse:
        start = time.time()

        await self._validator.validate_explain_request(request)

        audience = request.audience or "patient"
        prompt = EXPLAIN_TERM_MESSAGE.format(term=request.term, audience=audience)

        conversation_id = request.conversation_id
        context = ""
        if conversation_id:
            session_id = request.session_id or ""
            session = SessionMetadata(
                session_id=session_id,
                user_id=0,
                preferred_audience=audience,
            )
            context = await self._context_manager.build_medical_context(conversation_id, session)

        messages = [{"role": "user", "content": prompt}]
        if context:
            messages.insert(0, {"role": "system", "content": f"Conversation context:\n{context}"})

        gateway_request = GatewayRequest(
            messages=messages,
            temperature=0.5,
            max_tokens=512,
        )

        try:
            gateway_response = await self._gateway.execute(gateway_request)
            explanation = gateway_response.content
        except Exception as e:
            explanation = f"Unable to explain '{request.term}' at this time."

        elapsed = timing_ms(start)
        return ExplainResponse(
            term=request.term,
            plain_english=explanation,
            audience=audience,
            processing_time_ms=elapsed,
        )

    async def get_history(self, request: HistoryRequest) -> HistoryResponse:
        start = time.time()

        conversation = await self._conversation_manager.get_conversation(request.conversation_id)
        if not conversation:
            raise OrchestratorError(f"Conversation '{request.conversation_id}' not found")

        messages = await self._conversation_manager.get_messages(request.conversation_id)
        total_tokens = sum(m.token_count for m in messages)

        elapsed = timing_ms(start)
        return HistoryResponse(
            conversation_id=request.conversation_id,
            messages=messages,
            summary=conversation,
            total_messages=len(messages),
            total_tokens=total_tokens,
            processing_time_ms=elapsed,
        )

    async def reset(self, request: ResetRequest, user_id: int) -> ResetResponse:
        prev_conv_reset = False
        prev_session_reset = False

        if request.conversation_id:
            result = await self._conversation_manager.delete_conversation(request.conversation_id)
            prev_conv_reset = result

        if request.session_id:
            result = await self._session_manager.delete_session(request.session_id)
            prev_session_reset = result
        elif not request.conversation_id:
            sessions = await self._session_manager.list_sessions(user_id)
            for s in sessions:
                await self._session_manager.delete_session(s.session_id)
            prev_session_reset = True

        new_session = await self._session_manager.create_session(user_id)
        new_conversation_id = await self._conversation_manager.create_conversation(
            user_id, new_session.session_id,
        )
        await self._session_manager.update_session(new_session.session_id, {
            "conversation_id": new_conversation_id,
        })

        return ResetResponse(
            session_id=new_session.session_id,
            new_conversation_id=new_conversation_id,
            previous_conversation_reset=prev_conv_reset,
            previous_session_reset=prev_session_reset,
        )

    async def _resolve_session(self, session_id: str | None, user_id: int) -> tuple[SessionMetadata, bool]:
        if session_id:
            session = await self._session_manager.get_session(session_id)
            if session:
                if session.user_id != user_id:
                    raise OrchestratorError("Session belongs to a different user")
                return session, False

        sessions = await self._session_manager.list_sessions(user_id)
        active = [s for s in sessions if s.conversation_id is not None]
        if active:
            return active[0], False

        session = await self._session_manager.create_session(user_id)
        return session, True

    async def _resolve_conversation(
        self, conversation_id: str | None, session: SessionMetadata, user_id: int,
    ) -> tuple[str, bool]:
        if conversation_id:
            conv = await self._conversation_manager.get_conversation(conversation_id)
            if conv:
                return conversation_id, False

        if session.conversation_id:
            conv = await self._conversation_manager.get_conversation(session.conversation_id)
            if conv:
                return session.conversation_id, False

        conversation_id = await self._conversation_manager.create_conversation(
            user_id, session.session_id,
        )
        return conversation_id, True

    async def _detect_emergency(self, message: str) -> dict | None:
        emergency_patterns = [
            ("chest_pain", ["chest pain", "chest pressure", "tightness in chest", "heart attack"]),
            ("stroke", ["stroke", "facial droop", "slurred speech", "weakness on one side"]),
            ("severe_bleeding", ["severe bleeding", "uncontrolled bleeding", "heavy bleeding", "gushing blood"]),
            ("suicidal", ["suicide", "kill myself", "end my life", "want to die", "self-harm"]),
            ("anaphylaxis", ["anaphylaxis", "severe allergic", "difficulty breathing", "throat closing"]),
            ("respiratory", ["can't breathe", "shortness of breath", "gasping for air", "respiratory distress"]),
            ("unconscious", ["unconscious", "passed out", "fainted", "loss of consciousness", "not responding"]),
            ("overdose", ["overdose", "poisoning", "too much medication", "accidental ingestion"]),
        ]
        message_lower = message.lower()
        for emergency_type, patterns in emergency_patterns:
            for pattern in patterns:
                if pattern in message_lower:
                    return {"type": emergency_type, "matched": pattern}
        return None

    async def _build_emergency_response(
        self, conversation_id: str, session: SessionMetadata, emergency: dict, start: float
    ) -> ChatResponse:
        emergency_message = self._settings.ASSISTANT_EMERGENCY_MESSAGE
        await self._conversation_manager.add_message(
            conversation_id, "assistant", emergency_message,
            metadata={"emergency": emergency, "session_id": session.session_id},
        )
        await self._conversation_manager.update_state(conversation_id, ConversationState.ESCALATED)
        await self._session_manager.update_session(session.session_id, {
            "safety_flags": [f"emergency_{emergency['type']}"],
        })

        elapsed = timing_ms(start)
        return ChatResponse(
            conversation_id=conversation_id,
            session_id=session.session_id,
            message=emergency_message,
            formatted_response=f"\n{emergency_message}\n",
            has_emergency=True,
            emergency_message=emergency_message,
            requires_escalation=True,
            safety_passed=True,
            processing_time_ms=elapsed,
        )

    async def _build_fallback_response(
        self, conversation_id: str, session: SessionMetadata, error: str, start: float
    ) -> ChatResponse:
        fallback = self._settings.ASSISTANT_FALLBACK_MESSAGE
        await self._conversation_manager.add_message(
            conversation_id, "assistant", fallback,
            metadata={"error": error, "session_id": session.session_id},
        )
        elapsed = timing_ms(start)
        return ChatResponse(
            conversation_id=conversation_id,
            session_id=session.session_id,
            message=fallback,
            formatted_response=fallback,
            processing_time_ms=elapsed,
            safety_passed=True,
        )

    async def _build_chat_messages(
        self, query: str, conversation_id: str, context: str, session: SessionMetadata,
    ) -> list[dict]:
        system_message = ASSISTANT_SYSTEM_MESSAGE

        if context:
            system_message += f"\n\n## Current Conversation Context\n{context}"

        if session.preferred_audience and session.preferred_audience != "patient":
            system_message += f"\n\n## Audience\nTailor your response for a **{session.preferred_audience}** audience."

        if session.medical_specialty:
            system_message += f"\n\n## Active Medical Specialty\n{session.medical_specialty}"

        messages = [{"role": "system", "content": system_message}]

        recent = await self._conversation_manager.get_messages(conversation_id, limit=10)
        if recent:
            pass

        messages.append({"role": "user", "content": query})
        return messages

    def _extract_citations(self, text: str) -> list[dict]:
        citations = []
        ref_pattern = r"\[(\d+)\]"
        matches = set()
        for match in re.finditer(ref_pattern, text):
            matches.add(match.group(1))
        for ref_num in sorted(matches):
            citations.append({"reference_number": int(ref_num), "source": f"Reference {ref_num}"})
        return citations


import re
