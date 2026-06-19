import pytest

from app.ai.evidence.engines.citation import (
    CitationFormatterEngine,
    CitationGeneratorEngine,
)
from app.ai.evidence.schemas import (
    Citation,
    CitationGroup,
    CitationStyle,
    EvidenceSpan,
    EvidenceType,
    FormattedCitation,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)


@pytest.fixture
def generator():
    return CitationGeneratorEngine()


@pytest.fixture
def formatter():
    return CitationFormatterEngine()


@pytest.fixture
def sample_source():
    return VerifiedSource(
        source_id="src_1",
        title="Hypertension Treatment Guidelines",
        authors=["Alice Smith", "Bob Jones"],
        publication_date="2024-06-15",
        journal="Journal of Cardiology",
        doi="10.1234/jcard.2024.001",
        evidence_type=EvidenceType.GUIDELINE,
        authority_score=0.85,
        relevance_score=0.9,
        recency_score=0.95,
        quality_score=0.88,
        support_direction="supporting",
        excerpt="Guidelines recommend treating hypertension...",
    )


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
def verification_result(sample_span, sample_source):
    return VerificationResult(
        span=sample_span,
        verified=True,
        status=VerificationStatus.VERIFIED,
        supporting_sources=[sample_source],
        contradicting_sources=[],
        confidence=0.85,
        evidence_summary="Claim is well-supported by 1 source(s).",
        verification_details="Verified 1 supporting, 0 contradicting sources",
        processing_time_ms=150.0,
    )


@pytest.fixture
def multi_source_verification_result(sample_span, sample_source):
    source2 = VerifiedSource(
        source_id="src_2",
        title="Blood Pressure Meta-Analysis",
        authors=["Carol Davis"],
        publication_date="2023-11-01",
        journal="Lancet",
        evidence_type=EvidenceType.META_ANALYSIS,
        authority_score=0.9,
        relevance_score=0.85,
        recency_score=0.7,
        quality_score=0.92,
        support_direction="supporting",
        excerpt="Meta-analysis confirms hypertension prevalence...",
    )
    return VerificationResult(
        span=sample_span,
        verified=True,
        status=VerificationStatus.VERIFIED,
        supporting_sources=[sample_source, source2],
        contradicting_sources=[],
        confidence=0.88,
        evidence_summary="Claim is well-supported by 2 source(s).",
        processing_time_ms=200.0,
    )


class TestCitationGeneratorEngine:
    @pytest.mark.asyncio
    async def test_generate_empty_list(self, generator):
        result = await generator.generate([])
        assert result == []

    @pytest.mark.asyncio
    async def test_generate_with_verification_results(
        self, generator, verification_result
    ):
        results = await generator.generate([verification_result])
        assert len(results) == 1
        assert isinstance(results[0], Citation)
        assert results[0].evidence_text == verification_result.span.claim

    @pytest.mark.asyncio
    async def test_citations_have_unique_ids(
        self, generator, multi_source_verification_result
    ):
        results = await generator.generate([multi_source_verification_result])
        ids = [c.citation_id for c in results]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_citation_confidence_matches_verification(
        self, generator, verification_result
    ):
        results = await generator.generate([verification_result])
        assert results[0].confidence == verification_result.confidence

    @pytest.mark.asyncio
    async def test_generate_multiple_verification_results(
        self, generator, verification_result, sample_source
    ):
        span2 = EvidenceSpan(
            text="Patient was prescribed aspirin",
            claim="Aspirin 81mg daily prescribed",
        )
        vr2 = VerificationResult(
            span=span2,
            verified=True,
            status=VerificationStatus.VERIFIED,
            supporting_sources=[sample_source],
            contradicting_sources=[],
            confidence=0.75,
        )
        results = await generator.generate([verification_result, vr2])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_group_by_claim_empty(self, generator):
        groups = await generator.group_by_claim([])
        assert groups == []

    @pytest.mark.asyncio
    async def test_group_by_claim_groups_correctly(
        self, generator, verification_result, sample_source
    ):
        source2 = VerifiedSource(
            source_id="src_2",
            title="Another Source",
            authors=["Carol Davis"],
            evidence_type=EvidenceType.GUIDELINE,
            authority_score=0.7,
            relevance_score=0.8,
            recency_score=0.7,
            quality_score=0.75,
            support_direction="supporting",
        )
        vr2 = VerificationResult(
            span=EvidenceSpan(text="x", claim="Patient has hypertension"),
            verified=True,
            status=VerificationStatus.VERIFIED,
            supporting_sources=[source2],
            contradicting_sources=[],
            confidence=0.8,
        )
        all_citations = await generator.generate(
            [verification_result, vr2]
        )
        groups = await generator.group_by_claim(all_citations)
        assert len(groups) == 1
        assert groups[0].claim == "Patient has hypertension"
        assert groups[0].total_citations == 2

    @pytest.mark.asyncio
    async def test_group_by_claim_multiple_claims(
        self, generator, verification_result, sample_source
    ):
        span2 = EvidenceSpan(
            text="Patient was prescribed aspirin",
            claim="Aspirin 81mg daily prescribed",
        )
        vr2 = VerificationResult(
            span=span2,
            verified=True,
            status=VerificationStatus.VERIFIED,
            supporting_sources=[sample_source],
            contradicting_sources=[],
            confidence=0.75,
        )
        all_citations = await generator.generate(
            [verification_result, vr2]
        )
        groups = await generator.group_by_claim(all_citations)
        assert len(groups) == 2
        claims = {g.claim for g in groups}
        assert "Patient has hypertension" in claims
        assert "Aspirin 81mg daily prescribed" in claims

    @pytest.mark.asyncio
    async def test_inline_ref_populated(
        self, generator, verification_result
    ):
        results = await generator.generate([verification_result])
        assert results[0].inline_ref is not None
        assert "confidence" in results[0].inline_ref


