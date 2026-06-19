from app.ai.medical.entities.patterns import RuleBasedEntityExtractor
from app.ai.medical.entities.interfaces import EntityExtractorABC
from app.ai.medical.engine.schemas import EntityResult


class EntityExtractor(EntityExtractorABC):
    def __init__(self):
        self._extractor = RuleBasedEntityExtractor()

    def extract(self, query: str) -> EntityResult:
        return self._extractor.extract(query)
