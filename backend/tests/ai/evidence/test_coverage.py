import pytest

from app.ai.evidence.engines.coverage import CoverageAnalyzerEngine
from app.ai.evidence.schemas import (
    CoverageGap,
    CoverageResult,
    EvidenceSpan,
    EvidenceState,
    EvidenceType,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)


@pytest.fixture
def analyzer():
    return CoverageAnalyzerEngine()


@pytest.fixture
def sample_span():
    return EvidenceSpan(text="Patient has hypertension", claim="Patient has hypertension")


@pytest.fixture
def verified_result(sample_span):
    return VerificationResult(
        span=sample_span,
        verified=True,
        status=VerificationStatus.VERIFIED,
        supporting_sources=[
            VerifiedSource(
                source_id="src_1",
                title="Guideline",
                evidence_type="guideline",
                authority_score=0.8,
                relevance_score=0.9,
                recency_score=0.85,
                quality_score=0.75,
                support_direction="supporting",
                excerpt="Evidence supports...",
            )
        ],
        contradicting_sources=[],
        confidence=0.85,
        evidence_summary="Well-supported.",
    )


@pytest.fixture
def unverified_result(sample_span):
    return VerificationResult(
        span=sample_span,
        verified=False,
        status=VerificationStatus.UNVERIFIED,
        supporting_sources=[],
        contradicting_sources=[],
        confidence=0.0,
        evidence_summary="No evidence found.",
    )


@pytest.fixture
def partial_result(sample_span):
    return VerificationResult(
        span=sample_span,
        verified=True,
        status=VerificationStatus.PARTIALLY_VERIFIED,
        supporting_sources=[
            VerifiedSource(
                source_id="src_sup",
                title="Supporting Study",
                    evidence_type=EvidenceType.META_ANALYSIS,
                    authority_score=0.6,
                    relevance_score=0.7,
                    recency_score=0.5,
                    quality_score=0.6,
                    support_direction="supporting",
                    excerpt="Some evidence...",
                )
            ],
            contradicting_sources=[
                VerifiedSource(
                    source_id="src_con",
                    title="Contradicting Study",
                    evidence_type=EvidenceType.CASE_STUDY,
                authority_score=0.5,
                relevance_score=0.6,
                recency_score=0.4,
                quality_score=0.5,
                support_direction="contradicting",
                excerpt="Contradicts claim...",
            )
        ],
        confidence=0.4,
        evidence_summary="Mixed evidence.",
    )


@pytest.fixture
def contradicted_result(sample_span):
    return VerificationResult(
        span=sample_span,
        verified=False,
        status=VerificationStatus.CONTRADICTED,
        supporting_sources=[],
        contradicting_sources=[
            VerifiedSource(
                source_id="src_con",
                title="Contradicting Study",
                    evidence_type=EvidenceType.EXPERT_OPINION,
                    authority_score=0.7,
                    relevance_score=0.8,
                    recency_score=0.6,
                    quality_score=0.7,
                    support_direction="contradicting",
                    excerpt="Evidence contradicts...",
            )
        ],
        confidence=0.0,
        evidence_summary="Contradicted.",
    )


