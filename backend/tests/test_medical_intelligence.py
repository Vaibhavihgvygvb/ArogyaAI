from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.ai.medical.citations.citations import CitationEngine
from app.ai.medical.confidence.confidence import ConfidenceEngine
from app.ai.medical.config.config import MedicalSettings
from app.ai.medical.deps.deps import get_medical_service, reset_medical_service, set_medical_service
from app.ai.medical.exceptions.exceptions import (
    CitationError,
    ConfidenceError,
    IntentDetectionError,
    MedicalIntelligenceError,
    MedicalPromptError,
    MedicalReasoningError,
    QueryRewriteError,
    ResponseBuilderError,
    RetrievalOrchestrationError,
    SafetyValidationError,
    SpecialtyFilterError,
)
from app.ai.medical.intent.intent import IntentDetector
from app.ai.medical.pipelines.pipelines import DEFAULT_MEDICAL_SYSTEM_MESSAGE, MedicalPipeline
from app.ai.medical.reasoning.reasoning import MedicalReasoner
from app.ai.medical.responses.responses import ResponseBuilder
from app.ai.medical.rewriters.rewriters import QueryRewriter
from app.ai.medical.schemas.schemas import (
    CitationEntry,
    ConfidenceScore,
    IntentType,
    MedicalContext,
    MedicalIntent,
    MedicalMetadata,
    MedicalQuery,
    MedicalReasoning,
    MedicalResponse,
    MedicalSearchRequest,
    MedicalSearchResponse,
    QueryRewrite,
    SafetyCheckResult,
    Specialty,
    UrgencyLevel,
)
from app.ai.medical.services.services import MedicalService
from app.ai.medical.validators.validators import SafetyValidator
from app.ai.retrieval.deps.deps import get_retrieval_service  # noqa: F401 — ensure module loaded for patching
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_retrieval_service():
    mock = AsyncMock()
    mock.search = AsyncMock()
    mock.retrieve = AsyncMock()
    return mock


@pytest.fixture
def mock_gateway():
    mock = AsyncMock()
    mock_execute = AsyncMock()
    mock_execute.content = "Based on the medical evidence, hypertension requires lifestyle modifications and pharmacological intervention."
    mock_execute.model = "mock-model"
    mock_execute.provider = "mock-provider"
    mock_execute.usage = {"prompt_tokens": 100, "completion_tokens": 50}
    mock.execute = AsyncMock(return_value=mock_execute)
    return mock


@pytest.fixture
def medical_settings():
    return MedicalSettings(
        MEDICAL_ENABLED=True,
        MEDICAL_REWRITE_ENABLED=True,
        MEDICAL_SAFETY_ENABLED=True,
        MEDICAL_CITATIONS_REQUIRED=True,
        MEDICAL_REASONING_ENABLED=True,
    )


@pytest.fixture
def medical_query() -> MedicalQuery:
    return MedicalQuery(
        query="What are the symptoms of hypertension?",
        top_k=5,
        include_reasoning=True,
        include_citations=True,
    )


@pytest.fixture
def medical_intent() -> MedicalIntent:
    return MedicalIntent(
        intent_type=IntentType.DIAGNOSIS,
        specialty=Specialty.CARDIOLOGY,
        urgency=UrgencyLevel.MEDIUM,
        confidence=0.85,
        keywords=["hypertension", "symptoms", "blood pressure"],
    )


@pytest.fixture
def sample_citations() -> list[CitationEntry]:
    return [
        CitationEntry(
            chunk_id="chunk_1",
            knowledge_id="doc_cardio",
            document_id="doc_cardio",
            source="Cardiology Textbook",
            relevance_score=0.92,
            evidence_text="Hypertension is characterized by persistently elevated blood pressure...",
            metadata={"chunk_index": 0},
        ),
        CitationEntry(
            chunk_id="chunk_2",
            knowledge_id="doc_cardio",
            document_id="doc_cardio",
            source="Clinical Guidelines",
            relevance_score=0.85,
            evidence_text="Common symptoms include headaches, shortness of breath, and nosebleeds...",
            metadata={"chunk_index": 1},
        ),
    ]


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------


