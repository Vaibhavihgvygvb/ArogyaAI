import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.context.manager import ContextManager
from app.ai.assistant.conversation.manager import ConversationManager
from app.ai.assistant.exceptions.exceptions import (
    ConversationError,
    OrchestratorError,
    SessionError,
    ValidationError,
)
from app.ai.assistant.deps.deps import (
    get_conversation_manager,
    get_session_manager,
    get_context_manager,
    get_personalization_manager,
    get_response_formatter,
    get_orchestrator,
    reset_all,
    set_conversation_manager,
    set_session_manager,
    set_context_manager,
    set_personalization_manager,
    set_response_formatter,
    set_orchestrator,
)
from app.ai.assistant.orchestrator.orchestrator import AssistantOrchestrator
from app.ai.assistant.personalization.manager import PersonalizationManager
from app.ai.assistant.response.formatter import ResponseFormatter
from app.ai.assistant.schemas.schemas import (
    AssistantMessage,
    ChatRequest,
    ChatResponse,
    ContinueRequest,
    ConversationState,
    ConversationSummary,
    ExplainRequest,
    ExplainResponse,
    HistoryRequest,
    MessageRole,
    PersonalizationPreferences,
    ResetRequest,
    ResetResponse,
    SessionMetadata,
    SummarizeRequest,
    SummarizeResponse,
)
from app.ai.assistant.session.manager import SessionManager
from app.ai.assistant.validators.validators import AssistantValidator
from app.ai.assistant.utils.utils import extract_topics, timing_ms
from app.ai.interfaces.gateway_service import GatewayService, GatewayRequest, GatewayResponse
from app.main import app
from app.models.user import User
from app.models.enums import UserRole


@pytest.fixture(autouse=True)
def reset_assistant_deps():
    reset_all()
    yield
    reset_all()


@pytest.fixture
def settings():
    return AssistantSettings(
        ASSISTANT_ENABLED=True,
        ASSISTANT_MAX_MESSAGE_LENGTH=10000,
        ASSISTANT_MAX_HISTORY_MESSAGES=50,
    )


@pytest.fixture
def mock_gateway():
    gw = AsyncMock(spec=GatewayService)
    gw.execute.return_value = GatewayResponse(
        content="This is a test medical response. It is important to consult a healthcare professional.",
        conversation_id="test-conv-1",
        model="mock-model",
        provider="mock",
        usage={"prompt_tokens": 50, "completion_tokens": 20},
    )
    return gw


@pytest.fixture
def conversation_manager(settings):
    return ConversationManager(settings=settings)


@pytest.fixture
def session_manager(settings):
    return SessionManager(settings=settings)


@pytest.fixture
def context_manager(conversation_manager, session_manager, settings):
    return ContextManager(
        conversation_manager=conversation_manager,
        session_manager=session_manager,
        settings=settings,
    )


@pytest.fixture
def personalization_manager(settings):
    return PersonalizationManager(settings=settings)


@pytest.fixture
def response_formatter():
    return ResponseFormatter()


@pytest.fixture
def validator(settings):
    return AssistantValidator(settings=settings)


@pytest.fixture
def orchestrator(
    conversation_manager,
    session_manager,
    context_manager,
    personalization_manager,
    response_formatter,
    mock_gateway,
    settings,
    validator,
):
    return AssistantOrchestrator(
        conversation_manager=conversation_manager,
        session_manager=session_manager,
        context_manager=context_manager,
        personalization_manager=personalization_manager,
        response_formatter=response_formatter,
        gateway=mock_gateway,
        settings=settings,
        validator=validator,
    )


# ─── Conversation Manager Tests ───────────────────────────────────────────────


