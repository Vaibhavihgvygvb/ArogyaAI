from abc import ABC, abstractmethod
from app.ai.medical.taxonomy.schemas import TaxonomyResult, TerminologySystem


class TaxonomyProviderABC(ABC):
    @abstractmethod
    async def lookup(self, term: str, system: TerminologySystem | None = None) -> TaxonomyResult:
        ...

    @abstractmethod
    async def list_systems(self) -> list[TerminologySystem]:
        ...
