from datetime import datetime
from app.ai.evidence.schemas import (
    VerificationStatus,
    EvidenceType,
    CitationStyle,
    ConflictType,
    ProvenanceAction,
    EvidenceSpan,
    VerifiedSource,
    VerificationResult,
    Citation,
    CitationGroup,
    FormattedCitation,
    CoverageGap,
    CoverageResult,
    ConflictResult,
    ConfidenceBreakdown,
    ConfidenceResult,
    ProvenanceEntry,
    ProvenanceGraph,
    ExplanationComponent,
    ExplanationResult,
    EvidenceState,
    PipelineResult,
    ServiceResult,
)


class TestEnums:
    def test_verification_status_values(self):
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.PARTIALLY_VERIFIED.value == "partially_verified"
        assert VerificationStatus.UNVERIFIED.value == "unverified"
        assert VerificationStatus.CONTRADICTED.value == "contradicted"

    def test_verification_status_members(self):
        assert len(VerificationStatus) == 4

    def test_evidence_type_values(self):
        assert EvidenceType.DIRECT.value == "direct"
        assert EvidenceType.STATISTICAL.value == "statistical"
        assert EvidenceType.MECHANISTIC.value == "mechanistic"
        assert EvidenceType.EXPERT_OPINION.value == "expert_opinion"
        assert EvidenceType.GUIDELINE.value == "guideline"
        assert EvidenceType.META_ANALYSIS.value == "meta_analysis"
        assert EvidenceType.SYSTEMATIC_REVIEW.value == "systematic_review"
        assert EvidenceType.CASE_STUDY.value == "case_study"
        assert EvidenceType.UNKNOWN.value == "unknown"

    def test_evidence_type_members(self):
        assert len(EvidenceType) == 9

    def test_citation_style_values(self):
        assert CitationStyle.AMA.value == "ama"
        assert CitationStyle.APA.value == "apa"
        assert CitationStyle.VANCOUVER.value == "vancouver"
        assert CitationStyle.IEEE.value == "ieee"
        assert CitationStyle.MLA.value == "mla"
        assert CitationStyle.CHICAGO.value == "chicago"

    def test_citation_style_members(self):
        assert len(CitationStyle) == 6

    def test_conflict_type_values(self):
        assert ConflictType.DIRECT.value == "direct"
        assert ConflictType.CONTRADICTORY.value == "contradictory"
        assert ConflictType.DIRECTIONAL.value == "directional"
        assert ConflictType.DOSAGE.value == "dosage"
        assert ConflictType.TIMING.value == "timing"
        assert ConflictType.CONTRAINDICATION.value == "contraindication"

    def test_conflict_type_members(self):
        assert len(ConflictType) == 6

    def test_provenance_action_values(self):
        assert ProvenanceAction.VERIFICATION.value == "verification"
        assert ProvenanceAction.CITATION.value == "citation"
        assert ProvenanceAction.COVERAGE.value == "coverage"
        assert ProvenanceAction.CONFLICT.value == "conflict"
        assert ProvenanceAction.CONFIDENCE.value == "confidence"
        assert ProvenanceAction.RANKING.value == "ranking"
        assert ProvenanceAction.PIPELINE.value == "pipeline"
        assert ProvenanceAction.EXPLANATION.value == "explanation"

    def test_provenance_action_members(self):
        assert len(ProvenanceAction) == 8


class TestEvidenceSpan:
    def test_required_fields(self):
        span = EvidenceSpan(text="some text", claim="a claim")
        assert span.text == "some text"
        assert span.claim == "a claim"

    def test_defaults(self):
        span = EvidenceSpan(text="text", claim="claim")
        assert span.span_start == 0
        assert span.span_end == 0
        assert span.context is None
        assert span.metadata == {}

    def test_with_all_fields(self):
        span = EvidenceSpan(
            text="patient has fever",
            claim="fever present",
            span_start=10,
            span_end=25,
            context="clinical note",
            metadata={"source": "note_1"},
        )
        assert span.span_start == 10
        assert span.span_end == 25
        assert span.context == "clinical note"
        assert span.metadata == {"source": "note_1"}