def test_medical_intelligence_exception_hierarchy():
    assert issubclass(IntentDetectionError, MedicalIntelligenceError)
    assert issubclass(QueryRewriteError, MedicalIntelligenceError)
    assert issubclass(RetrievalOrchestrationError, MedicalIntelligenceError)
    assert issubclass(CitationError, MedicalIntelligenceError)
    assert issubclass(ConfidenceError, MedicalIntelligenceError)
    assert issubclass(SafetyValidationError, MedicalIntelligenceError)
    assert issubclass(ResponseBuilderError, MedicalIntelligenceError)
    assert issubclass(MedicalPromptError, MedicalIntelligenceError)
    assert issubclass(MedicalReasoningError, MedicalIntelligenceError)
    assert issubclass(SpecialtyFilterError, MedicalIntelligenceError)


def test_exceptions_can_be_raised():
    with pytest.raises(MedicalIntelligenceError):
        raise IntentDetectionError("test")
    with pytest.raises(MedicalIntelligenceError):
        raise QueryRewriteError("test")
    with pytest.raises(MedicalIntelligenceError):
        raise SafetyValidationError("test")


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestMedicalSchemas:
    def test_medical_query_valid(self):
        q = MedicalQuery(query="What causes diabetes?")
        assert q.query == "What causes diabetes?"
        assert q.top_k == 10
        assert q.include_reasoning is True
        assert q.include_citations is True

    def test_medical_query_empty_raises(self):
        with pytest.raises(ValueError):
            MedicalQuery(query="")

    def test_medical_intent_enum_values(self):
        assert IntentType.DIAGNOSIS.value == "diagnosis"
        assert IntentType.TREATMENT.value == "treatment"
        assert Specialty.CARDIOLOGY.value == "cardiology"
        assert UrgencyLevel.CRITICAL.value == "critical"

    def test_medical_response_defaults(self):
        r = MedicalResponse(answer="Test answer")
        assert r.answer == "Test answer"
        assert r.citations == []
        assert r.intent is None
        assert r.confidence is None
        assert r.safety is None

    def test_confidence_score_bounds(self):
        c = ConfidenceScore(overall=0.5, retrieval_confidence=0.8, evidence_confidence=0.6, generation_confidence=0.7, citation_coverage=0.4)
        assert 0 <= c.overall <= 1
        assert 0 <= c.retrieval_confidence <= 1

    def test_safety_check_result_defaults(self):
        s = SafetyCheckResult()
        assert s.passed is True
        assert s.warnings == []

    def test_citation_entry_creation(self):
        c = CitationEntry(chunk_id="c1", knowledge_id="k1", evidence_text="evidence")
        assert c.chunk_id == "c1"
        assert c.relevance_score == 0.0

    def test_medical_search_request(self):
        r = MedicalSearchRequest(query="heart disease")
        assert r.query == "heart disease"
        assert r.top_k == 10

    def test_medical_metadata_defaults(self):
        m = MedicalMetadata()
        assert m.processing_time_ms == 0.0
        assert m.pipeline_stages == {}

    def test_medical_reasoning_defaults(self):
        r = MedicalReasoning()
        assert r.differential_considerations == []
        assert r.limitations == []


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------


class TestMedicalSettings:
    def test_default_settings(self):
        s = MedicalSettings()
        assert s.MEDICAL_ENABLED is True
        assert s.MEDICAL_DEFAULT_SPECIALTY == "general_medicine"
        assert s.MEDICAL_REWRITE_ENABLED is True
        assert s.MEDICAL_SAFETY_ENABLED is True

    def test_specialties_property(self):
        s = MedicalSettings()
        specialties = s.specialties
        assert "cardiology" in specialties
        assert "neurology" in specialties
        assert "general_medicine" in specialties
        assert len(specialties) == 20

    def test_urgency_levels(self):
        s = MedicalSettings()
        levels = s.urgency_levels
        assert "critical" in levels
        assert "routine" in levels
        assert "emergency" in levels["critical"]
        assert "follow_up" in levels["routine"]


