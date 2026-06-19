import pytest

from app.ai.evidence.config import EvidenceConfig
from app.ai.evidence.pipeline import EvidencePipeline
from app.ai.evidence.schemas import (
    Citation,
    CitationStyle,
    ConfidenceBreakdown,
    ConfidenceResult,
    ConflictResult,
    ConflictType,
    CoverageGap,
    CoverageResult,
    EvidenceSpan,
    EvidenceState,
    ExplanationComponent,
    ExplanationResult,
    FormattedCitation,
    PipelineResult,
    ServiceResult,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)
from app.ai.evidence.service import EvidenceService


class MockVerifier:
    async def verify(self, spans, state=None):
        return [
            VerificationResult(
                span=s,
                verified=True,
                status=VerificationStatus.VERIFIED,
                supporting_sources=[
                    VerifiedSource(
                        source_id="s1",
                        support_direction="supporting",
                        authority_score=0.8,
                        relevance_score=0.9,
                        recency_score=0.7,
                        quality_score=0.85,
                    )
                ],
                contradicting_sources=[],
                confidence=0.9,
                evidence_summary=f"Verified: {s.claim}",
                verification_details="Mock verification",
            )
            for s in spans
        ]


class MockCitationGenerator:
    async def generate(self, verification_results, state=None):
        citations = []
        for i, vr in enumerate(verification_results):
            for j, src in enumerate(vr.supporting_sources):
                citations.append(
                    Citation(
                        citation_id=f"cit_{i}_{j}",
                        span_index=i,
                        evidence_text=vr.span.claim,
                        source=src,
                        confidence=vr.confidence,
                    )
                )
        return citations

    async def group_by_claim(self, citations):
        return []


class MockCitationFormatter:
    async def format(self, citations, style=CitationStyle.AMA):
        return FormattedCitation(style=style, text="", markdown="")


class MockCoverageAnalyzer:
    def __init__(self, coverage_result=None):
        self._coverage_result = coverage_result

    async def analyze(self, verification_results, state=None):
        if self._coverage_result is not None:
            return self._coverage_result
        return CoverageResult(
            total_spans=len(verification_results),
            verified_spans=len(verification_results),
            coverage_score=1.0,
        )


class MockConflictDetector:
    def __init__(self, conflicts=None):
        self._conflicts = conflicts

    async def detect(self, verification_results, state=None):
        if self._conflicts is not None:
            return self._conflicts
        return []


class MockSourceRanker:
    async def rank(self, sources, state=None):
        return sources


class MockConfidenceCalculator:
    def __init__(self, confidence_result=None):
        self._confidence_result = confidence_result

    async def calculate(
        self, verification_results, coverage=None, conflicts=None, citations=None, state=None
    ):
        if self._confidence_result is not None:
            return self._confidence_result
        return ConfidenceResult(
            overall=0.85,
            verification_confidence=0.9,
            citation_confidence=0.8,
            coverage_confidence=1.0,
            source_quality_confidence=0.8,
            suitable_for_ai=True,
            breakdown=[ConfidenceBreakdown(category="Verification", score=0.9, weight=0.35)],
        )


class MockProvenanceTracker:
    async def track(self, entry, state=None):
        return [entry]

    async def get_graph(self, entries):
        return {"entries": [], "total_time_ms": 0.0, "engine_count": 0}


class MockExplainabilityProvider:
    async def explain(
        self, verification_results, coverage=None, conflicts=None, confidence=None, citations=None, state=None
    ):
        return ExplanationResult(summary="Analysis complete.")


class MockBrokenPipeline:
    async def run(self, spans, citation_style=CitationStyle.AMA, config_override=None):
        raise RuntimeError("Pipeline crashed")


def make_span(claim="Aspirin reduces heart attack risk"):
    return EvidenceSpan(text=claim, claim=claim, span_start=0, span_end=len(claim))


def make_pipeline(**engine_overrides):
    defaults = dict(
        verifier=MockVerifier(),
        citation_generator=MockCitationGenerator(),
        citation_formatter=MockCitationFormatter(),
        coverage_analyzer=MockCoverageAnalyzer(),
        source_ranker=MockSourceRanker(),
        conflict_detector=MockConflictDetector(),
        confidence_calculator=MockConfidenceCalculator(),
        provenance_tracker=MockProvenanceTracker(),
        explainability_provider=MockExplainabilityProvider(),
    )
    defaults.update(engine_overrides)
    return EvidencePipeline(**defaults)


