import pytest

from app.ai.evidence.engines.confidence import ConfidenceCalculatorEngine
from app.ai.evidence.schemas import (
    Citation,
    ConfidenceBreakdown,
    ConflictResult,
    ConflictType,
    CoverageResult,
    EvidenceSpan,
    EvidenceType,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)


def _make_source(
    source_id: str = "s1",
    authority: float = 0.8,
    relevance: float = 0.8,
    recency: float = 0.8,
    quality: float = 0.8,
) -> VerifiedSource:
    return VerifiedSource(
        source_id=source_id,
        evidence_type=EvidenceType.DIRECT,
        authority_score=authority,
        relevance_score=relevance,
        recency_score=recency,
        quality_score=quality,
    )


def _make_vr(
    status: VerificationStatus = VerificationStatus.VERIFIED,
    confidence: float = 0.9,
    supporting: list[VerifiedSource] | None = None,
    contradicting: list[VerifiedSource] | None = None,
) -> VerificationResult:
    return VerificationResult(
        span=EvidenceSpan(text="test", claim="test"),
        verified=status == VerificationStatus.VERIFIED,
        status=status,
        supporting_sources=[_make_source()] if supporting is None else supporting,
        contradicting_sources=[] if contradicting is None else contradicting,
        confidence=confidence,
    )


def _make_conflict(severity: str = "high") -> ConflictResult:
    return ConflictResult(
        claim="test claim",
        conflict_type=ConflictType.DIRECT,
        sources=[_make_source()],
        severity=severity,
    )