# ---------------------------------------------------------------------------
# Intent Detector Tests
# ---------------------------------------------------------------------------


class TestIntentDetector:
    @pytest.fixture
    def detector(self):
        return IntentDetector()

    @pytest.mark.asyncio
    async def test_detect_diagnosis_intent(self, detector):
        intent = await detector.detect("What are the symptoms of diabetes?")
        assert intent.intent_type in (IntentType.DIAGNOSIS, IntentType.SYMPTOM_ASSESSMENT)

    @pytest.mark.asyncio
    async def test_detect_treatment_intent(self, detector):
        intent = await detector.detect("How to treat hypertension?")
        assert intent.intent_type == IntentType.TREATMENT

    @pytest.mark.asyncio
    async def test_detect_medication_intent(self, detector):
        intent = await detector.detect("What is the dosage of metformin?")
        assert intent.intent_type == IntentType.MEDICATION

    @pytest.mark.asyncio
    async def test_detect_cardiology_specialty(self, detector):
        intent = await detector.detect("Chest pain and palpitations with ECG findings")
        assert intent.specialty == Specialty.CARDIOLOGY

    @pytest.mark.asyncio
    async def test_detect_neurology_specialty(self, detector):
        intent = await detector.detect("Severe headache with neurological deficits")
        assert intent.specialty == Specialty.NEUROLOGY

    @pytest.mark.asyncio
    async def test_detect_critical_urgency(self, detector):
        intent = await detector.detect("Patient is unconscious and not breathing!")
        assert intent.urgency == UrgencyLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_detect_routine_urgency(self, detector):
        intent = await detector.detect("Annual checkup and routine screening")
        assert intent.urgency == UrgencyLevel.ROUTINE

    @pytest.mark.asyncio
    async def test_detect_with_specialty_hint(self, detector):
        intent = await detector.detect("What causes this condition?", specialty_hint="cardiology")
        assert intent.specialty == Specialty.CARDIOLOGY

    @pytest.mark.asyncio
    async def test_detect_general_inquiry(self, detector):
        intent = await detector.detect("Tell me about the human body")
        assert intent.intent_type == IntentType.GENERAL_INQUIRY

    @pytest.mark.asyncio
    async def test_detect_general_medicine_fallback(self, detector):
        intent = await detector.detect("xyz random non-medical query")
        assert intent.specialty == Specialty.GENERAL_MEDICINE


# ---------------------------------------------------------------------------
# Query Rewriter Tests
# ---------------------------------------------------------------------------


class TestQueryRewriter:
    @pytest.fixture
    def rewriter(self):
        return QueryRewriter()

    @pytest.mark.asyncio
    async def test_expand_abbreviations(self, rewriter, medical_intent):
        result = await rewriter.rewrite("What causes SOB in COPD?", medical_intent)
        assert len(result.abbreviations_expanded) == 2
        assert any("SOB" in a for a in result.abbreviations_expanded)
        assert any("COPD" in a for a in result.abbreviations_expanded)

    @pytest.mark.asyncio
    async def test_rewrite_no_changes(self, rewriter, medical_intent):
        result = await rewriter.rewrite("What is hypertension?", medical_intent)
        assert result.rewritten_query == result.original_query

    @pytest.mark.asyncio
    async def test_rewrite_reason_when_expanded(self, rewriter):
        intent = MedicalIntent(intent_type=IntentType.DIAGNOSIS, specialty=Specialty.CARDIOLOGY)
        result = await rewriter.rewrite("What causes HTN?", intent)
        assert "Expanded 1 abbreviation" in result.rewrite_reason

    @pytest.mark.asyncio
    async def test_rewrite_preserves_original(self, rewriter, medical_intent):
        original = "What causes diabetes?"
        result = await rewriter.rewrite(original, medical_intent)
        assert result.original_query == original


