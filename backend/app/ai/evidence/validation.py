from pydantic import AfterValidator, ValidationInfo
from typing_extensions import Annotated

from app.ai.evidence.schemas import ServiceResult


def _check_evidence_pass(v: ServiceResult | None, info: ValidationInfo) -> ServiceResult | None:
    if v is not None and not v.passed:
        raise ValueError(
            f"Evidence validation failed: {v.summary}. "
            f"Warnings: {'; '.join(v.warnings)}"
        )
    return v


HealthEvidenceValidator = Annotated[ServiceResult | None, AfterValidator(_check_evidence_pass)]