class TestVerifiedSource:
    def test_minimal(self):
        src = VerifiedSource(source_id="src_1")
        assert src.source_id == "src_1"
        assert src.title is None
        assert src.authors == []
        assert src.evidence_type == EvidenceType.UNKNOWN

    def test_with_all_fields(self):
        src = VerifiedSource(
            source_id="src_2",
            title="A Study",
            authors=["Alice", "Bob"],
            publication_date="2024-01-01",
            journal="Medical Journal",
            url="https://example.com",
            doi="10.1234/abc",
            evidence_type=EvidenceType.META_ANALYSIS,
            authority_score=0.9,
            relevance_score=0.8,
            recency_score=0.7,
            quality_score=0.85,
            support_direction="supports",
            excerpt="This study shows...",
            metadata={"impact_factor": 5.0},
        )
        assert src.title == "A Study"
        assert src.authors == ["Alice", "Bob"]
        assert src.evidence_type == EvidenceType.META_ANALYSIS
        assert src.authority_score == 0.9
        assert src.relevance_score == 0.8
        assert src.recency_score == 0.7
        assert src.quality_score == 0.85
        assert src.support_direction == "supports"
        assert src.excerpt == "This study shows..."
        assert src.metadata == {"impact_factor": 5.0}

    def test_score_bounds(self):
        from pydantic import ValidationError
        import pytest

        with pytest.raises(ValidationError):
            VerifiedSource(source_id="s", authority_score=1.5)
        with pytest.raises(ValidationError):
            VerifiedSource(source_id="s", relevance_score=-0.1)


class TestVerificationResult:
    def test_minimal(self):
        span = EvidenceSpan(text="x", claim="y")
        result = VerificationResult(
            span=span,
            verified=True,
            status=VerificationStatus.VERIFIED,
        )
        assert result.span == span
        assert result.verified is True
        assert result.status == VerificationStatus.VERIFIED

    def test_defaults(self):
        span = EvidenceSpan(text="x", claim="y")
        result = VerificationResult(
            span=span,
            verified=False,
            status=VerificationStatus.UNVERIFIED,
        )
        assert result.supporting_sources == []
        assert result.contradicting_sources == []
        assert result.confidence == 0.0
        assert result.processing_time_ms == 0.0
        assert result.evidence_summary is None
        assert result.verification_details is None

    def test_status_mapping(self):
        span = EvidenceSpan(text="x", claim="y")
        cases = [
            (True, VerificationStatus.VERIFIED),
            (True, VerificationStatus.PARTIALLY_VERIFIED),
            (False, VerificationStatus.UNVERIFIED),
            (False, VerificationStatus.CONTRADICTED),
        ]
        for verified, status in cases:
            result = VerificationResult(span=span, verified=verified, status=status)
            assert result.verified is verified
            assert result.status == status


class TestCitation:
    def test_required_fields(self):
        src = VerifiedSource(source_id="s1")
        c = Citation(citation_id="c1", evidence_text="evidence", source=src)
        assert c.citation_id == "c1"
        assert c.evidence_text == "evidence"
        assert c.source == src

    def test_citation_number_auto_zero(self):
        src = VerifiedSource(source_id="s1")
        c = Citation(citation_id="c1", evidence_text="e", source=src)
        assert c.citation_number == 0

    def test_citation_number_set(self):
        src = VerifiedSource(source_id="s1")
        c = Citation(
            citation_id="c1", evidence_text="e", source=src, citation_number=5
        )
        assert c.citation_number == 5

    def test_defaults(self):
        src = VerifiedSource(source_id="s1")
        c = Citation(citation_id="c1", evidence_text="e", source=src)
        assert c.span_index == 0
        assert c.inline_ref is None
        assert c.confidence == 0.0
        assert c.metadata == {}