# ---------------------------------------------------------------------------
# Citation Engine Tests
# ---------------------------------------------------------------------------


class TestCitationEngine:
    @pytest.fixture
    def engine(self):
        return CitationEngine()

    @pytest.mark.asyncio
    async def test_build_citations_from_objects(self, engine):
        class MockResult:
            def __init__(self, chunk_id, knowledge_id, score, content, source):
                self.chunk_id = chunk_id
                self.knowledge_id = knowledge_id
                self.document_id = knowledge_id
                self.score = score
                self.content = content
                self.metadata = {"source_document": source}

        results = [
            MockResult("c1", "k1", 0.9, "Evidence text 1", "Source A"),
            MockResult("c2", "k2", 0.8, "Evidence text 2", "Source B"),
        ]
        citations = await engine.build_citations(results, top_k=10)
        assert len(citations) == 2
        assert citations[0].chunk_id == "c1"
        assert citations[0].relevance_score == 0.9
        assert citations[1].evidence_text == "Evidence text 2"

    @pytest.mark.asyncio
    async def test_build_citations_empty_input(self, engine):
        citations = await engine.build_citations([], top_k=10)
        assert citations == []

    @pytest.mark.asyncio
    async def test_build_citations_respects_top_k(self, engine):
        class MockResult:
            def __init__(self, i):
                self.chunk_id = f"c{i}"
                self.knowledge_id = f"k{i}"
                self.document_id = f"k{i}"
                self.score = 1.0 - i * 0.1
                self.content = f"Content {i}"
                self.metadata = {"source_document": f"Src{i}"}

        results = [MockResult(i) for i in range(20)]
        citations = await engine.build_citations(results, top_k=5)
        assert len(citations) == 5


# ---------------------------------------------------------------------------
# Confidence Engine Tests
# ---------------------------------------------------------------------------


class TestConfidenceEngine:
    @pytest.fixture
    def engine(self):
        return ConfidenceEngine()

    @pytest.mark.asyncio
    async def test_score_high_confidence(self, engine, medical_intent, sample_citations):
        score = await engine.score(
            query="What is hypertension?",
            response="Hypertension is a chronic medical condition characterized by elevated blood pressure. "
                     "It requires ongoing management and monitoring. Common symptoms include headaches. "
                     "Treatment involves lifestyle modifications and medication.",
            citations=sample_citations,
            intent=medical_intent,
        )
        assert score.overall > 0.3
        assert score.retrieval_confidence > 0.3
        assert score.evidence_confidence > 0.3

    @pytest.mark.asyncio
    async def test_score_no_citations(self, engine, medical_intent):
        score = await engine.score(
            query="test",
            response="Short response",
            citations=[],
            intent=medical_intent,
        )
        assert score.overall < 0.5

    @pytest.mark.asyncio
    async def test_score_all_scores_in_range(self, engine, medical_intent, sample_citations):
        score = await engine.score(
            query="test",
            response="A moderate length response about medical conditions and their management in clinical practice.",
            citations=sample_citations,
            intent=medical_intent,
        )
        assert 0 <= score.overall <= 1
        assert 0 <= score.retrieval_confidence <= 1
        assert 0 <= score.evidence_confidence <= 1
        assert 0 <= score.generation_confidence <= 1
        assert 0 <= score.citation_coverage <= 1


# ---------------------------------------------------------------------------
# Safety Validator Tests
# ---------------------------------------------------------------------------