class TestCoverageAnalyzerEngine:
    @pytest.mark.asyncio
    async def test_empty_results_returns_default(self, analyzer):
        result = await analyzer.analyze([])
        assert isinstance(result, CoverageResult)
        assert result.total_spans == 0
        assert result.verified_spans == 0
        assert result.unverified_spans == 0
        assert result.partially_verified_spans == 0
        assert result.coverage_score == 0.0
        assert result.evidence_density == 0.0
        assert result.gaps == []
        assert result.recommendations == []

    @pytest.mark.asyncio
    async def test_all_verified_gives_high_coverage(
        self, analyzer, verified_result
    ):
        result = await analyzer.analyze([verified_result, verified_result])
        assert result.total_spans == 2
        assert result.verified_spans == 2
        assert result.coverage_score == 1.0

    @pytest.mark.asyncio
    async def test_all_unverified_gives_low_coverage(
        self, analyzer, unverified_result
    ):
        result = await analyzer.analyze([unverified_result, unverified_result])
        assert result.total_spans == 2
        assert result.unverified_spans == 2
        assert result.coverage_score == 0.0

    @pytest.mark.asyncio
    async def test_partial_verified_gives_medium_coverage(
        self, analyzer, partial_result
    ):
        result = await analyzer.analyze([partial_result])
        assert result.partially_verified_spans == 1
        assert result.coverage_score == 0.5

    @pytest.mark.asyncio
    async def test_mixed_results(
        self, analyzer, verified_result, unverified_result, partial_result
    ):
        result = await analyzer.analyze(
            [verified_result, verified_result, unverified_result, partial_result]
        )
        assert result.total_spans == 4
        assert result.verified_spans == 2
        assert result.unverified_spans == 1
        assert result.partially_verified_spans == 1
        assert result.coverage_score == pytest.approx(0.625)

    @pytest.mark.asyncio
    async def test_coverage_score_formula(
        self, analyzer, verified_result, unverified_result, partial_result
    ):
        result = await analyzer.analyze(
            [verified_result, unverified_result, partial_result]
        )
        expected = (1 + 0.5) / 3
        assert result.coverage_score == pytest.approx(expected)

    @pytest.mark.asyncio
    async def test_evidence_density_computation(
        self, analyzer, verified_result, unverified_result
    ):
        result = await analyzer.analyze([verified_result, unverified_result])
        expected = (1 + 0) / 2
        assert result.evidence_density == pytest.approx(expected)

    @pytest.mark.asyncio
    async def test_all_contradicted_gives_low_coverage(
        self, analyzer, contradicted_result
    ):
        result = await analyzer.analyze(
            [contradicted_result, contradicted_result]
        )
        assert result.coverage_score == 0.0

    @pytest.mark.asyncio
    async def test_gaps_found_for_unverified(
        self, analyzer, unverified_result
    ):
        result = await analyzer.analyze([unverified_result])
        assert len(result.gaps) == 1
        assert result.gaps[0].gap_type == "unverified"
        assert result.gaps[0].severity == "high"

    @pytest.mark.asyncio
    async def test_gaps_found_for_contradicted(
        self, analyzer, contradicted_result
    ):
        result = await analyzer.analyze([contradicted_result])
        assert len(result.gaps) == 1
        assert result.gaps[0].gap_type == "contradicted"
        assert result.gaps[0].severity == "high"

    @pytest.mark.asyncio
    async def test_gaps_found_for_partial(
        self, analyzer, partial_result
    ):
        result = await analyzer.analyze([partial_result])
        assert len(result.gaps) == 1
        assert result.gaps[0].gap_type == "insufficient"
        assert result.gaps[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_no_gaps_for_fully_verified(
        self, analyzer, verified_result
    ):
        result = await analyzer.analyze([verified_result])
        assert len(result.gaps) == 0

    @pytest.mark.asyncio
    async def test_recommendations_for_low_coverage(
        self, analyzer, unverified_result
    ):
        result = await analyzer.analyze([unverified_result, unverified_result])
        assert "Increase evidence coverage to improve confidence." in result.recommendations

    @pytest.mark.asyncio
    async def test_recommendations_for_contradicted(
        self, analyzer, contradicted_result
    ):
        result = await analyzer.analyze([contradicted_result])
        assert any(
            "Review contradicted claims" in r for r in result.recommendations
        )

    @pytest.mark.asyncio
    async def test_recommendations_for_unverified(
        self, analyzer, unverified_result
    ):
        result = await analyzer.analyze([unverified_result])
        assert any(
            "Add sources for unverified claims" in r for r in result.recommendations
        )

    @pytest.mark.asyncio
    async def test_recommendations_for_partial(
        self, analyzer, partial_result
    ):
        result = await analyzer.analyze([partial_result])
        assert any(
            "additional supporting references" in r for r in result.recommendations
        )

    @pytest.mark.asyncio
    async def test_adequate_coverage_recommendation(
        self, analyzer, verified_result
    ):
        result = await analyzer.analyze([verified_result, verified_result])
        assert "Evidence coverage is adequate." in result.recommendations

    @pytest.mark.asyncio
    async def test_analyze_with_state(
        self, analyzer, verified_result
    ):
        state = EvidenceState(config={"threshold": 0.5})
        result = await analyzer.analyze([verified_result], state=state)
        assert result.verified_spans == 1

    @pytest.mark.asyncio
    async def test_multiple_gap_types(
        self, analyzer, unverified_result, contradicted_result, partial_result
    ):
        result = await analyzer.analyze(
            [unverified_result, contradicted_result, partial_result]
        )
        gap_types = {g.gap_type for g in result.gaps}
        assert "unverified" in gap_types
        assert "contradicted" in gap_types
        assert "insufficient" in gap_types

    @pytest.mark.asyncio
    async def test_evidence_density_with_mixed_sources(
        self, analyzer, verified_result, partial_result
    ):
        result = await analyzer.analyze([verified_result, partial_result])
        expected = (1 + 2) / 2
        assert result.evidence_density == pytest.approx(expected)
