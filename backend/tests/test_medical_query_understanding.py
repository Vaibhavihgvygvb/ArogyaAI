import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status

from app.ai.medical.exceptions.query_exceptions import (
    QueryUnderstandingError,
    IntentError,
    EntityError,
    SpecialtyError,
    UrgencyError,
    AudienceError,
    LanguageError,
    ContextError,
    TaxonomyError,
    ValidationError,
)
from app.ai.medical.engine.schemas import (
    AnalysisScope,
    EntityType,
    AudienceType,
    MedicalEntity,
    EntityResult,
    IntentCandidate,
    IntentResult,
    SpecialtyCandidate,
    SpecialtyResult,
    UrgencyResult,
    AudienceResult,
    LanguageInfo,
    RewriteResult,
    ConversationContext,
    QueryUnderstandingResult,
    AnalyzeRequest,
    AnalyzeResponse,
)
from app.ai.medical.engine.deps import get_query_understanding_engine, set_query_understanding_engine, reset_query_understanding_engine
from app.ai.medical.engine.services import QueryUnderstandingEngine
from app.ai.medical.intent.classifiers import RuleBasedIntentClassifier
from app.ai.medical.intent.services import IntentDetectorService
from app.ai.medical.intent.schemas import INTENT_CATEGORIES, IntentCategory
from app.ai.medical.entities.services import EntityExtractor
from app.ai.medical.entities.patterns import RuleBasedEntityExtractor
from app.ai.medical.specialty.services import SpecialtyClassifier
from app.ai.medical.urgency.services import UrgencyClassifier
from app.ai.medical.audience.services import AudienceClassifier
from app.ai.medical.language.services import LanguageDetector
from app.ai.medical.rewrite.services import QueryRewriter
from app.ai.medical.context.services import ContextResolver
from app.ai.medical.taxonomy.services import MedicalTaxonomyService
from app.ai.medical.taxonomy.schemas import TerminologySystem
from app.main import app


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------

class TestQueryExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(IntentError, QueryUnderstandingError)
        assert issubclass(EntityError, QueryUnderstandingError)
        assert issubclass(SpecialtyError, QueryUnderstandingError)
        assert issubclass(UrgencyError, QueryUnderstandingError)
        assert issubclass(AudienceError, QueryUnderstandingError)
        assert issubclass(LanguageError, QueryUnderstandingError)
        assert issubclass(ContextError, QueryUnderstandingError)
        assert issubclass(TaxonomyError, QueryUnderstandingError)
        assert issubclass(ValidationError, QueryUnderstandingError)

    def test_exceptions_can_be_raised(self):
        with pytest.raises(QueryUnderstandingError):
            raise IntentError("test")
        with pytest.raises(QueryUnderstandingError):
            raise ValidationError("empty query")


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------

class TestEngineSchemas:
    def test_entity_type_values(self):
        assert EntityType.SYMPTOM.value == "symptom"
        assert EntityType.DISEASE.value == "disease"
        assert EntityType.MEDICATION.value == "medication"

    def test_audience_type_values(self):
        assert AudienceType.PATIENT.value == "patient"
        assert AudienceType.DOCTOR.value == "doctor"
        assert AudienceType.UNKNOWN.value == "unknown"

    def test_analysis_scope_values(self):
        assert AnalysisScope.FULL.value == "full"
        assert AnalysisScope.INTENT.value == "intent"

    def test_medical_entity_defaults(self):
        e = MedicalEntity(entity_type=EntityType.SYMPTOM, text="headache")
        assert e.confidence == 0.0
        assert e.attributes == {}

    def test_intent_candidate_confidence_range(self):
        c = IntentCandidate(intent_type="symptom_inquiry", confidence=0.85)
        assert 0 <= c.confidence <= 1

    def test_urgency_result_disclaimer(self):
        u = UrgencyResult(level="emergency", is_emergency=True)
        assert "clinical judgment" in u.disclaimer

    def test_query_understanding_result_defaults(self):
        r = QueryUnderstandingResult(original_query="test query")
        assert r.intent is None
        assert r.entities is None
        assert r.analysis_scope == AnalysisScope.FULL

    def test_analyze_request_validation(self):
        r = AnalyzeRequest(query="What is diabetes?")
        assert r.query == "What is diabetes?"
        assert r.scope == AnalysisScope.FULL
        assert r.include_rewrite is True

    def test_entity_result_empty(self):
        r = EntityResult()
        assert r.entities == []
        assert r.total == 0


# ---------------------------------------------------------------------------
# RuleBasedIntentClassifier Tests
# ---------------------------------------------------------------------------