class TestSafetyValidator:
    @pytest.fixture
    def validator(self):
        return SafetyValidator()

    @pytest.mark.asyncio
    async def test_validate_safe_response(self, validator, medical_intent, sample_citations):
        result = await validator.validate(
            query="What is hypertension?",
            response="Hypertension is a condition. Consult your doctor for proper diagnosis and treatment. "
                     "This is not medical advice. Seek immediate medical attention for emergencies.",
            citations=sample_citations,
            intent=medical_intent,
        )
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_validate_unsafe_advice(self, validator, medical_intent):
        result = await validator.validate(
            query="Can I stop taking medication?",
            response="Yes, you should discontinue your medication without consulting your doctor.",
            citations=[],
            intent=medical_intent,
        )
        assert result.unsafe_advice_risk > 0

    @pytest.mark.asyncio
    async def test_validate_missing_disclaimer(self, validator, medical_intent, sample_citations):
        result = await validator.validate(
            query="test query",
            response="Some medical response without any disclaimer.",
            citations=sample_citations,
            intent=medical_intent,
        )
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# Response Builder Tests
# ---------------------------------------------------------------------------


class TestResponseBuilder:
    @pytest.fixture
    def builder(self):
        return ResponseBuilder()

    @pytest.mark.asyncio
    async def test_build_basic_response(self, builder):
        response = await builder.build(answer="Test medical answer.")
        assert isinstance(response, MedicalResponse)
        assert response.answer.startswith("Test medical answer.")
        assert response.citations == []

    @pytest.mark.asyncio
    async def test_build_with_citations(self, builder, sample_citations):
        response = await builder.build(
            answer="Medical answer.",
            citations=sample_citations,
            confidence=ConfidenceScore(overall=0.8, retrieval_confidence=0.8, evidence_confidence=0.8, generation_confidence=0.8, citation_coverage=0.8),
            safety=SafetyCheckResult(passed=True),
            metadata=MedicalMetadata(model="test", provider="test"),
        )
        assert "References:" in response.answer

    @pytest.mark.asyncio
    async def test_build_raises_on_empty_answer(self, builder):
        with pytest.raises(ResponseBuilderError):
            await builder.build(answer="")

    @pytest.mark.asyncio
    async def test_build_with_failed_safety(self, builder, sample_citations):
        response = await builder.build(
            answer="Test answer.",
            citations=sample_citations,
            safety=SafetyCheckResult(passed=False, hallucination_risk=0.8, unsafe_advice_risk=0.5, contradiction_risk=0.3, warnings=["test"]),
        )
        assert "safety validation" in response.answer.lower()


# ---------------------------------------------------------------------------
# Pipeline Tests
# ---------------------------------------------------------------------------


class TestMedicalPipeline:
    @pytest.fixture
    def pipeline(self, medical_settings):
        return MedicalPipeline(settings=medical_settings)

    @pytest.mark.asyncio
    async def test_pipeline_full_flow(self, pipeline, medical_query):
        with (
            patch("app.ai.gateway.deps.get_gateway") as mock_get_gateway,
        ):
            mock_gw = AsyncMock()
            mock_exec = MagicMock()
            mock_exec.content = "Hypertension symptoms include headaches, shortness of breath, and nosebleeds."
            mock_exec.model = "mock-model"
            mock_exec.provider = "mock-provider"
            mock_exec.usage = {"prompt_tokens": 50, "completion_tokens": 30}
            mock_gw.execute = AsyncMock(return_value=mock_exec)
            mock_get_gateway.return_value = mock_gw

            response = await pipeline.run(
                query=medical_query,
                retrieval_results=[],
                retrieval_context="Hypertension is a chronic condition. Symptoms vary by severity.",
            )

            assert isinstance(response, MedicalResponse)
            assert response.answer
            assert response.intent is not None
            assert response.reasoning is not None
            assert response.confidence is not None
            assert response.safety is not None

    @pytest.mark.asyncio
    async def test_pipeline_without_reasoning(self, pipeline):
        query = MedicalQuery(query="Test query", include_reasoning=False)
        with patch("app.ai.gateway.deps.get_gateway") as mock_get_gw:
            mock_gw = AsyncMock()
            mock_exec = MagicMock()
            mock_exec.content = "Test answer."
            mock_exec.model = "m"
            mock_exec.provider = "p"
            mock_exec.usage = {}
            mock_gw.execute = AsyncMock(return_value=mock_exec)
            mock_get_gw.return_value = mock_gw

            response = await pipeline.run(query=query)
            assert response.reasoning is None


