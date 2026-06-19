from app.ai.medical.taxonomy.schemas import TaxonomyResult, TerminologySystem
from app.ai.medical.taxonomy.interfaces import TaxonomyProviderABC


class MedicalTaxonomyService(TaxonomyProviderABC):
    async def lookup(self, term: str, system: TerminologySystem | None = None) -> TaxonomyResult:
        return TaxonomyResult(
            term=term,
            mappings=[],
            available_systems=list(TerminologySystem),
            total_mappings=0,
        )

    async def list_systems(self) -> list[TerminologySystem]:
        return list(TerminologySystem)