class TestConfidenceCalculatorEngine:
    @pytest.mark.asyncio
    async def test_empty_results_returns_zero_confidence(self):
        engine = ConfidenceCalculatorEngine()
        result = await engine.calculate([])
        assert result.overall == 0.2
        assert result.suitable_for_ai is False

    @pytest.mark.asyncio
    async def test_high_confidence_when_all_verified_with_good_sources(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.95),
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.95),
        ]
        cov = CoverageResult(
            total_spans=2,
            verified_spans=2,
            coverage_score=0.9,
        )
        result = await engine.calculate(vrs, coverage=cov)
        assert result.overall >= 0.7
        assert result.suitable_for_ai is True

    @pytest.mark.asyncio
    async def test_low_confidence_when_all_unverified(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.UNVERIFIED, confidence=0.0),
            _make_vr(status=VerificationStatus.UNVERIFIED, confidence=0.0),
        ]
        result = await engine.calculate(vrs)
        assert result.overall < 0.4
        assert result.suitable_for_ai is False

    @pytest.mark.asyncio
    async def test_contradicted_results_lower_confidence(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(
                status=VerificationStatus.CONTRADICTED,
                confidence=0.0,
                supporting=[],
                contradicting=[_make_source(authority=0.0, relevance=0.0, recency=0.0, quality=0.0)],
            ),
        ]
        cov = CoverageResult(total_spans=1, verified_spans=0, coverage_score=0.0)
        result = await engine.calculate(vrs, coverage=cov)
        assert result.overall < 0.3

    @pytest.mark.asyncio
    async def test_coverage_influences_confidence(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.9),
        ]
        cov_high = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.9)
        cov_low = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.1)
        result_high = await engine.calculate(vrs, coverage=cov_high)
        result_low = await engine.calculate(vrs, coverage=cov_low)
        assert result_high.overall > result_low.overall

    @pytest.mark.asyncio
    async def test_citations_influence_confidence(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.9),
        ]
        cov = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.9)
        cits_high = [
            Citation(
                citation_id="c1",
                evidence_text="evidence",
                source=_make_source(),
                confidence=0.95,
            )
        ]
        cits_low = [
            Citation(
                citation_id="c2",
                evidence_text="evidence",
                source=_make_source(),
                confidence=0.1,
            )
        ]
        result_high = await engine.calculate(vrs, coverage=cov, citations=cits_high)
        result_low = await engine.calculate(vrs, coverage=cov, citations=cits_low)
        assert result_high.overall > result_low.overall

    @pytest.mark.asyncio
    async def test_conflicts_reduce_confidence(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.9),
        ]
        cov = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.9)
        conflicts = [_make_conflict(severity="high")]
        result_no_conflict = await engine.calculate(vrs, coverage=cov)
        result_with_conflict = await engine.calculate(vrs, coverage=cov, conflicts=conflicts)
        assert result_with_conflict.overall < result_no_conflict.overall

    @pytest.mark.asyncio
    async def test_suitable_for_ai_based_on_threshold(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.1),
        ]
        result_low = await engine.calculate(vrs)
        assert result_low.suitable_for_ai is False

        vrs_high = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.95),
        ]
        cov_high = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.9)
        result_high = await engine.calculate(vrs_high, coverage=cov_high)
        assert result_high.suitable_for_ai is True

    @pytest.mark.asyncio
    async def test_breakdown_includes_all_four_categories(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [_make_vr()]
        result = await engine.calculate(vrs)
        categories = {b.category for b in result.breakdown}
        assert categories == {"Verification", "Citation", "Coverage", "Source Quality"}

    @pytest.mark.asyncio
    async def test_breakdown_has_scores_and_weights(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(
                status=VerificationStatus.VERIFIED,
                confidence=0.8,
                supporting=[_make_source(source_id="s1")],
            ),
        ]
        cov = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.75)
        cits = [
            Citation(
                citation_id="c1",
                evidence_text="evidence",
                source=_make_source(),
                confidence=0.85,
            )
        ]
        result = await engine.calculate(vrs, coverage=cov, citations=cits)
        for b in result.breakdown:
            assert 0.0 <= b.score <= 1.0
            assert b.weight > 0.0

    @pytest.mark.asyncio
    async def test_warnings_for_low_verification(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.UNVERIFIED, confidence=0.0),
        ]
        result = await engine.calculate(vrs)
        assert any("Low verification" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_warnings_for_low_coverage(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.9),
        ]
        cov = CoverageResult(total_spans=10, verified_spans=1, coverage_score=0.1)
        result = await engine.calculate(vrs, coverage=cov)
        assert any("Insufficient evidence coverage" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_warnings_for_multiple_conflicts(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [_make_vr(status=VerificationStatus.VERIFIED, confidence=0.9)]
        cov = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.9)
        conflicts = [
            _make_conflict(severity="low"),
            _make_conflict(severity="low"),
            _make_conflict(severity="low"),
        ]
        result = await engine.calculate(vrs, coverage=cov, conflicts=conflicts)
        assert any("Multiple conflicts" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_warning_for_below_threshold(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.UNVERIFIED, confidence=0.0),
        ]
        result = await engine.calculate(vrs)
        assert any("below suitable" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_conflict_penalty_capped_at_0_5(self):
        engine = ConfidenceCalculatorEngine()
        many_conflicts = [
            _make_conflict(severity="high"),
            _make_conflict(severity="high"),
            _make_conflict(severity="high"),
            _make_conflict(severity="high"),
        ]
        penalty = engine._conflict_penalty(many_conflicts)
        assert penalty == 0.5

    @pytest.mark.asyncio
    async def test_conflict_penalty_respects_severity(self):
        engine = ConfidenceCalculatorEngine()
        high_penalty = engine._conflict_penalty([_make_conflict(severity="high")])
        med_penalty = engine._conflict_penalty([_make_conflict(severity="medium")])
        low_penalty = engine._conflict_penalty([_make_conflict(severity="low")])
        assert high_penalty == 0.15
        assert med_penalty == 0.08
        assert low_penalty == 0.03

    @pytest.mark.asyncio
    async def test_no_conflict_penalty_when_none(self):
        engine = ConfidenceCalculatorEngine()
        assert engine._conflict_penalty([]) == 0.0
        assert engine._conflict_penalty(None) == 0.0

    @pytest.mark.asyncio
    async def test_overall_clamped_between_zero_and_one(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.UNVERIFIED, confidence=0.0),
        ]
        result = await engine.calculate(vrs)
        assert 0.0 <= result.overall <= 1.0

    @pytest.mark.asyncio
    async def test_no_coverage_uses_zero(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.9),
        ]
        result_no_cov = await engine.calculate(vrs)
        result_with_cov = await engine.calculate(
            vrs,
            coverage=CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.8),
        )
        assert result_no_cov.overall < result_with_cov.overall

    @pytest.mark.asyncio
    async def test_no_citations_default_to_full_citation_confidence(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, confidence=0.9),
        ]
        result = await engine.calculate(vrs)
        assert result.citation_confidence == 1.0

    @pytest.mark.asyncio
    async def test_zero_citations_returns_zero(self):
        engine = ConfidenceCalculatorEngine()
        assert engine._citation_confidence([]) == 0.0

    @pytest.mark.asyncio
    async def test_verification_confidence_empty_returns_zero(self):
        engine = ConfidenceCalculatorEngine()
        assert engine._verification_confidence([]) == 0.0

    @pytest.mark.asyncio
    async def test_source_quality_confidence_empty_returns_zero(self):
        engine = ConfidenceCalculatorEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED, supporting=[], contradicting=[]),
        ]
        result = await engine.calculate(vrs)
        assert result.source_quality_confidence == 0.0

    @pytest.mark.asyncio
    async def test_source_quality_averages_all_source_scores(self):
        engine = ConfidenceCalculatorEngine()
        high = _make_source(source_id="high", authority=1.0, relevance=1.0, recency=1.0, quality=1.0)
        low = _make_source(source_id="low", authority=0.0, relevance=0.0, recency=0.0, quality=0.0)
        vrs = [
            _make_vr(
                status=VerificationStatus.VERIFIED,
                supporting=[high, low],
            ),
        ]
        result = await engine.calculate(vrs)
        assert result.source_quality_confidence == 0.5