# ---------------------------------------------------------------------------
# MedicalService Tests
# ---------------------------------------------------------------------------


class TestMedicalService:
    @pytest.fixture
    def service(self):
        reset_medical_service()
        svc = MedicalService()
        set_medical_service(svc)
        yield svc
        reset_medical_service()

    @pytest.mark.asyncio
    async def test_medical_query(self, service, mock_retrieval_service):
        with (
            patch("app.ai.medical.services.services.get_retrieval_service") as mock_get_retrieval,
            patch("app.ai.gateway.deps.get_gateway") as mock_get_gateway,
        ):
            mock_get_retrieval.return_value = mock_retrieval_service

            class MockRetrievalResult:
                def __init__(self):
                    self.content = "Test content"
                    self.chunk_id = "chunk_1"
                    self.knowledge_id = "doc_1"
                    self.document_id = "doc_1"
                    self.score = 0.9
                    self.metadata = {}

            mock_search_response = MagicMock()
            mock_search_response.results = [MockRetrievalResult()]
            mock_retrieval_service.search = AsyncMock(return_value=mock_search_response)

            mock_gw = AsyncMock()
            mock_exec = MagicMock()
            mock_exec.content = "Test medical answer about hypertension."
            mock_exec.model = "mock-model"
            mock_exec.provider = "mock-provider"
            mock_exec.usage = {}
            mock_gw.execute = AsyncMock(return_value=mock_exec)
            mock_get_gateway.return_value = mock_gw

            response = await service.query(
                MedicalQuery(query="What is hypertension?", top_k=3)
            )
            assert isinstance(response, MedicalResponse)
            assert response.answer

    @pytest.mark.asyncio
    async def test_medical_search(self, service, mock_retrieval_service):
        with patch("app.ai.medical.services.services.get_retrieval_service") as mock_get_retrieval:
            mock_get_retrieval.return_value = mock_retrieval_service

            class MockSearchResult:
                def __init__(self):
                    self.content = "Search result content"
                    self.chunk_id = "c1"
                    self.knowledge_id = "k1"
                    self.document_id = "d1"
                    self.score = 0.85
                    self.metadata = {}

            mock_response = MagicMock()
            mock_response.results = [MockSearchResult()]
            mock_retrieval_service.search = AsyncMock(return_value=mock_response)

            response = await service.search(
                MedicalSearchRequest(query="heart disease symptoms", top_k=5)
            )
            assert isinstance(response, MedicalSearchResponse)
            assert response.query == "heart disease symptoms"
            assert response.total >= 0
            assert response.intent is not None


# ---------------------------------------------------------------------------
# DI Tests
# ---------------------------------------------------------------------------


class TestDependencyInjection:
    def test_get_set_reset(self):
        reset_medical_service()
        assert get_medical_service() is not None

        svc = MedicalService()
        set_medical_service(svc)
        assert get_medical_service() is svc

        reset_medical_service()
        assert get_medical_service() is not None
        assert get_medical_service() is not svc

    def test_singleton_behavior(self):
        reset_medical_service()
        s1 = get_medical_service()
        s2 = get_medical_service()
        assert s1 is s2
        reset_medical_service()


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------


