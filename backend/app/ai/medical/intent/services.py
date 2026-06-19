from app.ai.medical.engine.schemas import IntentResult, IntentCandidate
from app.ai.medical.intent.interfaces import IntentServiceABC
from app.ai.medical.intent.classifiers import RuleBasedIntentClassifier


class IntentDetectorService(IntentServiceABC):
    def __init__(self):
        self._classifier = RuleBasedIntentClassifier()

    async def detect(self, query: str, specialty_hint: str | None = None) -> IntentResult:
        return self._classifier.classify(query)