class TestCitationGroup:
    def test_minimal(self):
        g = CitationGroup(claim="some claim")
        assert g.claim == "some claim"
        assert g.citations == []
        assert g.total_citations == 0

    def test_with_citations(self):
        src = VerifiedSource(source_id="s1")
        c = Citation(citation_id="c1", evidence_text="e", source=src)
        g = CitationGroup(claim="claim", citations=[c], total_citations=1)
        assert len(g.citations) == 1
        assert g.total_citations == 1


class TestFormattedCitation:
    def test_minimal(self):
        fc = FormattedCitation(style=CitationStyle.AMA, text="[1]", markdown="[1]")
        assert fc.style == CitationStyle.AMA
        assert fc.text == "[1]"
        assert fc.markdown == "[1]"

    def test_defaults(self):
        fc = FormattedCitation(style=CitationStyle.APA, text="t", markdown="m")
        assert fc.bibtex is None
        assert fc.citations == []
        assert fc.reference_list == []

    def test_with_style(self):
        fc = FormattedCitation(
            style=CitationStyle.VANCOUVER,
            text="(1)",
            markdown="(1)",
            bibtex="@article{...}",
        )
        assert fc.style == CitationStyle.VANCOUVER
        assert fc.bibtex == "@article{...}"


class TestCoverageGap:
    def test_minimal(self):
        gap = CoverageGap(claim="c", gap_type="missing")
        assert gap.claim == "c"
        assert gap.gap_type == "missing"
        assert gap.severity == "medium"
        assert gap.description is None
        assert gap.suggested_sources == []


class TestCoverageResult:
    def test_defaults(self):
        cr = CoverageResult()
        assert cr.total_spans == 0
        assert cr.verified_spans == 0
        assert cr.unverified_spans == 0
        assert cr.partially_verified_spans == 0
        assert cr.coverage_score == 0.0
        assert cr.evidence_density == 0.0
        assert cr.gaps == []
        assert cr.recommendations == []

    def test_coverage_score_bounds(self):
        from pydantic import ValidationError
        import pytest

        with pytest.raises(ValidationError):
            CoverageResult(coverage_score=1.5)
        with pytest.raises(ValidationError):
            CoverageResult(coverage_score=-0.1)

    def test_with_values(self):
        gap = CoverageGap(claim="c", gap_type="missing")
        cr = CoverageResult(
            total_spans=10,
            verified_spans=7,
            unverified_spans=2,
            partially_verified_spans=1,
            coverage_score=0.7,
            evidence_density=0.5,
            gaps=[gap],
            recommendations=["add source"],
        )
        assert cr.total_spans == 10
        assert cr.verified_spans == 7
        assert cr.unverified_spans == 2
        assert cr.partially_verified_spans == 1
        assert cr.gaps == [gap]
        assert cr.recommendations == ["add source"]


class TestConflictResult:
    def test_minimal(self):
        cr = ConflictResult(claim="c1", conflict_type=ConflictType.DIRECT)
        assert cr.claim == "c1"
        assert cr.conflict_type == ConflictType.DIRECT

    def test_defaults(self):
        cr = ConflictResult(claim="c1", conflict_type=ConflictType.CONTRADICTORY)
        assert cr.span_index == 0
        assert cr.sources == []
        assert cr.severity == "medium"
        assert cr.description is None
        assert cr.resolution is None

    def test_with_contradictory(self):
        cr = ConflictResult(
            claim="c1",
            conflict_type=ConflictType.CONTRADICTORY,
            severity="high",
            description="studies disagree",
            resolution="more data needed",
        )
        assert cr.conflict_type == ConflictType.CONTRADICTORY
        assert cr.severity == "high"
        assert cr.resolution == "more data needed"


class TestConfidenceBreakdown:
    def test_minimal(self):
        cb = ConfidenceBreakdown(category="source_quality")
        assert cb.category == "source_quality"
        assert cb.score == 0.0
        assert cb.weight == 0.0
        assert cb.details is None

    def test_score_bounds(self):
        from pydantic import ValidationError
        import pytest

        with pytest.raises(ValidationError):
            ConfidenceBreakdown(category="c", score=1.2)


