import pytest

from app.ai.clinical_safety.services.unsupported import DefaultUnsupportedClaimDetector
from app.ai.clinical_safety.schemas import SupportLevel


class TestDefaultUnsupportedClaimDetector:

    @pytest.mark.asyncio
    async def test_empty_claims_returns_empty_report(self):
        detector = DefaultUnsupportedClaimDetector()
        report = await detector.detect([], None)

        assert report.total_claims == 0
        assert report.supported_count == 0
        assert report.unsupported_count == 0
        assert report.contradictory_count == 0
        assert report.coverage_score == 0.0
        assert report.passed is True
        assert report.summary == "No claims to analyze."

    @pytest.mark.asyncio
    async def test_claim_with_matching_evidence_fully_supported(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {"Aspirin": "treats headaches", "effective": "yes"}
        report = await detector.detect(["Aspirin is effective."], evidence)

        assert report.total_claims == 1
        assert report.supported_count == 1
        assert report.claims[0].support_level == SupportLevel.FULLY_SUPPORTED

    @pytest.mark.asyncio
    async def test_claim_with_partial_evidence_partially_supported(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {"Aspirin": "treats headaches"}
        report = await detector.detect(["Aspirin cures cancer."], evidence)

        assert report.total_claims == 1
        assert report.claims[0].support_level == SupportLevel.PARTIALLY_SUPPORTED
        assert report.supported_count == 0

    @pytest.mark.asyncio
    async def test_claim_with_no_evidence_unsupported(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {"Aspirin": "treats headaches"}
        report = await detector.detect(["Unicorns cure diabetes."], evidence)

        assert report.total_claims == 1
        assert report.unsupported_count == 1
        assert report.claims[0].support_level == SupportLevel.UNSUPPORTED
        assert report.coverage_score == 0.0

    @pytest.mark.asyncio
    async def test_claim_with_contradicting_evidence_contradictory(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {"Aspirin": "contradict"}
        report = await detector.detect(["Aspirin cures cancer."], evidence)

        assert report.total_claims == 1
        assert report.contradictory_count == 1
        assert report.claims[0].support_level == SupportLevel.CONTRADICTORY
        assert report.claims[0].confidence == 0.85

    @pytest.mark.asyncio
    async def test_coverage_score_calculation(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {"aspirin": "treats", "effective": "yes", "metformin": "diabetes", "controls": "yes", "sugar": "yes"}
        claims = [
            "Aspirin is effective.",
            "Metformin controls sugar.",
            "Unicorns cure disease.",
        ]
        report = await detector.detect(claims, evidence)

        assert report.total_claims == 3
        assert report.supported_count == 2
        assert report.unsupported_count == 1
        assert report.coverage_score == 2.0 / 3.0

    @pytest.mark.asyncio
    async def test_passed_flag_based_on_unsupported_rate(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {"aspirin": "treats", "effective": "yes"}
        report = await detector.detect(
            ["Aspirin is effective.", "Unicorns cure disease."],
            evidence,
        )

        assert report.total_claims == 2
        assert report.supported_count == 1
        assert report.coverage_score == 0.5
        assert report.passed is True

    @pytest.mark.asyncio
    async def test_passed_false_when_coverage_below_threshold(self):
        detector = DefaultUnsupportedClaimDetector()
        report = await detector.detect(
            ["Unicorns cure disease.", "Magic heals wounds.", "Fairies prevent illness."],
            {"Aspirin": "treats"},
        )

        assert report.total_claims == 3
        assert report.supported_count == 0
        assert report.coverage_score == 0.0
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_mixed_support_levels(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {
            "Aspirin": "contradict", "metformin": "treats", "treats": "yes",
            "diabetes": "yes", "exercise": "beneficial", "improves": "yes",
            "health": "yes",
        }
        claims = [
            "Aspirin cures everything.",
            "Metformin treats diabetes.",
            "Exercise improves health.",
            "Magic pills cure all disease.",
        ]
        report = await detector.detect(claims, evidence)

        support_levels = {c.claim: c.support_level for c in report.claims}
        assert support_levels["Aspirin cures everything."] == SupportLevel.CONTRADICTORY
        assert support_levels["Metformin treats diabetes."] == SupportLevel.FULLY_SUPPORTED
        assert support_levels["Exercise improves health."] == SupportLevel.FULLY_SUPPORTED
        assert support_levels["Magic pills cure all disease."] == SupportLevel.UNSUPPORTED

    @pytest.mark.asyncio
    async def test_evidence_with_multiple_keywords(self):
        detector = DefaultUnsupportedClaimDetector()
        evidence = {
            "Aspirin treats headaches effectively": "true",
            "Aspirin prevents heart attacks": "true",
        }
        report = await detector.detect(["Aspirin treats headaches."], evidence)

        assert report.total_claims == 1
        assert report.claims[0].support_level == SupportLevel.FULLY_SUPPORTED

    @pytest.mark.asyncio
    async def test_none_evidence_treats_all_as_unsupported(self):
        detector = DefaultUnsupportedClaimDetector()
        report = await detector.detect(["Aspirin is effective.", "Metformin controls sugar."], None)

        assert report.total_claims == 2
        assert report.unsupported_count == 2
        assert report.supported_count == 0
        assert report.coverage_score == 0.0
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_empty_evidence_dict_treats_all_as_unsupported(self):
        detector = DefaultUnsupportedClaimDetector()
        report = await detector.detect(["Aspirin is effective."], {})

        assert report.total_claims == 1
        assert report.unsupported_count == 1
        assert report.supported_count == 0
        assert report.coverage_score == 0.0
        assert report.passed is False
