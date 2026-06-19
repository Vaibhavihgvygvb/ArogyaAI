import pytest

from app.ai.clinical_safety.services.hallucination import DefaultHallucinationDetector
from app.ai.clinical_safety.schemas import HallucinationType


class TestDefaultHallucinationDetector:

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_report_with_passed_true(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", [], None)

        assert report.passed is True
        assert report.total_claims == 0
        assert report.hallucinated_count == 0
        assert report.hallucination_rate == 0.0
        assert len(report.results) == 0
        assert report.summary == "No claims to analyze."

    @pytest.mark.asyncio
    async def test_known_medication_aspirin_not_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["Aspirin is effective for pain relief."], None)

        assert report.passed is True
        assert report.total_claims == 1
        assert report.hallucinated_count == 0

    @pytest.mark.asyncio
    async def test_unknown_fabricated_medication_xylomycin_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["Xylomycin is a new antibiotic treatment."], None)

        assert report.total_claims == 1
        assert report.hallucinated_count == 1
        assert report.results[0].hallucination_type == HallucinationType.FABRICATED_MEDICATION
        assert report.results[0].confidence >= 0.8
        assert "xylomycin" in report.results[0].evidence_snippet.lower()

    @pytest.mark.asyncio
    async def test_known_disease_diabetes_not_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["Diabetes requires careful blood sugar monitoring."], None)

        assert report.passed is True
        assert report.total_claims == 1
        assert report.hallucinated_count == 0

    @pytest.mark.asyncio
    async def test_unknown_fabricated_disease_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["The patient has been diagnosed with cardiomyelosis."], None)

        assert report.total_claims == 1
        assert report.results[0].hallucination_type == HallucinationType.UNSUPPORTED_CLAIM

    @pytest.mark.asyncio
    async def test_citation_pattern_without_evidence_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["Studies show improved outcomes [1]."], None)

        assert report.total_claims == 1
        assert report.hallucinated_count == 1
        assert report.results[0].hallucination_type == HallucinationType.FABRICATED_CITATION
        assert report.results[0].confidence == 0.8

    @pytest.mark.asyncio
    async def test_citation_with_evidence_does_not_flag(self):
        detector = DefaultHallucinationDetector()
        evidence = {"[1]": "Improved outcomes in clinical trials"}
        report = await detector.detect("", ["Studies show improved outcomes [1]."], evidence)

        assert report.total_claims == 1

    @pytest.mark.asyncio
    async def test_statistic_pattern_without_evidence_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["75% of patients respond well to treatment."], None)

        assert report.total_claims == 1
        assert report.hallucinated_count == 1
        assert report.results[0].hallucination_type == HallucinationType.FABRICATED_STATISTIC
        assert report.results[0].confidence == 0.6

    @pytest.mark.asyncio
    async def test_guideline_pattern_without_evidence_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["The guideline recommends annual screening."], None)

        assert report.total_claims == 1
        assert report.hallucinated_count == 1
        assert report.results[0].hallucination_type == HallucinationType.FABRICATED_GUIDELINE
        assert report.results[0].confidence == 0.7

    @pytest.mark.asyncio
    async def test_recommendation_without_evidence_flagged(self):
        detector = DefaultHallucinationDetector()
        report = await detector.detect("", ["Patients should take a daily walk for health."], None)

        assert report.total_claims == 1
        assert report.hallucinated_count == 1
        assert report.results[0].hallucination_type == HallucinationType.FABRICATED_RECOMMENDATION
        assert report.results[0].confidence == 0.5

    @pytest.mark.asyncio
    async def test_hallucination_rate_correctly_calculated(self):
        detector = DefaultHallucinationDetector()
        claims = [
            "Aspirin is safe.",                          # known medication → not flagged
            "Xylomycin is a new treatment.",             # unknown medication → flagged
            "75% of patients benefit from therapy.",     # statistic → flagged
        ]
        report = await detector.detect("", claims, None)

        assert report.total_claims == 3
        assert report.hallucinated_count == 2
        assert report.hallucination_rate == 2.0 / 3.0

    @pytest.mark.asyncio
    async def test_passed_flag_depends_on_hallucination_rate_threshold(self):
        detector = DefaultHallucinationDetector()
        claims = [
            "Xylomycin cures infections.",
            "85% of cases resolve with this drug.",
            "Guidelines recommend this approach.",
        ]
        report = await detector.detect("", claims, None)

        assert report.total_claims == 3
        assert report.hallucinated_count == 3
        assert report.hallucination_rate == 1.0
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_passed_true_when_rate_below_threshold(self):
        detector = DefaultHallucinationDetector()
        claims = [
            "Aspirin is safe.",
            "Metformin controls blood sugar.",
            "Xylomycin is a new treatment.",
        ]
        report = await detector.detect("", claims, None)

        assert report.total_claims == 3
        assert report.hallucinated_count == 1
        assert report.hallucination_rate == 1.0 / 3.0
        assert report.passed is True

    @pytest.mark.asyncio
    async def test_evidence_dict_reduces_hallucination_flags(self):
        detector = DefaultHallucinationDetector()
        evidence = {"Aspirin is effective for treating headaches": "true"}
        report = await detector.detect(
            "",
            ["Aspirin is effective for treating headaches."],
            evidence,
        )

        assert report.hallucinated_count == 0
        assert report.passed is True
        assert report.hallucination_rate == 0.0

    @pytest.mark.asyncio
    async def test_multiple_hallucinations_in_one_text(self):
        detector = DefaultHallucinationDetector()
        claims = [
            "Xylomycin is a breakthrough treatment.",
            "Studies show 90% efficacy in trials.",
            "The protocol recommends this drug.",
        ]
        report = await detector.detect("", claims, None)

        assert report.total_claims == 3
        assert report.hallucinated_count == 3

    @pytest.mark.asyncio
    async def test_custom_claims_list_processing(self):
        detector = DefaultHallucinationDetector()
        custom_claims = ["Aspirin is over-the-counter."]
        report = await detector.detect("Some unrelated text.", custom_claims, None)

        assert report.total_claims == 1
        assert report.hallucinated_count == 0
        assert report.results[0].claim == "Aspirin is over-the-counter."

    @pytest.mark.asyncio
    async def test_all_hallucination_types_can_be_detected(self):
        detector = DefaultHallucinationDetector()
        claims = [
            "Xylomycin is effective for infections.",        # FABRICATED_MEDICATION
            "Studies confirm results [2].",                  # FABRICATED_CITATION
            "The protocol recommends this approach.",        # FABRICATED_GUIDELINE
            "60% of patients experience relief.",            # FABRICATED_STATISTIC
            "Patients ought to rest frequently.",            # FABRICATED_RECOMMENDATION
            "Some unsupported medical claim here.",          # UNSUPPORTED_CLAIM
        ]
        report = await detector.detect("", claims, None)

        assert report.total_claims == 6
        detected_types = {r.hallucination_type for r in report.results}
        assert HallucinationType.FABRICATED_MEDICATION in detected_types
        assert HallucinationType.FABRICATED_CITATION in detected_types
        assert HallucinationType.FABRICATED_GUIDELINE in detected_types
        assert HallucinationType.FABRICATED_STATISTIC in detected_types
        assert HallucinationType.FABRICATED_RECOMMENDATION in detected_types
        assert HallucinationType.UNSUPPORTED_CLAIM in detected_types
