import uuid
from datetime import datetime, timedelta, timezone

from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.exceptions.exceptions import SessionError
from app.ai.assistant.interfaces.interfaces import SessionManagerABC
from app.ai.assistant.schemas.schemas import SessionMetadata, SessionState


class SessionManager(SessionManagerABC):

    def __init__(self, settings: AssistantSettings | None = None):
        self._settings = settings or AssistantSettings()
        self._sessions: dict[str, SessionMetadata] = {}
        self._session_states: dict[str, SessionState] = {}

    async def create_session(self, user_id: int, metadata: dict | None = None) -> SessionMetadata:
        now = datetime.now(timezone.utc)
        session_id = str(uuid.uuid4())
        expires_at = now + timedelta(minutes=self._settings.ASSISTANT_SESSION_TIMEOUT_MINUTES)
        session = SessionMetadata(
            session_id=session_id,
            user_id=user_id,
            last_activity=now,
            created_at=now,
            expires_at=expires_at,
            preferred_language=self._settings.ASSISTANT_DEFAULT_LANGUAGE,
            preferred_audience=self._settings.ASSISTANT_DEFAULT_AUDIENCE,
            literacy_level=self._settings.ASSISTANT_DEFAULT_LITERACY_LEVEL,
            context_state=metadata or {},
        )
        self._sessions[session_id] = session
        self._session_states[session_id] = SessionState(
            session=session,
            active=True,
            metadata=metadata or {},
        )
        return session

    async def get_session(self, session_id: str) -> SessionMetadata | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        now = datetime.now(timezone.utc)
        if session.expires_at and now > session.expires_at:
            await self.delete_session(session_id)
            return None
        return session

    async def update_session(self, session_id: str, updates: dict) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        session.last_activity = datetime.now(timezone.utc)
        if session_id in self._session_states:
            state = self._session_states[session_id]
            state.session = session
            for key, value in updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)
        return True

    async def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._session_states.pop(session_id, None)
            return True
        return False

    async def list_sessions(self, user_id: int) -> list[SessionMetadata]:
        now = datetime.now(timezone.utc)
        valid = []
        for s in self._sessions.values():
            if s.user_id == user_id:
                if s.expires_at and now > s.expires_at:
                    continue
                valid.append(s)
        return valid

    async def get_session_state(self, session_id: str) -> SessionState | None:
        state = self._session_states.get(session_id)
        if not state:
            return None
        session = await self.get_session(session_id)
        if not session:
            return None
        state.session = session
        return state

    async def touch_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        now = datetime.now(timezone.utc)
        session.last_activity = now
        session.expires_at = now + timedelta(minutes=self._settings.ASSISTANT_SESSION_TIMEOUT_MINUTES)
        if session_id in self._session_states:
            self._session_states[session_id].session = session
        return True
