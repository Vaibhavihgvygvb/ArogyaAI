import pytest
from pydantic import BaseModel, ValidationError

from app.ai.evidence.validation import HealthEvidenceValidator


class DummyModel(BaseModel):
    result: HealthEvidenceValidator


class TestHealthEvidenceValidator:
    def test_validator_passes_when_passed_true(self):
        model = DummyModel(result={"passed": True, "summary": "All good", "warnings": []})
        assert model.result.passed is True
        assert model.result.summary == "All good"

    def test_validator_raises_when_passed_false(self):
        with pytest.raises(ValidationError) as excinfo:
            DummyModel(result={"passed": False, "summary": "Validation failed", "warnings": ["Low confidence"]})

        error_str = str(excinfo.value)
        assert "Evidence validation failed" in error_str
        assert "Validation failed" in error_str
        assert "Low confidence" in error_str

    def test_validator_passes_when_value_is_none(self):
        model = DummyModel(result=None)
        assert model.result is None

    def test_validator_message_includes_summary(self):
        with pytest.raises(ValidationError) as excinfo:
            DummyModel(result={"passed": False, "summary": "Coverage too low", "warnings": []})

        assert "Coverage too low" in str(excinfo.value)

    def test_validator_message_includes_warnings(self):
        with pytest.raises(ValidationError) as excinfo:
            DummyModel(result={"passed": False, "summary": "Check failed", "warnings": ["warn1", "warn2"]})

        error_str = str(excinfo.value)
        assert "warn1" in error_str
        assert "warn2" in error_str

    def test_validator_accepts_empty_warnings_list(self):
        with pytest.raises(ValidationError):
            DummyModel(result={"passed": False, "summary": "Failed", "warnings": []})

    def test_validator_with_extra_fields(self):
        model = DummyModel(result={
            "passed": True,
            "summary": "OK",
            "warnings": [],
            "errors": [],
            "processing_time_ms": 10.5,
        })
        assert model.result.processing_time_ms == 10.5