class TestEvidenceService:
    @pytest.mark.asyncio
    async def test_validate_evidence_empty_spans_returns_passed(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.validate_evidence([])

        assert result.passed is True
        assert result.summary == "No evidence spans to validate."
        assert result.processing_time_ms == 0.0

    @pytest.mark.asyncio
    async def test_validate_evidence_valid_spans_returns_passed(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.validate_evidence([make_span()])

        assert result.passed is True
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_validate_evidence_truncates_to_max_spans(self):
        config = EvidenceConfig(EVIDENCE_MAX_SPANS=2)
        service = EvidenceService(pipeline=make_pipeline(), config=config)
        spans = [make_span(f"Claim {i}") for i in range(10)]
        result = await service.validate_evidence(spans)

        assert any("Truncated" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_evidence_with_failed_pipeline_returns_failed(self):
        service = EvidenceService(pipeline=MockBrokenPipeline())
        result = await service.validate_evidence([make_span()])

        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_coverage_below_threshold_makes_passed_false(self):
        low_coverage = CoverageResult(
            total_spans=1, verified_spans=0, coverage_score=0.1, evidence_density=0.0
        )
        coverage_analyzer = MockCoverageAnalyzer(coverage_result=low_coverage)
        pipeline = make_pipeline(coverage_analyzer=coverage_analyzer)
        config = EvidenceConfig(EVIDENCE_COVERAGE_MIN_SCORE=0.3)
        service = EvidenceService(pipeline=pipeline, config=config)
        result = await service.validate_evidence([make_span()])

        assert result.passed is False
        assert any("coverage below minimum" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_multiple_conflicts_make_passed_false(self):
        conflicts = [
            ConflictResult(claim="C1", conflict_type=ConflictType.DIRECT, sources=[], severity="high"),
            ConflictResult(claim="C2", conflict_type=ConflictType.DIRECT, sources=[], severity="high"),
            ConflictResult(claim="C3", conflict_type=ConflictType.DIRECT, sources=[], severity="high"),
            ConflictResult(claim="C4", conflict_type=ConflictType.DIRECT, sources=[], severity="high"),
        ]
        detector = MockConflictDetector(conflicts=conflicts)
        pipeline = make_pipeline(conflict_detector=detector)
        service = EvidenceService(pipeline=pipeline)
        result = await service.validate_evidence([make_span()])

        assert result.passed is False
        assert any("conflict" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_few_conflicts_generates_warning_but_passes(self):
        conflicts = [
            ConflictResult(claim="C1", conflict_type=ConflictType.DIRECT, sources=[], severity="low"),
            ConflictResult(claim="C2", conflict_type=ConflictType.DIRECT, sources=[], severity="low"),
        ]
        detector = MockConflictDetector(conflicts=conflicts)
        pipeline = make_pipeline(conflict_detector=detector)
        service = EvidenceService(pipeline=pipeline)
        result = await service.validate_evidence([make_span()])

        assert result.passed is True
        assert any("conflict(s)" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_confidence_not_suitable_makes_passed_false(self):
        low_confidence = ConfidenceResult(
            overall=0.2,
            verification_confidence=0.2,
            citation_confidence=0.2,
            coverage_confidence=0.2,
            source_quality_confidence=0.2,
            suitable_for_ai=False,
        )
        calculator = MockConfidenceCalculator(confidence_result=low_confidence)
        pipeline = make_pipeline(confidence_calculator=calculator)
        service = EvidenceService(pipeline=pipeline)
        result = await service.validate_evidence([make_span()])

        assert result.passed is False
        assert any("confidence below" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_verify_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.verify([make_span()])
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_generate_citations_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.generate_citations([make_span()], style=CitationStyle.APA)
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_analyze_coverage_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.analyze_coverage([make_span()])
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_detect_conflicts_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.detect_conflicts([make_span()])
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_calculate_confidence_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.calculate_confidence([make_span()])
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_get_provenance_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.get_provenance([make_span()])
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_get_explanation_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.get_explanation([make_span()])
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_full_pipeline_delegates_to_pipeline(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.full_pipeline([make_span()], citation_style=CitationStyle.VANCOUVER)
        assert isinstance(result, PipelineResult)

    @pytest.mark.asyncio
    async def test_service_uses_config(self):
        config = EvidenceConfig(EVIDENCE_MAX_SPANS=5)
        service = EvidenceService(pipeline=make_pipeline(), config=config)
        assert service._config.EVIDENCE_MAX_SPANS == 5

    @pytest.mark.asyncio
    async def test_warning_messages_in_result(self):
        conflicts = [
            ConflictResult(claim="C1", conflict_type=ConflictType.DIRECT, sources=[], severity="high"),
        ]
        detector = MockConflictDetector(conflicts=conflicts)
        pipeline = make_pipeline(conflict_detector=detector)
        service = EvidenceService(pipeline=pipeline)
        result = await service.validate_evidence([make_span()])

        assert len(result.warnings) > 0
        assert "1 evidence conflict(s)" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_summary_includes_confidence_and_coverage(self):
        service = EvidenceService(pipeline=make_pipeline())
        result = await service.validate_evidence([make_span()])

        assert "Confidence: 85.0%" in result.summary
        assert "Coverage: 100%" in result.summary
