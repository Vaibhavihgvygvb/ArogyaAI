import pytest

from app.ai.evidence.config import EvidenceConfig
from app.ai.evidence.exceptions import EvidencePipelineError
from app.ai.evidence.pipeline import EvidencePipeline
from app.ai.evidence.schemas import (
    Citation,
    CitationGroup,
    CitationStyle,
    ConfidenceBreakdown,
    ConfidenceResult,
    ConflictResult,
    CoverageResult,
    EvidenceSpan,
    EvidenceState,
    ExplanationComponent,
    ExplanationResult,
    FormattedCitation,
    PipelineResult,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)


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
                        inline_ref="(90% confidence)",
                        confidence=vr.confidence,
                    )
                )
        return citations

    async def group_by_claim(self, citations):
        return [
            CitationGroup(claim=c.evidence_text, citations=[c], total_citations=1)
            for c in citations
        ]


class MockCitationFormatter:
    async def format(self, citations, style=CitationStyle.AMA):
        return FormattedCitation(
            style=style,
            text="Formatted text",
            markdown="## References\n\n[^1]: ref\n",
            citations=citations,
            reference_list=["1. Author. Title."],
        )


class MockCoverageAnalyzer:
    async def analyze(self, verification_results, state=None):
        return CoverageResult(
            total_spans=len(verification_results),
            verified_spans=len(verification_results),
            unverified_spans=0,
            partially_verified_spans=0,
            coverage_score=1.0,
            evidence_density=1.0,
        )


class MockConflictDetector:
    async def detect(self, verification_results, state=None):
        return []


class MockSourceRanker:
    async def rank(self, sources, state=None):
        return sources


class MockConfidenceCalculator:
    async def calculate(
        self, verification_results, coverage=None, conflicts=None, citations=None, state=None
    ):
        return ConfidenceResult(
            overall=0.85,
            verification_confidence=0.9,
            citation_confidence=0.8,
            coverage_confidence=1.0,
            source_quality_confidence=0.8,
            suitable_for_ai=True,
            breakdown=[
                ConfidenceBreakdown(category="Verification", score=0.9, weight=0.35)
            ],
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
        return ExplanationResult(
            summary="Evidence analysis complete.",
            components=[
                ExplanationComponent(
                    component="Verification",
                    detail="1/1 claims verified",
                    score=1.0,
                )
            ],
        )


class MockBrokenVerifier:
    async def verify(self, spans, state=None):
        raise RuntimeError("Simulated engine failure")


def make_pipeline(**overrides):
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
        config=None,
    )
    defaults.update(overrides)
    return EvidencePipeline(**defaults)


def make_span(claim="Aspirin reduces heart attack risk", text="Aspirin is effective for primary prevention"):
    return EvidenceSpan(text=text, claim=claim, span_start=0, span_end=len(text))


class TestEvidencePipeline:
    @pytest.mark.asyncio
    async def test_run_empty_spans(self):
        pipeline = make_pipeline()
        result = await pipeline.run([])

        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert result.state is not None
        assert result.state.spans == []

    @pytest.mark.asyncio
    async def test_run_single_span_produces_all_steps(self):
        pipeline = make_pipeline()
        span = make_span()
        result = await pipeline.run([span])

        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert len(result.state.verification_results) == 1

    @pytest.mark.asyncio
    async def test_steps_completed_contains_expected_steps(self):
        pipeline = make_pipeline()
        result = await pipeline.run([make_span()])

        expected = ["verification", "citation", "coverage", "conflict_detection", "ranking", "confidence", "explanation"]
        for step in expected:
            assert step in result.steps_completed, f"Missing step: {step}"
        assert result.steps_completed == expected

    @pytest.mark.asyncio
    async def test_result_state_populated(self):
        pipeline = make_pipeline()
        span = make_span()
        result = await pipeline.run([span])

        state = result.state
        assert len(state.verification_results) == 1
        assert len(state.citations) > 0
        assert len(state.citation_groups) > 0
        assert state.formatted_citation is not None
        assert state.coverage is not None
        assert state.confidence is not None
        assert state.explanation is not None
        assert len(state.provenance) > 0

    @pytest.mark.asyncio
    async def test_total_processing_time_ms_gt_zero(self):
        pipeline = make_pipeline()
        result = await pipeline.run([make_span()])

        assert result.total_processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_success_is_true_when_no_errors(self):
        pipeline = make_pipeline()
        result = await pipeline.run([make_span()])

        assert result.success is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_config_override_merges_into_state(self):
        pipeline = make_pipeline()
        config_override = {"custom_key": "custom_value", "threshold": 0.9}
        result = await pipeline.run([make_span()], config_override=config_override)

        assert result.state.config.get("custom_key") == "custom_value"
        assert result.state.config.get("threshold") == 0.9

    @pytest.mark.asyncio
    async def test_default_engine_creation(self):
        pipeline = EvidencePipeline()
        assert pipeline._verifier is not None
        assert pipeline._citation_generator is not None
        assert pipeline._citation_formatter is not None
        assert pipeline._coverage_analyzer is not None
        assert pipeline._source_ranker is not None
        assert pipeline._conflict_detector is not None
        assert pipeline._confidence_calculator is not None
        assert pipeline._provenance_tracker is not None
        assert pipeline._explainability_provider is not None
        assert pipeline._config is not None

    @pytest.mark.asyncio
    async def test_default_config_used_when_none_provided(self):
        pipeline = EvidencePipeline()
        assert isinstance(pipeline._config, EvidenceConfig)

    @pytest.mark.asyncio
    async def test_citation_style_passed_through(self):
        pipeline = make_pipeline()
        style = CitationStyle.APA
        result = await pipeline.run([make_span()], citation_style=style)

        assert result.state.formatted_citation is not None
        assert result.state.formatted_citation.style == style

    @pytest.mark.asyncio
    async def test_error_handling_with_broken_engine(self):
        pipeline = make_pipeline(verifier=MockBrokenVerifier())
        with pytest.raises(EvidencePipelineError):
            await pipeline.run([make_span()])

    @pytest.mark.asyncio
    async def test_provenance_tracks_each_engine(self):
        pipeline = make_pipeline()
        result = await pipeline.run([make_span()])

        actions = [e.action.value for e in result.state.provenance]
        assert "verification" in actions
        assert "citation" in actions
        assert "coverage" in actions
        assert "conflict" in actions
        assert "ranking" in actions
        assert "confidence" in actions
        assert "explanation" in actions

    @pytest.mark.asyncio
    async def test_multiple_spans(self):
        pipeline = make_pipeline()
        spans = [make_span("Claim A"), make_span("Claim B"), make_span("Claim C")]
        result = await pipeline.run(spans)

        assert len(result.state.verification_results) == 3
        assert len(result.state.citations) >= 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_config_override_can_be_empty_dict(self):
        pipeline = make_pipeline()
        result = await pipeline.run([make_span()], config_override={})

        assert result.state.config == {}
