import pytest

from app.ai.evidence.engines.explain import ExplainabilityProviderEngine
from app.ai.evidence.schemas import (
    Citation,
    ConfidenceResult,
    ConflictResult,
    ConflictType,
    CoverageResult,
    EvidenceSpan,
    EvidenceType,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)


def _make_source(source_id: str = "s1") -> VerifiedSource:
    return VerifiedSource(
        source_id=source_id,
        evidence_type=EvidenceType.DIRECT,
        authority_score=0.8,
        relevance_score=0.8,
        recency_score=0.8,
        quality_score=0.8,
    )


def _make_vr(
    status: VerificationStatus = VerificationStatus.VERIFIED,
    confidence: float = 0.9,
) -> VerificationResult:
    return VerificationResult(
        span=EvidenceSpan(text="test claim", claim="test claim"),
        verified=status == VerificationStatus.VERIFIED,
        status=status,
        supporting_sources=[_make_source()],
        confidence=confidence,
    )


class TestExplainabilityProviderEngine:
    @pytest.mark.asyncio
    async def test_empty_results_returns_summary_with_zero_zero(self):
        engine = ExplainabilityProviderEngine()
        result = await engine.explain([])
        assert "0/0" in result.summary or "0 verified" in result.summary

    @pytest.mark.asyncio
    async def test_all_verified_creates_proper_components(self):
        engine = ExplainabilityProviderEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED),
            _make_vr(status=VerificationStatus.VERIFIED),
            _make_vr(status=VerificationStatus.VERIFIED),
        ]
        result = await engine.explain(vrs)
        comps = {c.component for c in result.components}
        assert "Verification" in comps
        assert "Coverage" in comps
        assert "Conflicts" in comps

    @pytest.mark.asyncio
    async def test_narrative_includes_verification_data(self):
        engine = ExplainabilityProviderEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED),
            _make_vr(status=VerificationStatus.UNVERIFIED),
        ]
        result = await engine.explain(vrs)
        assert result.narrative is not None
        assert "1 were verified" in result.narrative or "verified" in result.narrative

    @pytest.mark.asyncio
    async def test_narrative_includes_coverage_when_provided(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        cov = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.85)
        result = await engine.explain(vrs, coverage=cov)
        assert "85%" in result.narrative or "coverage" in result.narrative.lower()

    @pytest.mark.asyncio
    async def test_narrative_includes_conflicts_when_provided(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        conflicts = [
            ConflictResult(
                claim="test claim",
                conflict_type=ConflictType.DIRECT,
                sources=[_make_source()],
            ),
        ]
        result = await engine.explain(vrs, conflicts=conflicts)
        assert "1 evidence conflict" in result.narrative or "conflict" in result.narrative

    @pytest.mark.asyncio
    async def test_narrative_includes_confidence_when_provided(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        confidence = ConfidenceResult(
            overall=0.75,
            verification_confidence=0.8,
            citation_confidence=0.7,
            coverage_confidence=0.6,
            source_quality_confidence=0.9,
            suitable_for_ai=True,
        )
        result = await engine.explain(vrs, confidence=confidence)
        assert "75%" in result.narrative or "confidence" in result.narrative.lower()

    @pytest.mark.asyncio
    async def test_verification_summary_counts_all_statuses(self):
        engine = ExplainabilityProviderEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED),
            _make_vr(status=VerificationStatus.PARTIALLY_VERIFIED),
            _make_vr(status=VerificationStatus.UNVERIFIED),
            _make_vr(status=VerificationStatus.CONTRADICTED),
        ]
        result = await engine.explain(vrs)
        assert "Verified: 1" in result.verification_summary
        assert "Partially: 1" in result.verification_summary
        assert "Unverified: 1" in result.verification_summary
        assert "Contradicted: 1" in result.verification_summary

    @pytest.mark.asyncio
    async def test_citation_summary_shows_count(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        citations = [
            Citation(
                citation_id="c1",
                evidence_text="evidence",
                source=_make_source(),
                confidence=0.9,
            ),
            Citation(
                citation_id="c2",
                evidence_text="evidence",
                source=_make_source(),
                confidence=0.8,
            ),
        ]
        result = await engine.explain(vrs, citations=citations)
        assert "2 citations" in result.citation_summary

    @pytest.mark.asyncio
    async def test_citation_summary_default_when_none(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        result = await engine.explain(vrs)
        assert result.citation_summary == "No citations"

    @pytest.mark.asyncio
    async def test_coverage_summary_shows_percentage(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        cov = CoverageResult(total_spans=4, verified_spans=3, coverage_score=0.75)
        result = await engine.explain(vrs, coverage=cov)
        assert "75.0%" in result.coverage_summary or "75%" in result.coverage_summary

    @pytest.mark.asyncio
    async def test_coverage_summary_default_when_none(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        result = await engine.explain(vrs)
        assert result.coverage_summary == "Not analyzed"

    @pytest.mark.asyncio
    async def test_conflict_summary_shows_count(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        conflicts = [
            ConflictResult(
                claim="test claim",
                conflict_type=ConflictType.DIRECT,
                sources=[_make_source()],
            ),
            ConflictResult(
                claim="test claim 2",
                conflict_type=ConflictType.DIRECTIONAL,
                sources=[_make_source()],
            ),
        ]
        result = await engine.explain(vrs, conflicts=conflicts)
        assert "2 conflict" in result.conflict_summary

    @pytest.mark.asyncio
    async def test_confidence_summary_shows_percentage(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        confidence = ConfidenceResult(
            overall=0.65,
            verification_confidence=0.7,
            citation_confidence=0.6,
            coverage_confidence=0.5,
            source_quality_confidence=0.8,
            suitable_for_ai=True,
        )
        result = await engine.explain(vrs, confidence=confidence)
        assert "65.0%" in result.confidence_summary or "65%" in result.confidence_summary

    @pytest.mark.asyncio
    async def test_confidence_summary_default_when_none(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        result = await engine.explain(vrs)
        assert result.confidence_summary == "Not calculated"

    @pytest.mark.asyncio
    async def test_none_inputs_do_not_crash(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        result = await engine.explain(
            vrs,
            coverage=None,
            conflicts=None,
            confidence=None,
            citations=None,
        )
        assert result is not None
        assert len(result.components) >= 3

    @pytest.mark.asyncio
    async def test_empty_verification_results_do_not_crash(self):
        engine = ExplainabilityProviderEngine()
        result = await engine.explain(
            [],
            coverage=None,
            conflicts=None,
            confidence=None,
            citations=None,
        )
        assert result is not None
        assert "0/0" in result.summary or "0 verified" in result.summary

    @pytest.mark.asyncio
    async def test_recommendations_default_empty(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        result = await engine.explain(vrs)
        assert result.recommendations == []

    @pytest.mark.asyncio
    async def test_confidence_component_included_when_provided(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        confidence = ConfidenceResult(
            overall=0.8,
            verification_confidence=0.8,
            citation_confidence=0.8,
            coverage_confidence=0.8,
            source_quality_confidence=0.8,
            suitable_for_ai=True,
        )
        result = await engine.explain(vrs, confidence=confidence)
        comps = {c.component for c in result.components}
        assert "Confidence" in comps

    @pytest.mark.asyncio
    async def test_confidence_component_not_included_when_missing(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        result = await engine.explain(vrs)
        comps = {c.component for c in result.components}
        assert "Confidence" not in comps

    @pytest.mark.asyncio
    async def test_verification_component_detail(self):
        engine = ExplainabilityProviderEngine()
        vrs = [
            _make_vr(status=VerificationStatus.VERIFIED),
            _make_vr(status=VerificationStatus.UNVERIFIED),
            _make_vr(status=VerificationStatus.VERIFIED),
        ]
        result = await engine.explain(vrs)
        ver_comp = next(c for c in result.components if c.component == "Verification")
        assert "2/3" in ver_comp.detail

    @pytest.mark.asyncio
    async def test_coverage_component_detail_with_data(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        cov = CoverageResult(total_spans=1, verified_spans=1, coverage_score=0.9)
        result = await engine.explain(vrs, coverage=cov)
        cov_comp = next(c for c in result.components if c.component == "Coverage")
        assert "0.90" in cov_comp.detail

    @pytest.mark.asyncio
    async def test_conflicts_component_score_reflects_count(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        conflicts = [
            ConflictResult(
                claim="c1",
                conflict_type=ConflictType.DIRECT,
                sources=[_make_source()],
            ),
        ]
        result = await engine.explain(vrs, conflicts=conflicts)
        conf_comp = next(c for c in result.components if c.component == "Conflicts")
        assert conf_comp.score == 0.8

    @pytest.mark.asyncio
    async def test_explain_accepts_state_parameter(self):
        engine = ExplainabilityProviderEngine()
        vrs = [_make_vr()]
        from app.ai.evidence.schemas import EvidenceState
        state = EvidenceState()
        result = await engine.explain(vrs, state=state)
        assert result is not None