class TestRuleBasedIntentClassifier:
    @pytest.fixture
    def classifier(self):
        return RuleBasedIntentClassifier()

    def test_classify_symptom_inquiry(self, classifier):
        result = classifier.classify("I have a severe headache and fever")
        assert result.primary_intent.intent_type == "symptom_inquiry"
        assert result.primary_intent.confidence > 0

    def test_classify_disease_information(self, classifier):
        result = classifier.classify("What is diabetes mellitus?")
        assert result.primary_intent.intent_type == "disease_information"

    def test_classify_medication(self, classifier):
        result = classifier.classify("What is the dosage of metformin?")
        assert result.primary_intent.intent_type == "medication_information"

    def test_classify_emergency(self, classifier):
        result = classifier.classify("Patient is unconscious and not breathing!")
        assert result.primary_intent.intent_type == "emergency"

    def test_classify_mental_health(self, classifier):
        result = classifier.classify("I have been feeling very anxious and depressed")
        assert result.primary_intent.intent_type == "mental_health"

    def test_classify_general_inquiry_fallback(self, classifier):
        result = classifier.classify("xyz random non medical text")
        assert result.primary_intent.intent_type == "general_inquiry"

    def test_classify_multiple_candidates(self, classifier):
        result = classifier.classify("What is diabetes and how to treat it?")
        assert result.total_candidates >= 1


# ---------------------------------------------------------------------------
# IntentDetectorService Tests
# ---------------------------------------------------------------------------

class TestIntentDetectorService:
    @pytest.fixture
    def service(self):
        return IntentDetectorService()

    @pytest.mark.asyncio
    async def test_detect_symptom(self, service):
        result = await service.detect("I feel dizzy and nauseous")
        assert result.primary_intent.intent_type is not None
        assert result.primary_intent.confidence > 0

    @pytest.mark.asyncio
    async def test_detect_empty_query(self, service):
        result = await service.detect("hello world test")
        assert len(result.candidates) >= 0


# ---------------------------------------------------------------------------
# EntityExtractor Tests
# ---------------------------------------------------------------------------

class TestEntityExtractor:
    @pytest.fixture
    def extractor(self):
        return EntityExtractor()

    def test_extract_symptoms(self, extractor):
        result = extractor.extract("I have a severe headache and fever")
        assert len(result.entities) >= 1
        types = [e.entity_type for e in result.entities]
        assert EntityType.SYMPTOM in types

    def test_extract_diseases(self, extractor):
        result = extractor.extract("Patient has diabetes and hypertension")
        assert len(result.entities) >= 1
        types = [e.entity_type for e in result.entities]
        assert EntityType.DISEASE in types

    def test_extract_medications(self, extractor):
        result = extractor.extract("Taking metformin and atorvastatin")
        assert len(result.entities) >= 1
        types = [e.entity_type for e in result.entities]
        assert EntityType.MEDICATION in types

    def test_extract_anatomy(self, extractor):
        result = extractor.extract("Pain in the heart and liver")
        types = [e.entity_type for e in result.entities]
        assert EntityType.ANATOMY in types

    def test_extract_dosage(self, extractor):
        result = extractor.extract("Take 500mg twice daily")
        types = [e.entity_type for e in result.entities]
        assert EntityType.DOSAGE in types

    def test_extract_empty_query(self, extractor):
        result = extractor.extract("")
        assert result.entities == []

    def test_extract_non_medical(self, extractor):
        result = extractor.extract("hello world")
        assert result.entities == []

    def test_extract_multiple_types(self, extractor):
        result = extractor.extract("Heart disease patient takes aspirin 75mg daily for chest pain")
        assert len(result.entities) >= 3


# ---------------------------------------------------------------------------
# SpecialtyClassifier Tests
# ---------------------------------------------------------------------------

class TestSpecialtyClassifier:
    @pytest.fixture
    def classifier(self):
        return SpecialtyClassifier()

    def test_classify_cardiology(self, classifier):
        result = classifier.classify("Chest pain and hypertension with ECG changes")
        assert result.primary_specialty.specialty == "cardiology"

    def test_classify_neurology(self, classifier):
        result = classifier.classify("Severe headache with stroke symptoms")
        assert result.primary_specialty.specialty == "neurology"

    def test_classify_endocrinology(self, classifier):
        result = classifier.classify("Diabetes and thyroid problems")
        assert result.primary_specialty.specialty == "endocrinology"

    def test_classify_oncology(self, classifier):
        result = classifier.classify("Cancer tumor malignancy chemotherapy")
        assert result.primary_specialty.specialty == "oncology"

    def test_classify_general_fallback(self, classifier):
        result = classifier.classify("xyz non medical query")
        assert result.primary_specialty.specialty == "general_medicine"

    def test_classify_multiple_specialties(self, classifier):
        result = classifier.classify("Heart disease with diabetes and skin rash")
        assert result.total_candidates >= 2


