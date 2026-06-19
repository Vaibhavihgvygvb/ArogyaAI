from app.ai.medical.engine.schemas import QueryUnderstandingResult, ConversationContext
from app.ai.medical.engine.interfaces import QueryUnderstandingEngineABC
from app.ai.medical.intent.services import IntentDetectorService
from app.ai.medical.entities.services import EntityExtractor
from app.ai.medical.specialty.services import SpecialtyClassifier
from app.ai.medical.urgency.services import UrgencyClassifier
from app.ai.medical.audience.services import AudienceClassifier
from app.ai.medical.language.services import LanguageDetector
from app.ai.medical.rewrite.services import QueryRewriter
from app.ai.medical.context.services import ContextResolver


_intent_svc = IntentDetectorService()
_entity_svc = EntityExtractor()
_specialty_svc = SpecialtyClassifier()
_urgency_svc = UrgencyClassifier()
_audience_svc = AudienceClassifier()
_language_svc = LanguageDetector()
_rewrite_svc = QueryRewriter()
_context_svc = ContextResolver()


class QueryUnderstandingEngine(QueryUnderstandingEngineABC):
    async def analyze(self, query: str, conversation_id: str | None = None) -> QueryUnderstandingResult:
        intent = await self.detect_intent(query)
        entities = await self.extract_entities(query) if len(query) > 5 else None
        specialty = await self.classify_specialty(query)
        urgency = await self.classify_urgency(query)
        audience = await self.classify_audience(query)
        language = await self.detect_language(query)
        context = await self._resolve_context(conversation_id)
        rewrite = await self.rewrite_query(query)

        return QueryUnderstandingResult(
            original_query=query,
            intent=intent,
            entities=entities,
            specialty=specialty,
            urgency=urgency,
            audience=audience,
            language=language,
            rewrite=rewrite,
            context=context,
        )

    async def detect_intent(self, query: str) -> "IntentResult":
        return await _intent_svc.detect(query)

    async def extract_entities(self, query: str) -> "EntityResult":
        return _entity_svc.extract(query)

    async def classify_specialty(self, query: str) -> "SpecialtyResult":
        return _specialty_svc.classify(query)

    async def classify_urgency(self, query: str) -> "UrgencyResult":
        return _urgency_svc.classify(query)

    async def classify_audience(self, query: str) -> "AudienceResult":
        return _audience_svc.classify(query)

    async def detect_language(self, query: str) -> "LanguageInfo":
        return _language_svc.detect(query)

    async def rewrite_query(self, query: str, conversation_id: str | None = None) -> "RewriteResult":
        return await _rewrite_svc.rewrite(query)

    async def _resolve_context(self, conversation_id: str | None) -> ConversationContext:
        if not conversation_id:
            return ConversationContext()
        return await _context_svc.resolve(conversation_id)
