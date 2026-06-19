import pytest

from app.ai.evidence.engines.conflict import ConflictDetectorEngine
from app.ai.evidence.schemas import (
    ConflictType,
    EvidenceSpan,
    EvidenceState,
    EvidenceType,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)


def _make_source(source_id: str) -> VerifiedSource:
    return VerifiedSource(
        source_id=source_id,
        evidence_type=EvidenceType.DIRECT,
        authority_score=0.8,
        relevance_score=0.8,
        recency_score=0.8,
        quality_score=0.8,
    )


def _make_vr(
    claim: str,
    status: VerificationStatus = VerificationStatus.VERIFIED,
    contradicting: list[VerifiedSource] | None = None,
    supporting: list[VerifiedSource] | None = None,
    confidence: float = 0.9,
) -> VerificationResult:
    return VerificationResult(
        span=EvidenceSpan(text=claim, claim=claim),
        verified=status == VerificationStatus.VERIFIED,
        status=status,
        supporting_sources=supporting or [_make_source("s1")],
        contradicting_sources=contradicting or [],
        confidence=confidence,
    )


class TestConflictDetectorEngine:
    @pytest.mark.asyncio
    async def test_empty_results_returns_empty(self):
        engine = ConflictDetectorEngine()
        result = await engine.detect([])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_contradicting_sources_returns_empty(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr("Aspirin is safe for most patients.")
        result = await engine.detect([vr])
        assert result == []

    @pytest.mark.asyncio
    async def test_detects_contradictory_type_with_contraindicated(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This drug is contraindicated in elderly patients.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert len(result) == 1
        assert result[0].conflict_type == ConflictType.CONTRADICTORY
        assert result[0].severity == "high"

    @pytest.mark.asyncio
    async def test_detects_contradictory_type_with_no_evidence(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "There is no evidence supporting this treatment.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert len(result) == 1
        assert result[0].conflict_type == ConflictType.CONTRADICTORY

    @pytest.mark.asyncio
    async def test_detects_contradictory_type_with_not_recommended(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This medication is not recommended for children.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert len(result) == 1
        assert result[0].conflict_type == ConflictType.CONTRADICTORY

    @pytest.mark.asyncio
    async def test_detects_contradictory_type_with_harmful(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This herb can be harmful in large doses.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert len(result) == 1
        assert result[0].conflict_type == ConflictType.CONTRADICTORY

    @pytest.mark.asyncio
    async def test_detects_directional_type_with_increase(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This drug may increase blood pressure.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert len(result) == 1
        assert result[0].conflict_type == ConflictType.DIRECTIONAL
        assert result[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_detects_directional_type_with_improve(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "Exercise might improve cognitive function.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert len(result) == 1
        assert result[0].conflict_type == ConflictType.DIRECTIONAL

    @pytest.mark.asyncio
    async def test_detects_direct_type_fallback(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "The patient should take 500mg daily.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert len(result) == 1
        assert result[0].conflict_type == ConflictType.DIRECT
        assert result[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_detects_cross_claim_conflict(self):
        engine = ConflictDetectorEngine()
        vr1 = _make_vr(
            "Aspirin is effective for headache relief.",
            status=VerificationStatus.VERIFIED,
        )
        vr2 = _make_vr(
            "Aspirin is not effective for headache relief.",
            status=VerificationStatus.CONTRADICTED,
        )
        result = await engine.detect([vr1, vr2])
        cross = [c for c in result if "Cross-claim" in (c.description or "")]
        assert len(cross) == 1
        assert cross[0].conflict_type == ConflictType.DIRECTIONAL
        assert cross[0].severity == "low"

    @pytest.mark.asyncio
    async def test_no_cross_claim_conflict_when_both_verified(self):
        engine = ConflictDetectorEngine()
        vr1 = _make_vr(
            "Aspirin is effective for headache relief.",
            status=VerificationStatus.VERIFIED,
        )
        vr2 = _make_vr(
            "Aspirin is effective for migraine relief.",
            status=VerificationStatus.VERIFIED,
        )
        result = await engine.detect([vr1, vr2])
        cross = [c for c in result if "Cross-claim" in (c.description or "")]
        assert len(cross) == 0

    @pytest.mark.asyncio
    async def test_cross_claim_requires_word_overlap(self):
        engine = ConflictDetectorEngine()
        vr1 = _make_vr(
            "Aspirin helps headaches.",
            status=VerificationStatus.VERIFIED,
        )
        vr2 = _make_vr(
            "Ibuprofen treats muscle pain.",
            status=VerificationStatus.CONTRADICTED,
        )
        result = await engine.detect([vr1, vr2])
        cross = [c for c in result if "Cross-claim" in (c.description or "")]
        assert len(cross) == 0

    @pytest.mark.asyncio
    async def test_severity_high_for_contradictory(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This is contraindicated in pregnancy.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert result[0].severity == "high"

    @pytest.mark.asyncio
    async def test_severity_medium_for_directional(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This may decrease cholesterol.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert result[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_severity_medium_for_direct(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "Take one tablet daily.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert result[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_conflict_description_is_populated(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "Avoid this medication with grapefruit juice.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert result[0].description is not None
        assert "Avoid this medication" in result[0].description

    @pytest.mark.asyncio
    async def test_resolution_text_is_set(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This should not be used with MAOIs.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert result[0].resolution is not None
        assert len(result[0].resolution) > 0

    @pytest.mark.asyncio
    async def test_multiple_conflicts_detected(self):
        engine = ConflictDetectorEngine()
        vrs = [
            _make_vr("contraindicated in children.", contradicting=[_make_source("s2")]),
            _make_vr("may increase heart rate.", contradicting=[_make_source("s3")]),
            _make_vr("Take with food.", contradicting=[_make_source("s4")]),
        ]
        result = await engine.detect(vrs)
        assert len(result) >= 3

    @pytest.mark.asyncio
    async def test_contradictory_precedence_over_directional(self):
        engine = ConflictDetectorEngine()
        vr = _make_vr(
            "This is contraindicated and may increase risk.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr])
        assert result[0].conflict_type == ConflictType.CONTRADICTORY

    @pytest.mark.asyncio
    async def test_span_index_is_set(self):
        engine = ConflictDetectorEngine()
        vrs = [
            _make_vr("First claim.", contradicting=[_make_source("s2")]),
            _make_vr("Second claim.", contradicting=[_make_source("s3")]),
        ]
        result = await engine.detect(vrs)
        assert result[0].span_index == 0
        assert result[1].span_index == 1

    @pytest.mark.asyncio
    async def test_sources_are_populated(self):
        engine = ConflictDetectorEngine()
        src = _make_source("contra")
        vr = _make_vr(
            "Not recommended for elderly.",
            contradicting=[src],
        )
        result = await engine.detect([vr])
        assert len(result[0].sources) > 0
        assert result[0].sources[0].source_id == "contra"

    @pytest.mark.asyncio
    async def test_state_accepted_but_not_modified(self):
        engine = ConflictDetectorEngine()
        state = EvidenceState()
        vr = _make_vr(
            "Avoid in renal impairment.",
            contradicting=[_make_source("s2")],
        )
        result = await engine.detect([vr], state=state)
        assert len(result) == 1