class TestConfidenceResult:
    def test_defaults(self):
        cr = ConfidenceResult()
        assert cr.overall == 0.0
        assert cr.verification_confidence == 0.0
        assert cr.citation_confidence == 0.0
        assert cr.coverage_confidence == 0.0
        assert cr.source_quality_confidence == 0.0
        assert cr.suitable_for_ai is False
        assert cr.breakdown == []
        assert cr.warnings == []

    def test_with_breakdown(self):
        cb = ConfidenceBreakdown(category="source_quality", score=0.8, weight=0.5)
        cr = ConfidenceResult(
            overall=0.85,
            verification_confidence=0.9,
            citation_confidence=0.8,
            coverage_confidence=0.7,
            source_quality_confidence=0.75,
            suitable_for_ai=True,
            breakdown=[cb],
            warnings=["low sample size"],
        )
        assert cr.overall == 0.85
        assert cr.verification_confidence == 0.9
        assert cr.suitable_for_ai is True
        assert len(cr.breakdown) == 1
        assert cr.warnings == ["low sample size"]


class TestProvenanceEntry:
    def test_minimal(self):
        entry = ProvenanceEntry(
            action=ProvenanceAction.VERIFICATION, engine_name="verifier_v1"
        )
        assert entry.action == ProvenanceAction.VERIFICATION
        assert entry.engine_name == "verifier_v1"

    def test_timestamp_auto_generated(self):
        before = datetime.utcnow()
        entry = ProvenanceEntry(
            action=ProvenanceAction.CITATION, engine_name="cite_engine"
        )
        after = datetime.utcnow()
        assert before <= entry.timestamp <= after

    def test_defaults(self):
        entry = ProvenanceEntry(
            action=ProvenanceAction.CONFIDENCE, engine_name="confidence_v1"
        )
        assert entry.input_summary is None
        assert entry.output_summary is None
        assert entry.processing_time_ms == 0.0
        assert entry.confidence == 0.0
        assert entry.metadata == {}


class TestProvenanceGraph:
    def test_defaults(self):
        pg = ProvenanceGraph()
        assert pg.entries == []
        assert pg.total_time_ms == 0.0
        assert pg.engine_count == 0

    def test_with_entries(self):
        entry = ProvenanceEntry(
            action=ProvenanceAction.PIPELINE, engine_name="pipeline"
        )
        pg = ProvenanceGraph(entries=[entry], total_time_ms=150.0, engine_count=1)
        assert len(pg.entries) == 1
        assert pg.total_time_ms == 150.0
        assert pg.engine_count == 1


class TestExplanationComponent:
    def test_minimal(self):
        ec = ExplanationComponent(component="verification", detail="checked sources")
        assert ec.component == "verification"
        assert ec.detail == "checked sources"
        assert ec.score == 0.0

    def test_with_score(self):
        ec = ExplanationComponent(
            component="confidence", detail="high confidence", score=0.95
        )
        assert ec.score == 0.95


class TestExplanationResult:
    def test_defaults(self):
        er = ExplanationResult()
        assert er.summary is None
        assert er.components == []
        assert er.narrative is None
        assert er.recommendations == []
        assert er.metadata == {}

    def test_with_components(self):
        ec = ExplanationComponent(component="v", detail="d")
        er = ExplanationResult(
            summary="explanation",
            components=[ec],
            narrative="detailed narrative",
            verification_summary="verified 3 of 5",
            citation_summary="cited 2 sources",
            coverage_summary="95% coverage",
            conflict_summary="no conflicts",
            confidence_summary="high",
            recommendations=["add more sources"],
            metadata={"version": "1.0"},
        )
        assert er.summary == "explanation"
        assert len(er.components) == 1
        assert er.narrative == "detailed narrative"
        assert er.recommendations == ["add more sources"]
        assert er.metadata == {"version": "1.0"}


