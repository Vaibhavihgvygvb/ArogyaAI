from abc import ABC, abstractmethod

from app.ai.evidence.schemas import (
    Citation,
    CitationGroup,
    CitationStyle,
    EvidenceState,
    FormattedCitation,
    VerificationResult,
)


class CitationGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        verification_results: list[VerificationResult],
        state: EvidenceState | None = None,
    ) -> list[Citation]:
        ...

    @abstractmethod
    async def group_by_claim(
        self, citations: list[Citation]
    ) -> list[CitationGroup]:
        ...


class CitationFormatter(ABC):
    @abstractmethod
    async def format(
        self,
        citations: list[Citation],
        style: CitationStyle = CitationStyle.AMA,
    ) -> FormattedCitation:
        ...

    @abstractmethod
    async def supported_styles(self) -> list[CitationStyle]:
        ...
