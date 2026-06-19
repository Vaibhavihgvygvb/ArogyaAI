import pytest

from app.ai.evidence.di import (
    reset_all,
    reset_citation_formatter,
    reset_citation_generator,
    reset_confidence_calculator,
    reset_conflict_detector,
    reset_coverage_analyzer,
    reset_evidence_service,
    reset_explainability_provider,
    reset_pipeline,
    reset_provenance_tracker,
    reset_source_ranker,
    reset_verifier,
    get_citation_formatter,
    get_citation_generator,
    get_confidence_calculator,
    get_conflict_detector,
    get_coverage_analyzer,
    get_evidence_service,
    get_explainability_provider,
    get_pipeline,
    get_provenance_tracker,
    get_source_ranker,
    get_verifier,
    set_citation_formatter,
    set_citation_generator,
    set_confidence_calculator,
    set_conflict_detector,
    set_coverage_analyzer,
    set_evidence_service,
    set_explainability_provider,
    set_pipeline,
    set_provenance_tracker,
    set_source_ranker,
    set_verifier,
)
from app.ai.evidence.engines.citation import CitationFormatterEngine, CitationGeneratorEngine
from app.ai.evidence.engines.confidence import ConfidenceCalculatorEngine
from app.ai.evidence.engines.conflict import ConflictDetectorEngine
from app.ai.evidence.engines.coverage import CoverageAnalyzerEngine
from app.ai.evidence.engines.explain import ExplainabilityProviderEngine
from app.ai.evidence.engines.provenance import ProvenanceTrackerEngine
from app.ai.evidence.engines.ranking import SourceRankingEngine
from app.ai.evidence.engines.verifier import EvidenceVerifierEngine
from app.ai.evidence.pipeline import EvidencePipeline
from app.ai.evidence.service import EvidenceService


@pytest.fixture(autouse=True)
def cleanup():
    reset_all()
    yield
    reset_all()


