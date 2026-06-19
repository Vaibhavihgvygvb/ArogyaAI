import pytest

from app.ai.clinical_safety.services.emergency import DefaultEmergencyDetector
from app.ai.clinical_safety.schemas import EmergencyType


class TestDefaultEmergencyDetector:

    @pytest.mark.asyncio
    async def test_normal_text_returns_no_emergency(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("The patient is feeling well today.", [])

        assert report.has_emergency is False
        assert len(report.results) == 0
        assert report.max_severity == "none"
        assert report.requires_override is False

    @pytest.mark.asyncio
    async def test_chest_pain_detected(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("The patient reports chest pain.", [])

        assert report.has_emergency is True
        assert len(report.results) == 1
        assert report.results[0].emergency_type == EmergencyType.CHEST_PAIN
        assert report.results[0].is_emergency is True
        assert report.results[0].confidence >= 0.9

    @pytest.mark.asyncio
    async def test_stroke_symptoms_detected(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient presents with sudden numbness on one side.", [])

        assert report.has_emergency is True
        assert report.results[0].emergency_type == EmergencyType.STROKE_SYMPTOMS
        assert report.results[0].is_emergency is True

    @pytest.mark.asyncio
    async def test_severe_bleeding_detected(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("The wound shows severe bleeding.", [])

        assert report.has_emergency is True
        assert report.results[0].emergency_type == EmergencyType.SEVERE_BLEEDING
        assert report.results[0].confidence >= 0.9

    @pytest.mark.asyncio
    async def test_suicidal_ideation_detected(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("The patient mentioned suicide.", [])

        assert report.has_emergency is True
        assert report.results[0].emergency_type == EmergencyType.SUICIDAL_IDEATION
        assert report.results[0].confidence >= 0.9
        assert report.results[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_anaphylaxis_detected(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient is experiencing anaphylaxis after medication.", [])

        assert report.has_emergency is True
        assert report.results[0].emergency_type == EmergencyType.ANAPHYLAXIS
        assert report.results[0].confidence >= 0.9

    @pytest.mark.asyncio
    async def test_respiratory_distress_detected(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient has difficulty breathing.", [])

        assert report.has_emergency is True
        assert report.results[0].emergency_type == EmergencyType.RESPIRATORY_DISTRESS
        assert report.results[0].confidence >= 0.9

    @pytest.mark.asyncio
    async def test_loss_of_consciousness_detected(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("The patient passed out suddenly.", [])

        assert report.has_emergency is True
        assert report.results[0].emergency_type == EmergencyType.LOSS_OF_CONSCIOUSNESS
        assert report.results[0].confidence >= 0.8

    @pytest.mark.asyncio
    async def test_multiple_emergencies_in_one_text(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect(
            "Patient has chest pain and difficulty breathing.", []
        )

        assert report.has_emergency is True
        assert len(report.results) >= 2
        detected_types = {r.emergency_type for r in report.results}
        assert EmergencyType.CHEST_PAIN in detected_types
        assert EmergencyType.RESPIRATORY_DISTRESS in detected_types

    @pytest.mark.asyncio
    async def test_requires_override_true_for_severe_emergencies(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient is suicidal and wants to die.", [])

        assert report.has_emergency is True
        assert report.requires_override is True

    @pytest.mark.asyncio
    async def test_no_override_when_no_emergency(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient is feeling fine today.", [])

        assert report.requires_override is False

    @pytest.mark.asyncio
    async def test_recommended_action_includes_emergency_guidance(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient has chest pain.", [])

        assert report.results[0].recommended_action is not None
        assert "emergency" in report.results[0].recommended_action.lower()

    @pytest.mark.asyncio
    async def test_disclaimer_required_true(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("Patient has chest pain.", [])

        assert report.results[0].disclaimer_required is True

    @pytest.mark.asyncio
    async def test_confidence_scores_greater_than_zero(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect(
            "Patient has chest pain and passed out.", []
        )

        for result in report.results:
            assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_claims_list_parameter_works(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("", ["chest pain", "difficulty breathing"])

        assert report.has_emergency is True
        assert len(report.results) >= 2

    @pytest.mark.asyncio
    async def test_empty_text_returns_no_emergencies(self):
        detector = DefaultEmergencyDetector()
        report = await detector.detect("", [])

        assert report.has_emergency is False
        assert len(report.results) == 0
        assert report.max_severity == "none"