# ---------------------------------------------------------------------------
# UrgencyClassifier Tests
# ---------------------------------------------------------------------------

class TestUrgencyClassifier:
    @pytest.fixture
    def classifier(self):
        return UrgencyClassifier()

    def test_classify_emergency(self, classifier):
        result = classifier.classify("Patient is unconscious and not breathing!")
        assert result.level == "emergency"
        assert result.is_emergency is True

    def test_classify_urgent(self, classifier):
        result = classifier.classify("Severe chest pain with shortness of breath")
        assert result.level == "urgent"

    def test_classify_informational(self, classifier):
        result = classifier.classify("What is the definition of diabetes?")
        assert result.level == "informational"

    def test_classify_routine(self, classifier):
        result = classifier.classify("Annual checkup and routine screening")
        assert result.level == "routine"

    def test_classify_has_indicators(self, classifier):
        result = classifier.classify("Emergency! Severe bleeding")
        assert len(result.indicators) > 0


# ---------------------------------------------------------------------------
# AudienceClassifier Tests
# ---------------------------------------------------------------------------

class TestAudienceClassifier:
    @pytest.fixture
    def classifier(self):
        return AudienceClassifier()

    def test_classify_patient(self, classifier):
        result = classifier.classify("What should I do for my headache?")
        assert result.audience == AudienceType.PATIENT

    def test_classify_doctor(self, classifier):
        result = classifier.classify("My patient has an abnormal lab result")
        assert result.audience == AudienceType.DOCTOR

    def test_classify_caregiver(self, classifier):
        result = classifier.classify("My mother has been feeling unwell")
        assert result.audience == AudienceType.CAREGIVER

    def test_classify_administrator(self, classifier):
        result = classifier.classify("I need help with an insurance claim")
        assert result.audience == AudienceType.ADMINISTRATOR

    def test_classify_unknown(self, classifier):
        result = classifier.classify("What is diabetes?")
        assert result.audience in (AudienceType.UNKNOWN, AudienceType.PATIENT)

    def test_classify_confidence_range(self, classifier):
        result = classifier.classify("What should I do?")
        assert 0 <= result.confidence <= 1


# ---------------------------------------------------------------------------
# LanguageDetector Tests
# ---------------------------------------------------------------------------

class TestLanguageDetector:
    @pytest.fixture
    def detector(self):
        return LanguageDetector()

    def test_detect_basic_english(self, detector):
        result = detector.detect("What is diabetes?")
        assert result.language == "en"
        assert result.confidence > 0.9

    def test_detect_abbreviations(self, detector):
        result = detector.detect("Patient has HTN and COPD")
        assert result.has_abbreviations is True
        assert "htn" in result.detected_abbreviations or "copd" in result.detected_abbreviations

    def test_detect_informal_phrasing(self, detector):
        result = detector.detect("Gonna take my meds for the doc")
        assert result.has_informal_phrasing is True

    def test_detect_typos(self, detector):
        result = detector.detect("I have a reeeeally bad headache")
        assert result.has_typos is True

    def test_normalized_query(self, detector):
        result = detector.detect("What causes htn?")
        assert result.normalized_query is not None


# ---------------------------------------------------------------------------
# QueryRewriter Tests
# ---------------------------------------------------------------------------

class TestQueryRewriter:
    @pytest.fixture
    def rewriter(self):
        return QueryRewriter()

    @pytest.mark.asyncio
    async def test_rewrite_abbreviations(self, rewriter):
        result = await rewriter.rewrite("What causes SOB in COPD?")
        assert len(result.abbreviations_expanded) >= 1

    @pytest.mark.asyncio
    async def test_rewrite_preserves_original(self, rewriter):
        original = "What is diabetes?"
        result = await rewriter.rewrite(original)
        assert result.original_query == original

    @pytest.mark.asyncio
    async def test_rewrite_no_changes(self, rewriter):
        result = await rewriter.rewrite("What is hypertension?")
        assert result.rewritten_query is not None


# ---------------------------------------------------------------------------
# ContextResolver Tests (memory integration)
# ---------------------------------------------------------------------------

