import pytest

from app.ai.evidence.engines.verifier import EvidenceVerifierEngine
from app.ai.evidence.schemas import (
    EvidenceSpan,
    EvidenceState,
    EvidenceType,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)


class MockKnowledgeService:
    async def search(self, claim: str) -> list[dict]:
        return [
            {
                "content": f"Evidence found for: {claim}",
                "score": 0.85,
                "title": f"Source: {claim[:30]}",
            }
        ]


@pytest.fixture
def engine():
    return EvidenceVerifierEngine()


@pytest.fixture
def engine_with_kb():
    return EvidenceVerifierEngine(knowledge_service=MockKnowledgeService())


@pytest.fixture
def sample_span():
    return EvidenceSpan(
        text="Patient has high blood pressure",
        claim="Patient has hypertension",
        span_start=0,
        span_end=35,
        context="Cardiology report",
    )


@pytest.fixture
def sample_spans(sample_span):
    return [
        sample_span,
        EvidenceSpan(
            text="Patient was prescribed aspirin",
            claim="Aspirin 81mg daily prescribed",
            span_start=36,
            span_end=65,
            context="Medication list",
        ),
        EvidenceSpan(
            text="Previous history of stroke",
            claim="Patient had ischemic stroke in 2020",
            span_start=66,
            span_end=95,
            context="History section",
        ),
    ]


class TestEvidenceVerifierEngine:
    @pytest.mark.asyncio
    async def test_verify_empty_list(self, engine):
        result = await engine.verify([])
        assert result == []

    @pytest.mark.asyncio
    async def test_verify_single_span_returns_verification_result(
        self, engine, sample_span
    ):
        results = await engine.verify([sample_span])
        assert len(results) == 1
        assert isinstance(results[0], VerificationResult)
        assert results[0].span == sample_span

    @pytest.mark.asyncio
    async def test_verify_multiple_spans(self, engine, sample_spans):
        results = await engine.verify(sample_spans)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_mock_sources_generated_when_no_knowledge_service(
        self, engine, sample_span
    ):
        results = await engine.verify([sample_span])
        vr = results[0]
        assert len(vr.supporting_sources) > 0
        for src in vr.supporting_sources:
            assert src.source_id == "src_mock_1"
            assert src.support_direction == "supporting"

    @pytest.mark.asyncio
    async def test_verified_status_for_supporting_only(self, engine, sample_span):
        results = await engine.verify([sample_span])
        vr = results[0]
        assert vr.status == VerificationStatus.VERIFIED
        assert vr.verified is True

    @pytest.mark.asyncio
    async def test_processing_time_ms_is_set(self, engine, sample_span):
        results = await engine.verify([sample_span])
        assert results[0].processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_evidence_summary_populated_for_verified(self, engine, sample_span):
        results = await engine.verify([sample_span])
        summary = results[0].evidence_summary
        assert summary is not None
        assert "well-supported" in summary

    @pytest.mark.asyncio
    async def test_confidence_computed_correctly(self, engine, sample_span):
        results = await engine.verify([sample_span])
        vr = results[0]
        assert 0.0 <= vr.confidence <= 1.0
        assert vr.confidence > 0

    @pytest.mark.asyncio
    async def test_verify_with_knowledge_service(
        self, engine_with_kb, sample_span
    ):
        results = await engine_with_kb.verify([sample_span])
        assert len(results) == 1
        vr = results[0]
        assert len(vr.supporting_sources) > 0
        for src in vr.supporting_sources:
            assert src.source_id.startswith("kb_")

    @pytest.mark.asyncio
    async def test_knowledge_service_search_error_falls_back_to_mock(self, engine, sample_span):
        class FailingKnowledgeService:
            async def search(self, claim):
                raise ValueError("Search failed")
        engine._knowledge_service = FailingKnowledgeService()
        results = await engine.verify([sample_span])
        assert len(results) == 1
        assert results[0].supporting_sources[0].source_id == "src_mock_1"

    @pytest.mark.asyncio
    async def test_verification_details_populated(self, engine, sample_span):
        results = await engine.verify([sample_span])
        assert results[0].verification_details is not None
        assert "supporting" in results[0].verification_details

    @pytest.mark.asyncio
    async def test_verify_with_state(self, engine, sample_span):
        state = EvidenceState(
            config={"threshold": 0.5},
            metadata={"pipeline": "test"},
        )
        results = await engine.verify([sample_span], state=state)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_multiple_spans_preserve_order(self, engine, sample_spans):
        results = await engine.verify(sample_spans)
        for i, r in enumerate(results):
            assert r.span == sample_spans[i]

    @pytest.mark.asyncio
    async def test_all_spans_have_processing_time(self, engine, sample_spans):
        results = await engine.verify(sample_spans)
        for r in results:
            assert r.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_verified_span_has_supporting_sources(self, engine, sample_span):
        results = await engine.verify([sample_span])
        vr = results[0]
        assert len(vr.supporting_sources) > 0
        assert len(vr.contradicting_sources) == 0
