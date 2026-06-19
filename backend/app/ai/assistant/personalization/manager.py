from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.interfaces.interfaces import PersonalizationManagerABC
from app.ai.assistant.schemas.schemas import PersonalizationPreferences


class PersonalizationManager(PersonalizationManagerABC):

    def __init__(self, settings: AssistantSettings | None = None):
        self._settings = settings or AssistantSettings()
        self._preferences: dict[str, PersonalizationPreferences] = {}

    async def get_preferences(self, session_id: str) -> PersonalizationPreferences:
        return self._preferences.get(session_id, PersonalizationPreferences())

    async def set_preferences(self, session_id: str, preferences: PersonalizationPreferences) -> None:
        self._preferences[session_id] = preferences

    async def update_preferences(self, session_id: str, updates: dict) -> PersonalizationPreferences:
        prefs = await self.get_preferences(session_id)
        for key, value in updates.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        self._preferences[session_id] = prefs
        return prefs

    async def apply_personalization(self, session_id: str, response: str) -> str:
        prefs = await self.get_preferences(session_id)
        if prefs.simplify_terms:
            response = self._simplify_medical_terms(response)
        if prefs.response_length == "brief":
            response = self._truncate_to_brief(response)
        elif prefs.response_length == "detailed":
            pass
        return response

    async def personalize_query(self, session_id: str, query: str) -> str:
        prefs = await self.get_preferences(session_id)
        audience_prefixes = {
            "patient": "",
            "doctor": "[For a medical professional] ",
            "nurse": "[For a nursing professional] ",
            "caregiver": "[For a caregiver] ",
            "administrator": "[For a healthcare administrator] ",
        }
        prefix = audience_prefixes.get(prefs.audience, "")
        if prefix:
            query = f"{prefix}{query}"
        return query

    def _simplify_medical_terms(self, text: str) -> str:
        replacements = {
            " myocardial infarction": " heart attack",
            " Myocardial infarction": " Heart attack",
            " hypertension": " high blood pressure",
            " Hypertension": " High blood pressure",
            " hyperlipidemia": " high cholesterol",
            " Hyperlipidemia": " High cholesterol",
            " diabetes mellitus": " diabetes",
            " Diabetes mellitus": " Diabetes",
            " cerebrovascular accident": " stroke",
            " Cerebrovascular accident": " Stroke",
            " pneumonia": " lung infection",
            " Pneumonia": " Lung infection",
            " upper respiratory tract infection": " common cold or flu",
            " urinary tract infection": " bladder infection",
            " gastroenteritis": " stomach flu",
            " administer": " give",
            " contraindicated": " should not be used",
            " contraindication": " reason not to use",
            " adverse effect": " side effect",
            " adverse event": " side effect",
        }
        for medical, plain in replacements.items():
            text = text.replace(medical, plain)
        return text

    def _truncate_to_brief(self, text: str, max_sentences: int = 3) -> str:
        sentences = text.replace("! ", "!||").replace("? ", "?||").replace(". ", ".||")
        parts = sentences.split("||")
        if len(parts) <= max_sentences:
            return text
        return " ".join(parts[:max_sentences]) + "."