class TestEvidenceDI:
    def _check_get_set_reset(self, getter, setter, resetter, engine_cls):
        instance1 = getter()
        assert isinstance(instance1, engine_cls)

        custom = engine_cls()
        setter(custom)
        instance2 = getter()
        assert instance2 is custom

        resetter()
        instance3 = getter()
        assert isinstance(instance3, engine_cls)
        assert instance3 is not custom

    def test_get_verifier_returns_default(self):
        instance = get_verifier()
        assert isinstance(instance, EvidenceVerifierEngine)

    def test_set_verifier_stores_custom(self):
        custom = EvidenceVerifierEngine()
        set_verifier(custom)
        assert get_verifier() is custom

    def test_get_verifier_returns_custom_after_set(self):
        custom = EvidenceVerifierEngine()
        set_verifier(custom)
        assert get_verifier() is custom

    def test_reset_verifier_clears(self):
        set_verifier(EvidenceVerifierEngine())
        reset_verifier()
        assert isinstance(get_verifier(), EvidenceVerifierEngine)

    def test_verifier_singleton(self):
        a = get_verifier()
        b = get_verifier()
        assert a is b

    def test_get_citation_generator_returns_default(self):
        assert isinstance(get_citation_generator(), CitationGeneratorEngine)

    def test_set_citation_generator_stores_custom(self):
        custom = CitationGeneratorEngine()
        set_citation_generator(custom)
        assert get_citation_generator() is custom

    def test_reset_citation_generator_clears(self):
        set_citation_generator(CitationGeneratorEngine())
        reset_citation_generator()
        assert isinstance(get_citation_generator(), CitationGeneratorEngine)

    def test_get_citation_formatter_returns_default(self):
        assert isinstance(get_citation_formatter(), CitationFormatterEngine)

    def test_set_citation_formatter_stores_custom(self):
        custom = CitationFormatterEngine()
        set_citation_formatter(custom)
        assert get_citation_formatter() is custom

    def test_reset_citation_formatter_clears(self):
        set_citation_formatter(CitationFormatterEngine())
        reset_citation_formatter()
        assert isinstance(get_citation_formatter(), CitationFormatterEngine)

    def test_get_coverage_analyzer_returns_default(self):
        assert isinstance(get_coverage_analyzer(), CoverageAnalyzerEngine)

    def test_get_source_ranker_returns_default(self):
        assert isinstance(get_source_ranker(), SourceRankingEngine)

    def test_get_conflict_detector_returns_default(self):
        assert isinstance(get_conflict_detector(), ConflictDetectorEngine)

    def test_get_confidence_calculator_returns_default(self):
        assert isinstance(get_confidence_calculator(), ConfidenceCalculatorEngine)

    def test_get_provenance_tracker_returns_default(self):
        assert isinstance(get_provenance_tracker(), ProvenanceTrackerEngine)

    def test_get_explainability_provider_returns_default(self):
        assert isinstance(get_explainability_provider(), ExplainabilityProviderEngine)

    def test_get_pipeline_returns_default(self):
        assert isinstance(get_pipeline(), EvidencePipeline)

    def test_set_pipeline_stores_custom(self):
        custom = EvidencePipeline()
        set_pipeline(custom)
        assert get_pipeline() is custom

    def test_reset_pipeline_clears(self):
        set_pipeline(EvidencePipeline())
        reset_pipeline()
        assert isinstance(get_pipeline(), EvidencePipeline)

    def test_get_evidence_service_returns_default(self):
        assert isinstance(get_evidence_service(), EvidenceService)

    def test_set_evidence_service_stores_custom(self):
        custom = EvidenceService()
        set_evidence_service(custom)
        assert get_evidence_service() is custom

    def test_reset_evidence_service_clears(self):
        set_evidence_service(EvidenceService())
        reset_evidence_service()
        assert isinstance(get_evidence_service(), EvidenceService)

    def test_reset_all_clears_everything(self):
        set_verifier(EvidenceVerifierEngine())
        set_citation_generator(CitationGeneratorEngine())
        set_citation_formatter(CitationFormatterEngine())
        set_coverage_analyzer(CoverageAnalyzerEngine())
        set_source_ranker(SourceRankingEngine())
        set_conflict_detector(ConflictDetectorEngine())
        set_confidence_calculator(ConfidenceCalculatorEngine())
        set_provenance_tracker(ProvenanceTrackerEngine())
        set_explainability_provider(ExplainabilityProviderEngine())
        set_pipeline(EvidencePipeline())
        set_evidence_service(EvidenceService())

        reset_all()

        assert isinstance(get_verifier(), EvidenceVerifierEngine)
        assert isinstance(get_citation_generator(), CitationGeneratorEngine)
        assert isinstance(get_citation_formatter(), CitationFormatterEngine)
        assert isinstance(get_coverage_analyzer(), CoverageAnalyzerEngine)
        assert isinstance(get_source_ranker(), SourceRankingEngine)
        assert isinstance(get_conflict_detector(), ConflictDetectorEngine)
        assert isinstance(get_confidence_calculator(), ConfidenceCalculatorEngine)
        assert isinstance(get_provenance_tracker(), ProvenanceTrackerEngine)
        assert isinstance(get_explainability_provider(), ExplainabilityProviderEngine)
        assert isinstance(get_pipeline(), EvidencePipeline)
        assert isinstance(get_evidence_service(), EvidenceService)

    def test_pipeline_singleton(self):
        a = get_pipeline()
        b = get_pipeline()
        assert a is b

    def test_service_defaults_use_default_pipeline(self):
        service = get_evidence_service()
        assert isinstance(service._pipeline, EvidencePipeline)
        assert isinstance(service._config, type(service._config))

    def test_set_custom_engine_affects_new_pipeline(self):
        custom = EvidenceVerifierEngine()
        set_verifier(custom)
        reset_pipeline()
        pipeline = get_pipeline()
        assert pipeline._verifier is custom

    def test_get_evidence_service_returns_same_instance(self):
        a = get_evidence_service()
        b = get_evidence_service()
        assert a is b
