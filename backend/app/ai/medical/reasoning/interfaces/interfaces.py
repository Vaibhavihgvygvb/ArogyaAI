from abc import ABC, abstractmethod

from app.ai.medical.engine.schemas import QueryUnderstandingResult
from app.ai.medical.reasoning.schemas.schemas import (
    AssembledPrompt,
    CitationPlan,
    CompressedContext,
    ConfidencePlan,
    EvidencePlan,
    RankedContext,
    ReasoningPlan,
    RetrievalPlan,
    SafetyPlan,
)

RETRIEVAL_RESULT_TYPE = dict


class ReasoningPlannerABC(ABC):
    @abstractmethod
    async def plan(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
        approach_hint: str | None = None,
    ) -> ReasoningPlan:
        ...


class EvidencePlannerABC(ABC):
    @abstractmethod
    async def plan(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
        reasoning_plan: ReasoningPlan,
    ) -> EvidencePlan:
        ...


class RetrievalStrategyABC(ABC):
    @abstractmethod
    async def plan(
        self,
        query: str,
        evidence_plan: EvidencePlan,
        analysis: QueryUnderstandingResult,
        top_k: int = 15,
        filters: dict | None = None,
    ) -> RetrievalPlan:
        ...


class ContextRankerABC(ABC):
    @abstractmethod
    async def rank(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        query: str,
        retrieval_plan: RetrievalPlan,
        analysis: QueryUnderstandingResult,
    ) -> RankedContext:
        ...


class ContextCompressorABC(ABC):
    @abstractmethod
    async def compress(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
        query: str,
        max_tokens: int,
    ) -> CompressedContext:
        ...


class PromptAssemblerABC(ABC):
    @abstractmethod
    async def assemble(
        self,
        query: str,
        compressed_context: CompressedContext,
        reasoning_plan: ReasoningPlan,
        evidence_plan: EvidencePlan,
        analysis: QueryUnderstandingResult,
    ) -> AssembledPrompt:
        ...


class CitationPlannerABC(ABC):
    @abstractmethod
    async def plan(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
    ) -> CitationPlan:
        ...


class ConfidencePlannerABC(ABC):
    @abstractmethod
    async def plan(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
        analysis: QueryUnderstandingResult,
    ) -> ConfidencePlan:
        ...


class SafetyPlannerABC(ABC):
    @abstractmethod
    async def plan(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
        reasoning_plan: ReasoningPlan,
    ) -> SafetyPlan:
        ...


class ReasoningPipelineABC(ABC):
    @abstractmethod
    async def run(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
        top_k: int = 15,
        filters: dict | None = None,
        min_score: float | None = None,
        max_context_tokens: int = 4096,
    ) -> dict:
        ...


class ReasoningServiceABC(ABC):
    @abstractmethod
    async def reason(
        self,
        query: str,
        conversation_id: str | None = None,
        approach_hint: str | None = None,
        top_k: int = 15,
        filters: dict | None = None,
        min_score: float | None = None,
        max_context_tokens: int = 4096,
    ) -> dict:
        ...