class TestCitationFormatterEngine:
    @pytest.mark.asyncio
    async def test_format_empty_citations(self, formatter):
        result = await formatter.format([])
        assert isinstance(result, FormattedCitation)
        assert result.text == ""
        assert result.markdown == ""

    @pytest.mark.asyncio
    async def test_format_produces_text_and_markdown(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations)
        assert result.text != ""
        assert result.markdown != ""

    @pytest.mark.asyncio
    async def test_format_ama_style(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations, style=CitationStyle.AMA)
        assert result.style == CitationStyle.AMA
        assert len(result.reference_list) == 1
        assert result.reference_list[0].startswith("1.")

    @pytest.mark.asyncio
    async def test_format_apa_style(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations, style=CitationStyle.APA)
        assert result.style == CitationStyle.APA
        assert "(2024)" in result.reference_list[0]

    @pytest.mark.asyncio
    async def test_format_vancouver_style(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations, style=CitationStyle.VANCOUVER)
        assert result.style == CitationStyle.VANCOUVER

    @pytest.mark.asyncio
    async def test_format_ieee_style(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations, style=CitationStyle.IEEE)
        assert result.style == CitationStyle.IEEE
        assert result.reference_list[0].startswith("[1]")

    @pytest.mark.asyncio
    async def test_format_mla_style(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations, style=CitationStyle.MLA)
        assert result.style == CitationStyle.MLA

    @pytest.mark.asyncio
    async def test_format_chicago_style(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations, style=CitationStyle.CHICAGO)
        assert result.style == CitationStyle.CHICAGO

    @pytest.mark.asyncio
    async def test_supported_styles_returns_all_styles(self, formatter):
        styles = await formatter.supported_styles()
        assert len(styles) == 6
        assert CitationStyle.AMA in styles
        assert CitationStyle.APA in styles
        assert CitationStyle.VANCOUVER in styles
        assert CitationStyle.IEEE in styles
        assert CitationStyle.MLA in styles
        assert CitationStyle.CHICAGO in styles

    @pytest.mark.asyncio
    async def test_citation_number_assigned_during_format(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        assert all(c.citation_number == 0 for c in citations)
        result = await formatter.format(citations)
        for c in result.citations:
            assert c.citation_number > 0

    @pytest.mark.asyncio
    async def test_format_with_multiple_citations(
        self, formatter, multi_source_verification_result, generator
    ):
        citations = await generator.generate([multi_source_verification_result])
        result = await formatter.format(citations)
        assert len(result.reference_list) == 2
        assert result.reference_list[0].startswith("1.")
        assert result.reference_list[1].startswith("2.")

    @pytest.mark.asyncio
    async def test_markdown_contains_references_section(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations)
        assert "## References" in result.markdown
        assert "[^1]" in result.markdown

    @pytest.mark.asyncio
    async def test_text_uses_bracket_format(
        self, formatter, verification_result, generator
    ):
        citations = await generator.generate([verification_result])
        result = await formatter.format(citations)
        assert result.text.startswith("[1]")