class TestContextResolver:
    @pytest.fixture
    def resolver(self):
        return ContextResolver()

    @pytest.mark.asyncio
    async def test_resolve_non_existent_conversation(self, resolver):
        result = await resolver.resolve("non_existent_id")
        assert result.has_context is False
        assert result.conversation_id == "non_existent_id"

    @pytest.mark.asyncio
    async def test_resolve_empty_id(self, resolver):
        result = await resolver.resolve("")
        assert result.has_context is False


# ---------------------------------------------------------------------------
# MedicalTaxonomyService Tests
# ---------------------------------------------------------------------------

class TestMedicalTaxonomyService:
    @pytest.fixture
    def service(self):
        return MedicalTaxonomyService()

    @pytest.mark.asyncio
    async def test_lookup_returns_empty(self, service):
        result = await service.lookup("diabetes")
        assert result.term == "diabetes"
        assert result.mappings == []
        assert result.total_mappings == 0

    @pytest.mark.asyncio
    async def test_list_systems(self, service):
        systems = await service.list_systems()
        assert TerminologySystem.ICD_10 in systems
        assert TerminologySystem.SNOMED_CT in systems
        assert TerminologySystem.LOINC in systems


# ---------------------------------------------------------------------------
# QueryUnderstandingEngine Tests
# ---------------------------------------------------------------------------

class TestQueryUnderstandingEngine:
    @pytest.fixture
    def engine(self):
        return QueryUnderstandingEngine()

    @pytest.mark.asyncio
    async def test_analyze_full(self, engine):
        result = await engine.analyze("What are the symptoms of diabetes?")
        assert result.original_query == "What are the symptoms of diabetes?"
        assert result.intent is not None
        assert result.specialty is not None
        assert result.urgency is not None
        assert result.audience is not None
        assert result.language is not None
        assert result.rewrite is not None

    @pytest.mark.asyncio
    async def test_detect_intent(self, engine):
        result = await engine.detect_intent("What causes heart disease?")
        assert result.primary_intent.intent_type is not None

    @pytest.mark.asyncio
    async def test_extract_entities(self, engine):
        result = await engine.extract_entities("Patient has diabetes and takes metformin")
        assert result.total > 0

    @pytest.mark.asyncio
    async def test_classify_specialty(self, engine):
        result = await engine.classify_specialty("Heart disease and chest pain")
        assert result.primary_specialty.specialty is not None

    @pytest.mark.asyncio
    async def test_classify_urgency(self, engine):
        result = await engine.classify_urgency("Emergency! Severe chest pain")
        assert result.level == "emergency"

    @pytest.mark.asyncio
    async def test_classify_audience(self, engine):
        result = await engine.classify_audience("What should I do?")
        assert result.audience == AudienceType.PATIENT

    @pytest.mark.asyncio
    async def test_detect_language(self, engine):
        result = await engine.detect_language("What is diabetes?")
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_rewrite_query(self, engine):
        result = await engine.rewrite_query("What causes HTN?")
        assert result.abbreviations_expanded is not None


# ---------------------------------------------------------------------------
# DI Tests
# ---------------------------------------------------------------------------

class TestDependencyInjection:
    def test_get_set_reset(self):
        reset_query_understanding_engine()
        eng = get_query_understanding_engine()
        assert eng is not None

        mock = AsyncMock()
        set_query_understanding_engine(mock)
        assert get_query_understanding_engine() is mock

        reset_query_understanding_engine()
        assert get_query_understanding_engine() is not mock

    def test_singleton_behavior(self):
        reset_query_understanding_engine()
        s1 = get_query_understanding_engine()
        s2 = get_query_understanding_engine()
        assert s1 is s2
        reset_query_understanding_engine()


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

