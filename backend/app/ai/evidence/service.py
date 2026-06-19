import time

from app.ai.evidence.config import EvidenceConfig
from app.ai.evidence.exceptions import EvidenceServiceError
from app.ai.evidence.pipeline import EvidencePipeline
from app.ai.evidence.schemas import (
    CitationStyle,
    EvidenceSpan,
    PipelineResult,
    ServiceResult,
)


class EvidenceService:
    def __init__(
        self,
        pipeline: EvidencePipeline | None = None,
        config: EvidenceConfig | None = None,
    ):
        self._config = config or EvidenceConfig()
        self._pipeline = pipeline or EvidencePipeline(config=self._config)

    async def validate_evidence(
        self,
        spans: list[EvidenceSpan],
        citation_style: CitationStyle = CitationStyle.AMA,
    ) -> ServiceResult:
        t0 = time.time()
        errors: list[str] = []
        warnings: list[str] = []

        if not spans:
            return ServiceResult(
                passed=True,
                summary="No evidence spans to validate.",
                processing_time_ms=0.0,
            )

        if len(spans) > self._config.EVIDENCE_MAX_SPANS:
            warnings.append(f"Truncated to {self._config.EVIDENCE_MAX_SPANS} spans (got {len(spans)})")
            spans = spans[: self._config.EVIDENCE_MAX_SPANS]

        try:
            pipeline_result = await self._pipeline.run(
                spans=spans,
                citation_style=citation_style,
            )
        except Exception as e:
            errors.append(str(e))
            return ServiceResult(
                passed=False,
                summary=f"Evidence validation failed: {e}",
                errors=errors,
                processing_time_ms=round((time.time() - t0) * 1000, 2),
            )

        passed = True
        summary_parts = []
        if pipeline_result.state.confidence:
            confidence = pipeline_result.state.confidence
            passed = confidence.suitable_for_ai
            summary_parts.append(f"Confidence: {confidence.overall:.1%}")
            if not confidence.suitable_for_ai:
                warnings.append("Overall confidence below suitable-for-AI threshold.")

        if pipeline_result.state.conflicts:
            n = len(pipeline_result.state.conflicts)
            warnings.append(f"{n} evidence conflict(s) detected.")
            if n > 3:
                passed = False

        if pipeline_result.state.coverage:
            cov = pipeline_result.state.coverage
            summary_parts.append(f"Coverage: {cov.coverage_score:.0%}")
            if cov.coverage_score < self._config.EVIDENCE_COVERAGE_MIN_SCORE:
                warnings.append("Evidence coverage below minimum threshold.")
                passed = False

        if pipeline_result.errors:
            errors.extend(pipeline_result.errors)
            passed = False

        summary = " | ".join(summary_parts) if summary_parts else "Validation complete."

        return ServiceResult(
            passed=passed,
            pipeline_result=pipeline_result,
            summary=summary,
            warnings=warnings,
            errors=errors,
            processing_time_ms=round((time.time() - t0) * 1000, 2),
        )

    async def verify(
        self, spans: list[EvidenceSpan]
    ) -> PipelineResult:
        return await self._pipeline.run(spans)

    async def generate_citations(
        self,
        spans: list[EvidenceSpan],
        style: CitationStyle = CitationStyle.AMA,
    ) -> PipelineResult:
        return await self._pipeline.run(spans, citation_style=style)

    async def analyze_coverage(
        self, spans: list[EvidenceSpan]
    ) -> PipelineResult:
        return await self._pipeline.run(spans)

    async def detect_conflicts(
        self, spans: list[EvidenceSpan]
    ) -> PipelineResult:
        return await self._pipeline.run(spans)

    async def calculate_confidence(
        self, spans: list[EvidenceSpan]
    ) -> PipelineResult:
        return await self._pipeline.run(spans)

    async def get_provenance(
        self, spans: list[EvidenceSpan]
    ) -> PipelineResult:
        return await self._pipeline.run(spans)

    async def get_explanation(
        self, spans: list[EvidenceSpan]
    ) -> PipelineResult:
        return await self._pipeline.run(spans)

    async def full_pipeline(
        self,
        spans: list[EvidenceSpan],
        citation_style: CitationStyle = CitationStyle.AMA,
    ) -> PipelineResult:
        return await self._pipeline.run(spans, citation_style=citation_style)
