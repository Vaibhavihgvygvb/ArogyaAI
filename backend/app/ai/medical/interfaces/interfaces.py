from abc import ABC, abstractmethod

from app.ai.medical.schemas.schemas import (
    CitationEntry,
    ConfidenceScore,
    MedicalContext,
    MedicalIntent,
    MedicalMetadata,
    MedicalReasoning,
    MedicalResponse,
    QueryRewrite,
    SafetyCheckResult,
)


class IntentDetectorABC(ABC):
    @abstractmethod
    async def detect(self, query: str, specialty_hint: str | None = None) -> MedicalIntent:
        ...


class QueryRewriterABC(ABC):
    @abstractmethod
    async def rewrite(self, query: str, intent: MedicalIntent, context: str | None = None) -> QueryRewrite:
        ...


class ContextOptimizerABC(ABC):
    @abstractmethod
    async def optimize(self, context: str, intent: MedicalIntent, max_tokens: int = 2048) -> MedicalContext:
        ...


class MedicalPromptBuilderABC(ABC):
    @abstractmethod
    async def build(self, query: str, context: str, intent: MedicalIntent) -> tuple[str, str]:
        ...


class MedicalReasonerABC(ABC):
    @abstractmethod
    async def reason(self, query: str, context: str, response: str, intent: MedicalIntent) -> MedicalReasoning:
        ...


class CitationEngineABC(ABC):
    @abstractmethod
    async def build_citations(self, results: list, top_k: int = 10) -> list[CitationEntry]:
        ...


class ConfidenceEngineABC(ABC):
    @abstractmethod
    async def score(
        self,
        query: str,
        response: str,
        citations: list[CitationEntry],
        intent: MedicalIntent,
    ) -> ConfidenceScore:
        ...


class SafetyValidatorABC(ABC):
    @abstractmethod
    async def validate(
        self,
        query: str,
        response: str,
        citations: list[CitationEntry],
        intent: MedicalIntent,
    ) -> SafetyCheckResult:
        ...


class ResponseBuilderABC(ABC):
    @abstractmethod
    async def build(
        self,
        answer: str,
        intent: MedicalIntent | None = None,
        reasoning: MedicalReasoning | None = None,
        citations: list[CitationEntry] | None = None,
        confidence: ConfidenceScore | None = None,
        safety: SafetyCheckResult | None = None,
        metadata: MedicalMetadata | None = None,
        conversation_id: str | None = None,
    ) -> MedicalResponse:
        ...