class TestEvidenceState:
    def test_defaults(self):
        state = EvidenceState()
        assert state.spans == []
        assert state.verification_results == []
        assert state.citations == []
        assert state.citation_groups == []
        assert state.formatted_citation is None
        assert state.coverage is None
        assert state.ranked_sources == []
        assert state.conflicts == []
        assert state.confidence is None
        assert state.provenance == []
        assert state.explanation is None
        assert state.config == {}
        assert state.metadata == {}

    def test_with_all_sub_objects(self):
        span = EvidenceSpan(text="t", claim="c")
        src = VerifiedSource(source_id="s1")
        vr = VerificationResult(
            span=span, verified=True, status=VerificationStatus.VERIFIED
        )
        citation = Citation(citation_id="c1", evidence_text="e", source=src)
        cg = CitationGroup(claim="c", citations=[citation], total_citations=1)
        fc = FormattedCitation(
            style=CitationStyle.AMA, text="[1]", markdown="[1]"
        )
        cov = CoverageResult(
            total_spans=1, verified_spans=1, coverage_score=1.0, evidence_density=1.0
        )
        conflict = ConflictResult(claim="c", conflict_type=ConflictType.DIRECT)
        cb = ConfidenceBreakdown(category="c", score=0.5, weight=0.5)
        conf = ConfidenceResult(
            overall=0.5,
            verification_confidence=0.5,
            citation_confidence=0.5,
            coverage_confidence=0.5,
            source_quality_confidence=0.5,
            breakdown=[cb],
        )
        prov = ProvenanceEntry(
            action=ProvenanceAction.VERIFICATION, engine_name="v1"
        )
        expl = ExplanationResult(summary="done")
        state = EvidenceState(
            spans=[span],
            verification_results=[vr],
            citations=[citation],
            citation_groups=[cg],
            formatted_citation=fc,
            coverage=cov,
            ranked_sources=[src],
            conflicts=[conflict],
            confidence=conf,
            provenance=[prov],
            explanation=expl,
            config={"threshold": 0.5},
            metadata={"pipeline": "v2"},
        )
        assert state.spans == [span]
        assert state.verification_results == [vr]
        assert state.citations == [citation]
        assert state.citation_groups == [cg]
        assert state.formatted_citation == fc
        assert state.coverage == cov
        assert state.ranked_sources == [src]
        assert state.conflicts == [conflict]
        assert state.confidence == conf
        assert state.provenance == [prov]
        assert state.explanation == expl
        assert state.config == {"threshold": 0.5}
        assert state.metadata == {"pipeline": "v2"}


class TestPipelineResult:
    def test_minimal(self):
        state = EvidenceState()
        pr = PipelineResult(state=state)
        assert pr.state == state
        assert pr.pipeline_name == "default"
        assert pr.total_processing_time_ms == 0.0
        assert pr.success is True

    def test_defaults(self):
        state = EvidenceState()
        pr = PipelineResult(state=state)
        assert pr.steps_completed == []
        assert pr.steps_skipped == []
        assert pr.errors == []

    def test_with_steps(self):
        state = EvidenceState()
        pr = PipelineResult(
            state=state,
            pipeline_name="evidence_pipeline",
            total_processing_time_ms=250.0,
            steps_completed=["verify", "cite"],
            steps_skipped=["rank"],
            errors=["timeout on re-rank"],
            success=False,
        )
        assert pr.pipeline_name == "evidence_pipeline"
        assert pr.total_processing_time_ms == 250.0
        assert pr.steps_completed == ["verify", "cite"]
        assert pr.steps_skipped == ["rank"]
        assert pr.errors == ["timeout on re-rank"]
        assert pr.success is False


