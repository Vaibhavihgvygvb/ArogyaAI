import pytest

from app.ai.clinical_safety.services.phi import DefaultPHIValidator
from app.ai.clinical_safety.schemas import PHIType


@pytest.mark.asyncio
async def test_clean_text_no_phi():
    validator = DefaultPHIValidator()
    report = await validator.validate("The patient has a mild fever and cough.")
    assert len(report.findings) == 0
    assert report.total_findings == 0
    assert report.has_phi is False
    assert report.passed is True


@pytest.mark.asyncio
async def test_detects_ssn():
    validator = DefaultPHIValidator()
    report = await validator.validate("SSN is 123-45-6789.")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.SSN


@pytest.mark.asyncio
async def test_detects_email():
    validator = DefaultPHIValidator()
    report = await validator.validate("Contact test@example.com for details.")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.EMAIL


@pytest.mark.asyncio
async def test_detects_phone():
    validator = DefaultPHIValidator()
    report = await validator.validate("Call 9876543210 now.")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.PHONE


@pytest.mark.asyncio
async def test_detects_aadhaar():
    validator = DefaultPHIValidator()
    report = await validator.validate("Aadhaar: 1234 5678 9012")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.AADHAAR


@pytest.mark.asyncio
async def test_detects_passport():
    validator = DefaultPHIValidator()
    report = await validator.validate("Passport AB123456 is on file.")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.PASSPORT


@pytest.mark.asyncio
async def test_detects_credit_card():
    validator = DefaultPHIValidator()
    report = await validator.validate("Card: 4111111111111111")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.CREDIT_CARD


@pytest.mark.asyncio
async def test_detects_medical_record_number():
    validator = DefaultPHIValidator()
    report = await validator.validate("MRN-12345")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.MEDICAL_RECORD_NUMBER


@pytest.mark.asyncio
async def test_detects_insurance_id():
    validator = DefaultPHIValidator()
    report = await validator.validate("INS-12345")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.INSURANCE_ID


@pytest.mark.asyncio
async def test_detects_dob():
    validator = DefaultPHIValidator()
    report = await validator.validate("born on 01/15/1990")
    assert len(report.findings) == 1
    assert report.findings[0].phi_type == PHIType.DOB


@pytest.mark.asyncio
async def test_multiple_phi_findings():
    validator = DefaultPHIValidator()
    text = "SSN: 123-45-6789, Email: test@example.com, Phone: 9876543210"
    report = await validator.validate(text)
    assert report.total_findings >= 3
    types = {f.phi_type for f in report.findings}
    assert PHIType.SSN in types
    assert PHIType.EMAIL in types
    assert PHIType.PHONE in types


@pytest.mark.asyncio
async def test_value_preview_masks_sensitive_data():
    validator = DefaultPHIValidator()
    report = await validator.validate("SSN is 123-45-6789")
    finding = report.findings[0]
    assert "123-45-6789" not in finding.value_preview
    assert finding.value_preview == "1*********9"


@pytest.mark.asyncio
async def test_risk_levels_assigned():
    validator = DefaultPHIValidator()
    report = await validator.validate("SSN: 123-45-6789, Email: user@test.com")
    for f in report.findings:
        if f.phi_type == PHIType.SSN:
            assert f.risk == "high"
        elif f.phi_type == PHIType.EMAIL:
            assert f.risk == "medium"


@pytest.mark.asyncio
async def test_has_phi_when_phi_found():
    validator = DefaultPHIValidator()
    report = await validator.validate("Contact: test@example.com")
    assert report.has_phi is True


@pytest.mark.asyncio
async def test_passed_false_when_phi_found():
    validator = DefaultPHIValidator()
    report = await validator.validate("SSN: 123-45-6789")
    assert report.passed is False


@pytest.mark.asyncio
async def test_total_findings_count():
    validator = DefaultPHIValidator()
    text = "Email: a@b.com, SSN: 123-45-6789, Phone: 9876543210"
    report = await validator.validate(text)
    assert report.total_findings == 3