class TestQueryUnderstandingAPI:
    def test_analyze_endpoint(self, client, doctor_token):
        from app.ai.medical.engine.deps import reset_query_understanding_engine, set_query_understanding_engine

        mock_engine = AsyncMock()
        from app.ai.medical.engine.schemas import (
            QueryUnderstandingResult, IntentResult, IntentCandidate,
            SpecialtyResult, SpecialtyCandidate, UrgencyResult,
            AudienceResult, LanguageInfo, RewriteResult, ConversationContext,
        )

        async def mock_analyze(query, conversation_id=None):
            return QueryUnderstandingResult(
                original_query=query,
                intent=IntentResult(
                    primary_intent=IntentCandidate(intent_type="symptom_inquiry", confidence=0.85),
                ),
                specialty=SpecialtyResult(
                    primary_specialty=SpecialtyCandidate(specialty="general_medicine", confidence=0.7),
                ),
                urgency=UrgencyResult(level="routine", is_emergency=False),
                audience=AudienceResult(audience="patient", confidence=0.8),
                language=LanguageInfo(language="en", confidence=0.95),
                rewrite=RewriteResult(original_query=query, rewritten_query=query),
                context=ConversationContext(),
            )
        mock_engine.analyze = mock_analyze
        reset_query_understanding_engine()
        set_query_understanding_engine(mock_engine)

        response = client.post(
            "/ai/medical/analyze",
            json={"query": "What is diabetes?"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "result" in data
        assert "intent" in data["result"]
        assert "specialty" in data["result"]
        assert "urgency" in data["result"]
        assert "audience" in data["result"]
        assert data["result"]["original_query"] == "What is diabetes?"

    def test_analyze_unauthenticated(self, client):
        response = client.post(
            "/ai/medical/analyze",
            json={"query": "What is diabetes?"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_intent_endpoint(self, client, doctor_token):
        from app.ai.medical.engine.deps import reset_query_understanding_engine, set_query_understanding_engine
        mock_engine = AsyncMock()

        async def mock_detect(query):
            from app.ai.medical.engine.schemas import IntentResult, IntentCandidate
            return IntentResult(
                primary_intent=IntentCandidate(intent_type="symptom_inquiry", confidence=0.85),
                candidates=[IntentCandidate(intent_type="symptom_inquiry", confidence=0.85)],
                total_candidates=1,
            )
        mock_engine.detect_intent = mock_detect
        reset_query_understanding_engine()
        set_query_understanding_engine(mock_engine)

        response = client.post(
            "/ai/medical/intent",
            json={"query": "I have a headache"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["primary_intent"]["intent_type"] == "symptom_inquiry"

    def test_entities_endpoint(self, client, doctor_token):
        from app.ai.medical.engine.deps import reset_query_understanding_engine, set_query_understanding_engine
        mock_engine = AsyncMock()

        async def mock_extract(query):
            from app.ai.medical.engine.schemas import EntityResult, MedicalEntity, EntityType
            return EntityResult(
                entities=[MedicalEntity(entity_type=EntityType.SYMPTOM, text="headache", confidence=0.9)],
                total=1,
            )
        mock_engine.extract_entities = mock_extract
        reset_query_understanding_engine()
        set_query_understanding_engine(mock_engine)

        response = client.post(
            "/ai/medical/entities",
            json={"query": "I have a headache"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] > 0

    def test_rewrite_endpoint(self, client, doctor_token):
        from app.ai.medical.engine.deps import reset_query_understanding_engine, set_query_understanding_engine
        mock_engine = AsyncMock()

        async def mock_rewrite(query):
            from app.ai.medical.engine.schemas import RewriteResult
            return RewriteResult(original_query=query, rewritten_query=query)
        mock_engine.rewrite_query = mock_rewrite
        reset_query_understanding_engine()
        set_query_understanding_engine(mock_engine)

        response = client.post(
            "/ai/medical/rewrite",
            json={"query": "What causes HTN?"},
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["original_query"] == "What causes HTN?"

    def test_specialties_endpoint(self, client, doctor_token):
        response = client.get(
            "/ai/medical/specialties",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert any(s["value"] == "cardiology" for s in data)

    def test_intents_endpoint(self, client, doctor_token):
        response = client.get(
            "/ai/medical/intents",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        names = [i["value"] for i in data]
        assert "symptom_inquiry" in names


# ---------------------------------------------------------------------------
# INTENT_CATEGORIES Tests
# ---------------------------------------------------------------------------

class TestIntentCategories:
    def test_all_categories_defined(self):
        assert len(INTENT_CATEGORIES) >= 14
        names = [c.name for c in INTENT_CATEGORIES]
        assert "symptom_inquiry" in names
        assert "disease_information" in names
        assert "medication_information" in names
        assert "emergency" in names
        assert "mental_health" in names

    def test_category_priorities(self):
        emergency = [c for c in INTENT_CATEGORIES if c.name == "emergency"][0]
        assert emergency.priority == 10
        admin = [c for c in INTENT_CATEGORIES if c.name == "administrative"][0]
        assert admin.priority == 4


# ---------------------------------------------------------------------------
# TerminologySystem Tests
# ---------------------------------------------------------------------------

class TestTerminologySystem:
    def test_supported_systems(self):
        assert TerminologySystem.ICD_10.value == "icd_10"
        assert TerminologySystem.ICD_11.value == "icd_11"
        assert TerminologySystem.SNOMED_CT.value == "snomed_ct"
        assert TerminologySystem.LOINC.value == "loinc"
        assert TerminologySystem.RXNORM.value == "rxnorm"
        assert TerminologySystem.ATC.value == "atc"