class TestServiceResult:
    def test_defaults(self):
        sr = ServiceResult()
        assert sr.passed is False
        assert sr.pipeline_result is None
        assert sr.summary is None
        assert sr.warnings == []
        assert sr.errors == []
        assert sr.processing_time_ms == 0.0

    def test_with_passed_summary(self):
        state = EvidenceState()
        pr = PipelineResult(state=state, success=True)
        sr = ServiceResult(
            passed=True,
            pipeline_result=pr,
            summary="all evidence verified",
            warnings=["low confidence on one span"],
            errors=[],
            processing_time_ms=300.0,
        )
        assert sr.passed is True
        assert sr.pipeline_result == pr
        assert sr.summary == "all evidence verified"
        assert sr.warnings == ["low confidence on one span"]
        assert sr.processing_time_ms == 300.0


class TestDefaultFactories:
    def test_evidence_span_metadata_factory(self):
        s = EvidenceSpan(text="t", claim="c")
        assert s.metadata == {}
        s.metadata["key"] = "val"
        assert s.metadata == {"key": "val"}

    def test_verified_source_authors_factory(self):
        s = VerifiedSource(source_id="s1")
        assert s.authors == []
        s.authors.append("Alice")
        assert s.authors == ["Alice"]

    def test_verification_result_sources_factory(self):
        span = EvidenceSpan(text="t", claim="c")
        vr = VerificationResult(
            span=span, verified=True, status=VerificationStatus.VERIFIED
        )
        assert vr.supporting_sources == []
        assert vr.contradicting_sources == []

    def test_citation_metadata_factory(self):
        src = VerifiedSource(source_id="s1")
        c = Citation(citation_id="c1", evidence_text="e", source=src)
        assert c.metadata == {}

    def test_citation_group_citations_factory(self):
        g = CitationGroup(claim="c")
        assert g.citations == []

    def test_formatted_citation_citations_factory(self):
        fc = FormattedCitation(style=CitationStyle.AMA, text="t", markdown="m")
        assert fc.citations == []

    def test_coverage_gap_suggested_sources_factory(self):
        gap = CoverageGap(claim="c", gap_type="g")
        assert gap.suggested_sources == []

    def test_coverage_result_gaps_factory(self):
        cr = CoverageResult()
        assert cr.gaps == []

    def test_conflict_result_sources_factory(self):
        cr = ConflictResult(claim="c", conflict_type=ConflictType.DIRECT)
        assert cr.sources == []

    def test_confidence_breakdown_in_confidence_result(self):
        cr = ConfidenceResult()
        assert cr.breakdown == []
        assert cr.warnings == []

    def test_provenance_entry_metadata_factory(self):
        pe = ProvenanceEntry(
            action=ProvenanceAction.VERIFICATION, engine_name="v1"
        )
        assert pe.metadata == {}

    def test_provenance_graph_entries_factory(self):
        pg = ProvenanceGraph()
        assert pg.entries == []

    def test_explanation_result_components_factory(self):
        er = ExplanationResult()
        assert er.components == []

    def test_evidence_state_spans_factory(self):
        state = EvidenceState()
        assert state.spans == []
        assert state.citations == []
        assert state.provenance == []
        assert state.config == {}

    def test_pipeline_result_steps_factory(self):
        state = EvidenceState()
        pr = PipelineResult(state=state)
        assert pr.steps_completed == []
        assert pr.errors == []

    def test_service_result_warnings_factory(self):
        sr = ServiceResult()
        assert sr.warnings == []
        assert sr.errors == []


class TestModelConfig:
    def test_default_model_config_is_empty(self):
        for model in [
            EvidenceSpan,
            VerifiedSource,
            VerificationResult,
            Citation,
            CitationGroup,
            FormattedCitation,
            CoverageGap,
            CoverageResult,
            ConflictResult,
            ConfidenceBreakdown,
            ConfidenceResult,
            ProvenanceEntry,
            ProvenanceGraph,
            ExplanationComponent,
            ExplanationResult,
            EvidenceState,
            PipelineResult,
            ServiceResult,
        ]:
            assert isinstance(model.model_config, dict)