class TestMedicalAPI:
    @pytest.fixture(autouse=True)
    def setup_di(self):
        reset_medical_service()
        yield
        reset_medical_service()

    def test_medical_query_endpoint_authenticated(self, client, doctor_token):
        mock_svc = AsyncMock()

        async def mock_query(request):
            return MedicalResponse(
                answer="Test answer about hypertension. Consult your doctor.",
                intent=MedicalIntent(
                    intent_type=IntentType.DIAGNOSIS,
                    specialty=Specialty.CARDIOLOGY,
                    urgency=UrgencyLevel.MEDIUM,
                    confidence=0.85,
                ),
                citations=[
                    CitationEntry(
                        chunk_id="c1",
                        knowledge_id="k1",
                        evidence_text="Evidence",
                        relevance_score=0.9,
                    )
                ],
                confidence=ConfidenceScore(overall=0.8, retrieval_confidence=0.8, evidence_confidence=0.8, generation_confidence=0.8, citation_coverage=0.8),
                safety=SafetyCheckResult(passed=True),
                metadata=MedicalMetadata(model="test", provider="test"),
            )

        mock_svc.query = mock_query
        set_medical_service(mock_svc)

        response = client.post(
            "/ai/medical/query",
            json={"query": "What is hypertension?"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "answer" in data
        assert "intent" in data
        assert "citations" in data
        assert "confidence" in data
        assert "safety" in data

    def test_medical_query_endpoint_unauthenticated(self, client):
        response = client.post(
            "/ai/medical/query",
            json={"query": "What is hypertension?"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_medical_search_endpoint_authenticated(self, client, doctor_token):
        mock_svc = AsyncMock()

        async def mock_search(request):
            return MedicalSearchResponse(
                results=[CitationEntry(chunk_id="c1", knowledge_id="k1", evidence_text="e")],
                total=1,
                query=request.query,
                intent=MedicalIntent(
                    intent_type=IntentType.DIAGNOSIS,
                    specialty=Specialty.CARDIOLOGY,
                ),
            )

        mock_svc.search = mock_search
        set_medical_service(mock_svc)

        response = client.post(
            "/ai/medical/search",
            json={"query": "heart disease"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert "intent" in data
        assert data["total"] == 1

    def test_medical_search_endpoint_unauthenticated(self, client):
        response = client.post(
            "/ai/medical/search",
            json={"query": "heart disease"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_medical_query_with_specialty_hint(self, client, doctor_token):
        mock_svc = AsyncMock()

        async def mock_query(request):
            return MedicalResponse(
                answer="Cardiology-related answer.",
                intent=MedicalIntent(
                    intent_type=IntentType.DIAGNOSIS,
                    specialty=Specialty.CARDIOLOGY,
                ),
            )

        mock_svc.query = mock_query
        set_medical_service(mock_svc)

        response = client.post(
            "/ai/medical/query",
            json={"query": "chest pain", "specialty": "cardiology"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# MedicalReasoner Tests
# ---------------------------------------------------------------------------


class TestMedicalReasoner:
    @pytest.fixture
    def reasoner(self):
        return MedicalReasoner()

    @pytest.mark.asyncio
    async def test_reason_diagnosis(self, reasoner, medical_intent):
        reasoning = await reasoner.reason(
            query="What causes diabetes?",
            context="Diabetes is a metabolic disorder. Key symptoms include polyuria and polydipsia.",
            response="Diabetes is caused by insulin deficiency or resistance.",
            intent=medical_intent,
        )
        assert reasoning.chain_of_thought is not None
        assert "Diagnosis" in reasoning.chain_of_thought

    @pytest.mark.asyncio
    async def test_reason_identifies_limitations(self, reasoner, medical_intent):
        reasoning = await reasoner.reason(
            query="test", context="", response="Brief.",
            intent=medical_intent,
        )
        assert len(reasoning.limitations) > 0

    @pytest.mark.asyncio
    async def test_reason_empty_context(self, reasoner, medical_intent):
        reasoning = await reasoner.reason(
            query="test", context="", response="Response text.",
            intent=medical_intent,
        )
        assert "No evidence base" in (reasoning.evidence_summary or "")


# ---------------------------------------------------------------------------
# MedicalSettings Edge Cases
# ---------------------------------------------------------------------------


class TestMedicalSettingsEdgeCases:
    def test_specialties_not_empty(self):
        s = MedicalSettings()
        assert len(s.specialties) > 0

    def test_urgency_levels_contain_all_levels(self):
        s = MedicalSettings()
        assert set(s.urgency_levels.keys()) == {"critical", "high", "medium", "low", "routine"}
