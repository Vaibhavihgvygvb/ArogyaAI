from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.context.manager import ContextManager
from app.ai.assistant.conversation.manager import ConversationManager
from app.ai.assistant.interfaces.interfaces import (
    AssistantOrchestratorABC,
    ContextManagerABC,
    ConversationManagerABC,
    PersonalizationManagerABC,
    ResponseFormatterABC,
    SessionManagerABC,
)
from app.ai.assistant.orchestrator.orchestrator import AssistantOrchestrator
from app.ai.assistant.personalization.manager import PersonalizationManager
from app.ai.assistant.response.formatter import ResponseFormatter
from app.ai.assistant.session.manager import SessionManager
from app.ai.assistant.validators.validators import AssistantValidator

_conversation_manager: ConversationManagerABC | None = None
_session_manager: SessionManagerABC | None = None
_context_manager: ContextManagerABC | None = None
_personalization_manager: PersonalizationManagerABC | None = None
_response_formatter: ResponseFormatterABC | None = None
_orchestrator: AssistantOrchestratorABC | None = None
_settings: AssistantSettings | None = None
_validator: AssistantValidator | None = None


def get_assistant_settings() -> AssistantSettings:
    global _settings
    if _settings is None:
        _settings = AssistantSettings()
    return _settings


def set_assistant_settings(s: AssistantSettings) -> None:
    global _settings
    _settings = s


def reset_assistant_settings() -> None:
    global _settings
    _settings = None


def get_conversation_manager() -> ConversationManagerABC:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager(settings=get_assistant_settings())
    return _conversation_manager


def set_conversation_manager(m: ConversationManagerABC) -> None:
    global _conversation_manager
    _conversation_manager = m


def reset_conversation_manager() -> None:
    global _conversation_manager
    _conversation_manager = None


def get_session_manager() -> SessionManagerABC:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(settings=get_assistant_settings())
    return _session_manager


def set_session_manager(m: SessionManagerABC) -> None:
    global _session_manager
    _session_manager = m


def reset_session_manager() -> None:
    global _session_manager
    _session_manager = None


def get_context_manager() -> ContextManagerABC:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager(
            conversation_manager=get_conversation_manager(),
            session_manager=get_session_manager(),
            settings=get_assistant_settings(),
        )
    return _context_manager


def set_context_manager(m: ContextManagerABC) -> None:
    global _context_manager
    _context_manager = m


def reset_context_manager() -> None:
    global _context_manager
    _context_manager = None


def get_personalization_manager() -> PersonalizationManagerABC:
    global _personalization_manager
    if _personalization_manager is None:
        _personalization_manager = PersonalizationManager(settings=get_assistant_settings())
    return _personalization_manager


def set_personalization_manager(m: PersonalizationManagerABC) -> None:
    global _personalization_manager
    _personalization_manager = m


def reset_personalization_manager() -> None:
    global _personalization_manager
    _personalization_manager = None


def get_response_formatter() -> ResponseFormatterABC:
    global _response_formatter
    if _response_formatter is None:
        _response_formatter = ResponseFormatter()
    return _response_formatter


def set_response_formatter(f: ResponseFormatterABC) -> None:
    global _response_formatter
    _response_formatter = f


def reset_response_formatter() -> None:
    global _response_formatter
    _response_formatter = None


def get_validator() -> AssistantValidator:
    global _validator
    if _validator is None:
        _validator = AssistantValidator(settings=get_assistant_settings())
    return _validator


def set_validator(v: AssistantValidator) -> None:
    global _validator
    _validator = v


def reset_validator() -> None:
    global _validator
    _validator = None


def get_orchestrator() -> AssistantOrchestratorABC:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AssistantOrchestrator(
            conversation_manager=get_conversation_manager(),
            session_manager=get_session_manager(),
            context_manager=get_context_manager(),
            personalization_manager=get_personalization_manager(),
            response_formatter=get_response_formatter(),
            settings=get_assistant_settings(),
            validator=get_validator(),
        )
    return _orchestrator


def set_orchestrator(o: AssistantOrchestratorABC) -> None:
    global _orchestrator
    _orchestrator = o


def reset_orchestrator() -> None:
    global _orchestrator
    _orchestrator = None


def reset_all() -> None:
    reset_conversation_manager()
    reset_session_manager()
    reset_context_manager()
    reset_personalization_manager()
    reset_response_formatter()
    reset_validator()
    reset_orchestrator()
    reset_assistant_settings()