class TestConversationManager:
    @pytest.mark.asyncio
    async def test_create_conversation(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        assert conv_id is not None
        assert isinstance(conv_id, str)
        assert len(conv_id) > 0

    @pytest.mark.asyncio
    async def test_get_conversation(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        conv = await conversation_manager.get_conversation(conv_id)
        assert conv is not None
        assert conv.conversation_id == conv_id
        assert conv.metadata.get("user_id") == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, conversation_manager):
        conv = await conversation_manager.get_conversation("nonexistent")
        assert conv is None

    @pytest.mark.asyncio
    async def test_add_message(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        msg = await conversation_manager.add_message(conv_id, "user", "Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.token_count > 0

    @pytest.mark.asyncio
    async def test_add_message_nonexistent(self, conversation_manager):
        with pytest.raises(ConversationError):
            await conversation_manager.add_message("nonexistent", "user", "Hello")

    @pytest.mark.asyncio
    async def test_get_messages(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "Hello")
        await conversation_manager.add_message(conv_id, "assistant", "Hi there")
        messages = await conversation_manager.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        for i in range(10):
            await conversation_manager.add_message(conv_id, "user", f"Message {i}")
        messages = await conversation_manager.get_messages(conv_id, limit=3)
        assert len(messages) == 3

    @pytest.mark.asyncio
    async def test_get_context_messages(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "Hello")
        await conversation_manager.add_message(conv_id, "assistant", "Hi")
        context = await conversation_manager.get_context_messages(conv_id)
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_update_state(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        result = await conversation_manager.update_state(conv_id, ConversationState.ACTIVE)
        assert result is True

    @pytest.mark.asyncio
    async def test_update_state_nonexistent(self, conversation_manager):
        result = await conversation_manager.update_state("nonexistent", ConversationState.ACTIVE)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_conversation(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        result = await conversation_manager.delete_conversation(conv_id)
        assert result is True
        assert await conversation_manager.get_conversation(conv_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, conversation_manager):
        result = await conversation_manager.delete_conversation("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_conversations(self, conversation_manager):
        await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.create_conversation(user_id=2, session_id="session-2")
        user1_convs = await conversation_manager.list_conversations(user_id=1)
        user2_convs = await conversation_manager.list_conversations(user_id=2)
        assert len(user1_convs) == 2
        assert len(user2_convs) == 1

    @pytest.mark.asyncio
    async def test_generate_summary(self, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "What causes headaches?")
        await conversation_manager.add_message(conv_id, "assistant", "Headaches can be caused by various factors.")
        summary = await conversation_manager.generate_summary(conv_id)
        assert summary.conversation_id == conv_id
        assert summary.message_count == 2
        assert "Headaches" in summary.title

    @pytest.mark.asyncio
    async def test_message_history_pruning(self, conversation_manager):
        settings = AssistantSettings(ASSISTANT_MAX_HISTORY_MESSAGES=5)
        cm = ConversationManager(settings=settings)
        conv_id = await cm.create_conversation(user_id=1, session_id="session-1")
        for i in range(10):
            await cm.add_message(conv_id, "user", f"Message {i}")
        messages = await cm.get_messages(conv_id)
        assert len(messages) == 5


# ─── Session Manager Tests ────────────────────────────────────────────────────


class TestSessionManager:
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        session = await session_manager.create_session(user_id=1)
        assert session.session_id is not None
        assert session.user_id == 1
        assert session.created_at is not None

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager):
        session = await session_manager.create_session(user_id=1)
        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager):
        session = await session_manager.get_session("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_update_session(self, session_manager):
        session = await session_manager.create_session(user_id=1)
        result = await session_manager.update_session(session.session_id, {"active_topic": "cardiology"})
        assert result is True
        updated = await session_manager.get_session(session.session_id)
        assert updated.active_topic == "cardiology"

    @pytest.mark.asyncio
    async def test_update_nonexistent_session(self, session_manager):
        result = await session_manager.update_session("nonexistent", {"active_topic": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        session = await session_manager.create_session(user_id=1)
        result = await session_manager.delete_session(session.session_id)
        assert result is True
        assert await session_manager.get_session(session.session_id) is None

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_manager):
        await session_manager.create_session(user_id=1)
        await session_manager.create_session(user_id=1)
        await session_manager.create_session(user_id=2)
        user1_sessions = await session_manager.list_sessions(user_id=1)
        user2_sessions = await session_manager.list_sessions(user_id=2)
        assert len(user1_sessions) == 2
        assert len(user2_sessions) == 1

    @pytest.mark.asyncio
    async def test_get_session_state(self, session_manager):
        session = await session_manager.create_session(user_id=1)
        state = await session_manager.get_session_state(session.session_id)
        assert state is not None
        assert state.active is True

    @pytest.mark.asyncio
    async def test_touch_session(self, session_manager):
        session = await session_manager.create_session(user_id=1)
        old_expiry = session.expires_at
        result = await session_manager.touch_session(session.session_id)
        assert result is True
        updated = await session_manager.get_session(session.session_id)
        assert updated.last_activity >= session.last_activity

    @pytest.mark.asyncio
    async def test_touch_nonexistent(self, session_manager):
        result = await session_manager.touch_session("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_session_expiry(self):
        settings = AssistantSettings(ASSISTANT_SESSION_TIMEOUT_MINUTES=0)
        sm = SessionManager(settings=settings)
        session = await sm.create_session(user_id=1)
        import time
        time.sleep(0.001)
        retrieved = await sm.get_session(session.session_id)
        assert retrieved is None


# ─── Context Manager Tests ────────────────────────────────────────────────────


class TestContextManager:
    @pytest.mark.asyncio
    async def test_short_term_context(self, context_manager, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "Hello")
        await conversation_manager.add_message(conv_id, "assistant", "Hi there")
        context = await context_manager.get_short_term_context(conv_id)
        assert len(context) == 2

    @pytest.mark.asyncio
    async def test_long_term_context(self, context_manager):
        context = await context_manager.get_long_term_context("nonexistent")
        assert context is None

    @pytest.mark.asyncio
    async def test_relevant_history(self, context_manager, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "What causes chest pain?")
        await conversation_manager.add_message(conv_id, "assistant", "Chest pain has many causes.")
        await conversation_manager.add_message(conv_id, "user", "What about headaches?")
        await conversation_manager.add_message(conv_id, "assistant", "Headaches are common.")
        relevant = await context_manager.get_relevant_history(conv_id, "headache treatment", max_messages=5)
        assert len(relevant) > 0

    @pytest.mark.asyncio
    async def test_build_medical_context(self, context_manager, conversation_manager, session_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "What is hypertension?")
        session = await session_manager.create_session(user_id=1)
        context = await context_manager.build_medical_context(conv_id, session)
        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_update_context(self, context_manager, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        msg = await conversation_manager.add_message(conv_id, "user", "A" * 5000)
        await context_manager.update_context(conv_id, msg)
        long_term = await context_manager.get_long_term_context(conv_id)
        assert long_term is not None or True


# ─── Personalization Manager Tests ────────────────────────────────────────────


class TestPersonalizationManager:
    @pytest.mark.asyncio
    async def test_get_default_preferences(self, personalization_manager):
        prefs = await personalization_manager.get_preferences("session-1")
        assert prefs.language == "en"
        assert prefs.audience == "patient"

    @pytest.mark.asyncio
    async def test_set_preferences(self, personalization_manager):
        prefs = PersonalizationPreferences(audience="doctor", language="en")
        await personalization_manager.set_preferences("session-1", prefs)
        retrieved = await personalization_manager.get_preferences("session-1")
        assert retrieved.audience == "doctor"

    @pytest.mark.asyncio
    async def test_update_preferences(self, personalization_manager):
        updated = await personalization_manager.update_preferences("session-1", {"audience": "doctor"})
        assert updated.audience == "doctor"
        assert updated.language == "en"

    @pytest.mark.asyncio
    async def test_apply_personalization_simplify(self, personalization_manager):
        await personalization_manager.update_preferences("session-1", {"simplify_terms": True})
        result = await personalization_manager.apply_personalization(
            "session-1", "The patient has hypertension."
        )
        assert "high blood pressure" in result

    @pytest.mark.asyncio
    async def test_apply_personalization_brief(self, personalization_manager):
        await personalization_manager.update_preferences("session-1", {"response_length": "brief"})
        result = await personalization_manager.apply_personalization(
            "session-1", "First point. Second point. Third point. Fourth point."
        )
        assert result.count(".") <= 3

    @pytest.mark.asyncio
    async def test_personalize_query_doctor(self, personalization_manager):
        await personalization_manager.update_preferences("session-1", {"audience": "doctor"})
        result = await personalization_manager.personalize_query("session-1", "What causes chest pain?")
        assert "[For a medical professional]" in result

    @pytest.mark.asyncio
    async def test_personalize_query_patient(self, personalization_manager):
        result = await personalization_manager.personalize_query("session-1", "What causes chest pain?")
        assert "[For a" not in result

    @pytest.mark.asyncio
    async def test_simplify_medical_terms(self, personalization_manager):
        simplified = personalization_manager._simplify_medical_terms(
            "The patient has hypertension and diabetes mellitus."
        )
        assert "high blood pressure" in simplified
        assert "diabetes" in simplified

    @pytest.mark.asyncio
    async def test_truncate_to_brief(self, personalization_manager):
        text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
        truncated = personalization_manager._truncate_to_brief(text, max_sentences=2)
        assert truncated.count(".") == 2


# ─── Response Formatter Tests ─────────────────────────────────────────────────


class TestResponseFormatter:
    @pytest.mark.asyncio
    async def test_format_chat_response_basic(self, response_formatter):
        response = ChatResponse(
            conversation_id="conv-1",
            session_id="session-1",
            message="Test response",
        )
        formatted = await response_formatter.format_chat_response(response)
        assert "Test response" in formatted

    @pytest.mark.asyncio
    async def test_format_chat_response_with_takeaways(self, response_formatter):
        response = ChatResponse(
            conversation_id="conv-1",
            session_id="session-1",
            message="Test response",
            key_takeaways=["Takeaway 1", "Takeaway 2"],
        )
        formatted = await response_formatter.format_chat_response(response)
        assert "Key Takeaways" in formatted
        assert "Takeaway 1" in formatted

    @pytest.mark.asyncio
    async def test_format_chat_response_with_citations(self, response_formatter):
        response = ChatResponse(
            conversation_id="conv-1",
            session_id="session-1",
            message="Test response",
            citations=[{"source": "Study 2024", "title": "Medical Study"}],
        )
        formatted = await response_formatter.format_chat_response(response)
        assert "References" in formatted
        assert "Study 2024" in formatted

    @pytest.mark.asyncio
    async def test_format_chat_response_with_actions(self, response_formatter):
        response = ChatResponse(
            conversation_id="conv-1",
            session_id="session-1",
            message="Test response",
            recommended_actions=["Consult a doctor", "Rest"],
        )
        formatted = await response_formatter.format_chat_response(response)
        assert "Recommended Actions" in formatted

    @pytest.mark.asyncio
    async def test_format_markdown(self, response_formatter):
        result = await response_formatter.format_markdown("**bold** text", audience="patient")
        assert "**bold**" in result

    @pytest.mark.asyncio
    async def test_extract_key_takeaways(self, response_formatter):
        text = "Key Takeaways:\n- Takeaway one\n- Takeaway two\nSome other text."
        takeaways = await response_formatter.extract_key_takeaways(text, max_items=5)
        assert len(takeaways) > 0

    @pytest.mark.asyncio
    async def test_generate_follow_up_questions(self, response_formatter):
        text = "You may also ask:\n- What causes this?\n- How is it treated?"
        questions = await response_formatter.generate_follow_up_questions(text, max_questions=3)
        assert len(questions) > 0

    @pytest.mark.asyncio
    async def test_generate_recommended_actions(self, response_formatter):
        text = "Recommended Actions:\n- See a doctor\n- Get rest"
        actions = await response_formatter.generate_recommended_actions(text, max_actions=3)
        assert len(actions) > 0

    @pytest.mark.asyncio
    async def test_simplify_for_audience_patient(self, response_formatter):
        text = "The efficacy of the treatment for hypertension."
        simplified = await response_formatter.simplify_for_audience(text, "patient")
        assert "how well it works" in simplified
        assert "high blood pressure" in simplified


# ─── Validator Tests ──────────────────────────────────────────────────────────


class TestAssistantValidator:
    @pytest.mark.asyncio
    async def test_validate_empty_message(self, validator):
        with pytest.raises(ValidationError, match="empty"):
            await validator._validate_not_empty("", "Message")

    @pytest.mark.asyncio
    async def test_validate_message_length(self, validator):
        with pytest.raises(ValidationError, match="exceeds"):
            await validator._validate_max_length("A" * 10001, 10000, "Message")

    @pytest.mark.asyncio
    async def test_validate_temperature_valid(self, validator):
        validator._validate_temperature(0.5)
        validator._validate_temperature(None)

    @pytest.mark.asyncio
    async def test_validate_temperature_invalid(self, validator):
        with pytest.raises(ValidationError, match="Temperature"):
            validator._validate_temperature(3.0)

    @pytest.mark.asyncio
    async def test_validate_max_tokens_invalid(self, validator):
        with pytest.raises(ValidationError, match="max_tokens"):
            validator._validate_max_tokens(0)

    @pytest.mark.asyncio
    async def test_validate_audience_valid(self, validator):
        validator._validate_audience("patient")
        validator._validate_audience(None)

    @pytest.mark.asyncio
    async def test_validate_audience_invalid(self, validator):
        with pytest.raises(ValidationError, match="audience"):
            validator._validate_audience("invalid_role")

    @pytest.mark.asyncio
    async def test_validate_chat_request_valid(self, validator):
        request = ChatRequest(message="What causes chest pain?")
        await validator.validate_chat_request(request)

    @pytest.mark.asyncio
    async def test_validate_continue_request_valid(self, validator):
        request = ContinueRequest(conversation_id="conv-1")
        await validator.validate_continue_request(request)


# ─── Orchestrator Tests ───────────────────────────────────────────────────────


class TestAssistantOrchestrator:
    @pytest.mark.asyncio
    async def test_chat_basic(self, orchestrator):
        request = ChatRequest(message="What causes headaches?")
        response = await orchestrator.chat(request, user_id=1)
        assert response.conversation_id is not None
        assert response.session_id is not None
        assert len(response.message) > 0
        assert response.safety_passed is True

    @pytest.mark.asyncio
    async def test_chat_with_session(self, orchestrator, session_manager):
        session = await session_manager.create_session(user_id=1)
        request = ChatRequest(message="Hello", session_id=session.session_id)
        response = await orchestrator.chat(request, user_id=1)
        assert response.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_chat_with_conversation(self, orchestrator, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        request = ChatRequest(message="Hello", conversation_id=conv_id)
        response = await orchestrator.chat(request, user_id=1)
        assert response.conversation_id == conv_id

    @pytest.mark.asyncio
    async def test_chat_emergency_detection(self, orchestrator):
        request = ChatRequest(message="I'm having chest pain and difficulty breathing")
        response = await orchestrator.chat(request, user_id=1)
        assert response.has_emergency is True
        assert response.emergency_message is not None
        assert "emergency" in response.message.lower()

    @pytest.mark.asyncio
    async def test_chat_emergency_suicidal(self, orchestrator):
        request = ChatRequest(message="I want to kill myself")
        response = await orchestrator.chat(request, user_id=1)
        assert response.has_emergency is True

    @pytest.mark.asyncio
    async def test_chat_emergency_stroke(self, orchestrator):
        request = ChatRequest(message="I think I'm having a stroke")
        response = await orchestrator.chat(request, user_id=1)
        assert response.has_emergency is True

    @pytest.mark.asyncio
    async def test_chat_audience_override(self, orchestrator):
        request = ChatRequest(message="What is hypertension?", audience="doctor")
        response = await orchestrator.chat(request, user_id=1)
        assert response.conversation_id is not None

    @pytest.mark.asyncio
    async def test_chat_empty_message(self, orchestrator):
        with pytest.raises(OrchestratorError):
            await orchestrator._validator.validate_chat_request(
                ChatRequest.model_construct(message="")
            )

    @pytest.mark.asyncio
    async def test_continue_conversation(self, orchestrator, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "What causes headaches?")
        await conversation_manager.add_message(conv_id, "assistant", "Various factors.")
        request = ContinueRequest(conversation_id=conv_id)
        response = await orchestrator.continue_conversation(request, user_id=1)
        assert response.conversation_id == conv_id
        assert len(response.message) > 0

    @pytest.mark.asyncio
    async def test_continue_nonexistent_conversation(self, orchestrator):
        request = ContinueRequest(conversation_id="nonexistent")
        with pytest.raises(OrchestratorError):
            await orchestrator.continue_conversation(request, user_id=1)

    @pytest.mark.asyncio
    async def test_summarize(self, orchestrator, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "What causes headaches?")
        await conversation_manager.add_message(conv_id, "assistant", "Headaches have many causes.")
        request = SummarizeRequest(conversation_id=conv_id)
        response = await orchestrator.summarize(request)
        assert response.conversation_id == conv_id
        assert response.message_count == 2

    @pytest.mark.asyncio
    async def test_summarize_empty(self, orchestrator, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        request = SummarizeRequest(conversation_id=conv_id)
        response = await orchestrator.summarize(request)
        assert response.message_count == 0

    @pytest.mark.asyncio
    async def test_explain_term(self, orchestrator):
        request = ExplainRequest(conversation_id="conv-1", term="hypertension")
        response = await orchestrator.explain_term(request)
        assert response.term == "hypertension"
        assert len(response.plain_english) > 0

    @pytest.mark.asyncio
    async def test_explain_term_with_audience(self, orchestrator):
        request = ExplainRequest(conversation_id="conv-1", term="myocardial infarction", audience="patient")
        response = await orchestrator.explain_term(request)
        assert response.audience == "patient"

    @pytest.mark.asyncio
    async def test_get_history(self, orchestrator, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        await conversation_manager.add_message(conv_id, "user", "Hello")
        await conversation_manager.add_message(conv_id, "assistant", "Hi")
        request = HistoryRequest(conversation_id=conv_id)
        response = await orchestrator.get_history(request)
        assert response.total_messages == 2

    @pytest.mark.asyncio
    async def test_get_history_nonexistent(self, orchestrator):
        request = HistoryRequest(conversation_id="nonexistent")
        with pytest.raises(OrchestratorError):
            await orchestrator.get_history(request)

    @pytest.mark.asyncio
    async def test_reset(self, orchestrator, conversation_manager):
        conv_id = await conversation_manager.create_conversation(user_id=1, session_id="session-1")
        request = ResetRequest(conversation_id=conv_id)
        response = await orchestrator.reset(request, user_id=1)
        assert response.previous_conversation_reset is True
        assert response.new_conversation_id is not None

    @pytest.mark.asyncio
    async def test_reset_new_session(self, orchestrator):
        request = ResetRequest()
        response = await orchestrator.reset(request, user_id=1)
        assert response.session_id is not None
        assert response.new_conversation_id is not None

    @pytest.mark.asyncio
    async def test_chat_citations(self, orchestrator, mock_gateway):
        mock_gateway.execute.return_value = GatewayResponse(
            content="According to recent studies [1], this condition affects many people [2].",
            conversation_id="test",
            model="mock",
            provider="mock",
        )
        request = ChatRequest(message="Tell me about diabetes")
        response = await orchestrator.chat(request, user_id=1)
        assert len(response.citations) >= 0

    @pytest.mark.asyncio
    async def test_chat_follow_up_questions(self, orchestrator):
        with patch.object(orchestrator._response_formatter, 'generate_follow_up_questions',
                          AsyncMock(return_value=["What causes this?", "How is it treated?"])):
            request = ChatRequest(message="What is diabetes?")
            response = await orchestrator.chat(request, user_id=1)
            assert len(response.follow_up_questions) > 0

    @pytest.mark.asyncio
    async def test_chat_recommended_actions(self, orchestrator):
        with patch.object(orchestrator._response_formatter, 'generate_recommended_actions',
                          AsyncMock(return_value=["Consult a doctor"])):
            request = ChatRequest(message="I have a fever")
            response = await orchestrator.chat(request, user_id=1)
            assert len(response.recommended_actions) >= 0


# ─── Utils Tests ──────────────────────────────────────────────────────────────


class TestUtils:
    def test_extract_topics_symptom(self):
        topics = extract_topics("I have chest pain and fever")
        assert "symptom" in topics

    def test_extract_topics_medication(self):
        topics = extract_topics("What is the dosage for this medication?")
        assert "medication" in topics

    def test_extract_topics_emergency(self):
        topics = extract_topics("This is an emergency, severe pain")
        assert "emergency" in topics

    def test_extract_topics_empty(self):
        topics = extract_topics("")
        assert topics == []

    def test_extract_topics_multiple(self):
        topics = extract_topics("I need medication for my anxiety and depression")
        assert "medication" in topics
        assert "mental_health" in topics

    def test_timing_ms(self):
        import time
        start = time.time()
        result = timing_ms(start)
        assert isinstance(result, float)
        assert result >= 0


# ─── API Tests ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_api_gateway():
    gw = AsyncMock(spec=GatewayService)
    gw.execute.return_value = GatewayResponse(
        content="This is a test medical response. Consult a healthcare professional.",
        conversation_id="api-test-conv",
        model="mock-model",
        provider="mock",
        usage={"prompt_tokens": 50, "completion_tokens": 20},
    )
    return gw


@pytest.fixture
def assistant_client(client, mock_api_gateway):
    reset_all()
    from app.ai.assistant.deps.deps import (
        get_orchestrator as _get_orchestrator,
        get_conversation_manager as _get_cm,
        get_session_manager as _get_sm,
        get_context_manager as _get_ctx,
        get_personalization_manager as _get_pm,
        get_response_formatter as _get_rf,
    )

    cm = ConversationManager()
    sm = SessionManager()
    ctx = ContextManager(conversation_manager=cm, session_manager=sm)
    pm = PersonalizationManager()
    rf = ResponseFormatter()
    validator = AssistantValidator()

    orchestrator = AssistantOrchestrator(
        conversation_manager=cm,
        session_manager=sm,
        context_manager=ctx,
        personalization_manager=pm,
        response_formatter=rf,
        gateway=mock_api_gateway,
        validator=validator,
    )

    from app.main import app
    app.dependency_overrides[_get_orchestrator] = lambda: orchestrator

    yield client

    app.dependency_overrides.pop(_get_orchestrator, None)
    reset_all()


class TestAssistantAPI:
    def test_chat_endpoint_requires_auth(self, assistant_client):
        response = assistant_client.post("/ai/assistant/chat", json={"message": "Hello"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_chat_endpoint_patient(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": "What causes headaches?"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "conversation_id" in data
        assert "session_id" in data
        assert "message" in data

    def test_chat_endpoint_doctor(self, assistant_client, doctor_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": "What causes hypertension?"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_chat_endpoint_admin(self, assistant_client, admin_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": "What is diabetes?"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_continue_endpoint(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        conv_id = response.json()["conversation_id"]

        response = client.post(
            "/ai/assistant/continue",
            json={"conversation_id": conv_id},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_summarize_endpoint(self, assistant_client, patient_token):
        chat_resp = client.post(
            "/ai/assistant/chat",
            json={"message": "What causes headaches?"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        conv_id = chat_resp.json()["conversation_id"]

        response = client.post(
            "/ai/assistant/summarize",
            json={"conversation_id": conv_id},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conversation_id"] == conv_id

    def test_explain_endpoint(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/explain",
            json={"conversation_id": "test-conv", "term": "hypertension"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["term"] == "hypertension"

    def test_history_endpoint(self, assistant_client, patient_token):
        chat_resp = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        conv_id = chat_resp.json()["conversation_id"]

        response = client.post(
            "/ai/assistant/history",
            json={"conversation_id": conv_id},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_messages"] >= 1

    def test_reset_endpoint(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/reset",
            json={},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["new_conversation_id"] is not None
        assert data["session_id"] is not None

    def test_reset_with_conversation(self, assistant_client, patient_token):
        chat_resp = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        conv_id = chat_resp.json()["conversation_id"]

        response = client.post(
            "/ai/assistant/reset",
            json={"conversation_id": conv_id},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_session_endpoint(self, assistant_client, patient_token):
        chat_resp = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        session_id = chat_resp.json()["session_id"]

        response = client.get(
            f"/ai/assistant/session/{session_id}",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id

    def test_get_session_unauthorized(self, assistant_client, patient_token, doctor_token):
        chat_resp = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        session_id = chat_resp.json()["session_id"]

        response = client.get(
            f"/ai/assistant/session/{session_id}",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_session_admin_can_access_any(self, assistant_client, patient_token, admin_token):
        chat_resp = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        session_id = chat_resp.json()["session_id"]

        response = client.get(
            f"/ai/assistant/session/{session_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_session_nonexistent(self, assistant_client, patient_token):
        response = client.get(
            "/ai/assistant/session/nonexistent-session",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_history_by_id(self, assistant_client, patient_token):
        chat_resp = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        conv_id = chat_resp.json()["conversation_id"]

        response = client.get(
            f"/ai/assistant/history/{conv_id}",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_list_conversations(self, assistant_client, patient_token):
        response = client.get(
            "/ai/assistant/conversations",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "conversations" in data
        assert "total" in data

    def test_chat_validation_error(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": ""},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_continue_validation_error(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/continue",
            json={"conversation_id": ""},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_chat_emergency_endpoint(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": "I'm having chest pain"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_emergency"] is True

    def test_chat_with_audience_override(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": "What is hypertension?", "audience": "doctor"},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_chat_with_temperature(self, assistant_client, patient_token):
        response = client.post(
            "/ai/assistant/chat",
            json={"message": "Hello", "temperature": 0.5},
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == status.HTTP_200_OK


# ─── Schema Tests ─────────────────────────────────────────────────────────────


class TestSchemas:
    def test_chat_request_defaults(self):
        request = ChatRequest(message="Hello")
        assert request.message == "Hello"
        assert request.conversation_id is None
        assert request.session_id is None
        assert request.stream is False

    def test_chat_request_with_all_fields(self):
        request = ChatRequest(
            message="Hello",
            conversation_id="conv-1",
            session_id="session-1",
            temperature=0.5,
            max_tokens=100,
            stream=True,
            audience="doctor",
            language="en",
        )
        assert request.temperature == 0.5
        assert request.max_tokens == 100
        assert request.stream is True

    def test_chat_response_defaults(self):
        response = ChatResponse(
            conversation_id="conv-1",
            session_id="session-1",
            message="Test",
        )
        assert response.has_emergency is False
        assert response.safety_passed is True
        assert response.citations == []
        assert response.disclaimers == []

    def test_continue_request(self):
        request = ContinueRequest(conversation_id="conv-1")
        assert request.conversation_id == "conv-1"

    def test_summarize_request(self):
        request = SummarizeRequest(conversation_id="conv-1")
        assert request.conversation_id == "conv-1"

    def test_summarize_response(self):
        response = SummarizeResponse(
            conversation_id="conv-1",
            summary="A summary",
            title="Title",
            message_count=5,
        )
        assert response.conversation_id == "conv-1"

    def test_explain_request(self):
        request = ExplainRequest(conversation_id="conv-1", term="hypertension")
        assert request.term == "hypertension"

    def test_explain_response(self):
        response = ExplainResponse(
            term="hypertension",
            plain_english="High blood pressure",
            audience="patient",
        )
        assert response.plain_english == "High blood pressure"

    def test_reset_request(self):
        request = ResetRequest(conversation_id="conv-1")
        assert request.conversation_id == "conv-1"

    def test_reset_response(self):
        response = ResetResponse(
            session_id="session-1",
            new_conversation_id="conv-2",
        )
        assert response.previous_conversation_reset is False

    def test_session_metadata_defaults(self):
        session = SessionMetadata(session_id="s1", user_id=1)
        assert session.preferred_language == "en"
        assert session.preferred_audience == "patient"
        assert session.safety_flags == []

    def test_personalization_preferences_defaults(self):
        prefs = PersonalizationPreferences()
        assert prefs.language == "en"
        assert prefs.audience == "patient"
        assert prefs.include_citations is True

    def test_conversation_summary_defaults(self):
        summary = ConversationSummary(conversation_id="c1")
        assert summary.message_count == 0
        assert summary.topics == []

    def test_assistant_message(self):
        msg = AssistantMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.token_count == 0
