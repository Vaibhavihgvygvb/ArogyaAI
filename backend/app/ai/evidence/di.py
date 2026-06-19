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


_verifier: EvidenceVerifierEngine | None = None
_citation_generator: CitationGeneratorEngine | None = None
_citation_formatter: CitationFormatterEngine | None = None
_coverage_analyzer: CoverageAnalyzerEngine | None = None
_source_ranker: SourceRankingEngine | None = None
_conflict_detector: ConflictDetectorEngine | None = None
_confidence_calculator: ConfidenceCalculatorEngine | None = None
_provenance_tracker: ProvenanceTrackerEngine | None = None
_explainability_provider: ExplainabilityProviderEngine | None = None
_pipeline: EvidencePipeline | None = None
_service: EvidenceService | None = None


def get_verifier() -> EvidenceVerifierEngine:
    global _verifier
    if _verifier is None:
        _verifier = EvidenceVerifierEngine()
    return _verifier


def set_verifier(v: EvidenceVerifierEngine) -> None:
    global _verifier
    _verifier = v


def reset_verifier() -> None:
    global _verifier
    _verifier = None


def get_citation_generator() -> CitationGeneratorEngine:
    global _citation_generator
    if _citation_generator is None:
        _citation_generator = CitationGeneratorEngine()
    return _citation_generator


def set_citation_generator(c: CitationGeneratorEngine) -> None:
    global _citation_generator
    _citation_generator = c


def reset_citation_generator() -> None:
    global _citation_generator
    _citation_generator = None


def get_citation_formatter() -> CitationFormatterEngine:
    global _citation_formatter
    if _citation_formatter is None:
        _citation_formatter = CitationFormatterEngine()
    return _citation_formatter


def set_citation_formatter(c: CitationFormatterEngine) -> None:
    global _citation_formatter
    _citation_formatter = c


def reset_citation_formatter() -> None:
    global _citation_formatter
    _citation_formatter = None


def get_coverage_analyzer() -> CoverageAnalyzerEngine:
    global _coverage_analyzer
    if _coverage_analyzer is None:
        _coverage_analyzer = CoverageAnalyzerEngine()
    return _coverage_analyzer


def set_coverage_analyzer(c: CoverageAnalyzerEngine) -> None:
    global _coverage_analyzer
    _coverage_analyzer = c


def reset_coverage_analyzer() -> None:
    global _coverage_analyzer
    _coverage_analyzer = None


def get_source_ranker() -> SourceRankingEngine:
    global _source_ranker
    if _source_ranker is None:
        _source_ranker = SourceRankingEngine()
    return _source_ranker


def set_source_ranker(r: SourceRankingEngine) -> None:
    global _source_ranker
    _source_ranker = r


def reset_source_ranker() -> None:
    global _source_ranker
    _source_ranker = None


def get_conflict_detector() -> ConflictDetectorEngine:
    global _conflict_detector
    if _conflict_detector is None:
        _conflict_detector = ConflictDetectorEngine()
    return _conflict_detector


def set_conflict_detector(c: ConflictDetectorEngine) -> None:
    global _conflict_detector
    _conflict_detector = c


def reset_conflict_detector() -> None:
    global _conflict_detector
    _conflict_detector = None


def get_confidence_calculator() -> ConfidenceCalculatorEngine:
    global _confidence_calculator
    if _confidence_calculator is None:
        _confidence_calculator = ConfidenceCalculatorEngine()
    return _confidence_calculator


def set_confidence_calculator(c: ConfidenceCalculatorEngine) -> None:
    global _confidence_calculator
    _confidence_calculator = c


def reset_confidence_calculator() -> None:
    global _confidence_calculator
    _confidence_calculator = None


def get_provenance_tracker() -> ProvenanceTrackerEngine:
    global _provenance_tracker
    if _provenance_tracker is None:
        _provenance_tracker = ProvenanceTrackerEngine()
    return _provenance_tracker


def set_provenance_tracker(p: ProvenanceTrackerEngine) -> None:
    global _provenance_tracker
    _provenance_tracker = p


def reset_provenance_tracker() -> None:
    global _provenance_tracker
    _provenance_tracker = None


def get_explainability_provider() -> ExplainabilityProviderEngine:
    global _explainability_provider
    if _explainability_provider is None:
        _explainability_provider = ExplainabilityProviderEngine()
    return _explainability_provider


def set_explainability_provider(e: ExplainabilityProviderEngine) -> None:
    global _explainability_provider
    _explainability_provider = e


def reset_explainability_provider() -> None:
    global _explainability_provider
    _explainability_provider = None


def get_pipeline() -> EvidencePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = EvidencePipeline(
            verifier=get_verifier(),
            citation_generator=get_citation_generator(),
            citation_formatter=get_citation_formatter(),
            coverage_analyzer=get_coverage_analyzer(),
            source_ranker=get_source_ranker(),
            conflict_detector=get_conflict_detector(),
            confidence_calculator=get_confidence_calculator(),
            provenance_tracker=get_provenance_tracker(),
            explainability_provider=get_explainability_provider(),
        )
    return _pipeline


def set_pipeline(p: EvidencePipeline) -> None:
    global _pipeline
    _pipeline = p


def reset_pipeline() -> None:
    global _pipeline
    _pipeline = None


def get_evidence_service() -> EvidenceService:
    global _service
    if _service is None:
        _service = EvidenceService(pipeline=get_pipeline())
    return _service


def set_evidence_service(s: EvidenceService) -> None:
    global _service
    _service = s


def reset_evidence_service() -> None:
    global _service
    _service = None


def reset_all() -> None:
    reset_verifier()
    reset_citation_generator()
    reset_citation_formatter()
    reset_coverage_analyzer()
    reset_source_ranker()
    reset_conflict_detector()
    reset_confidence_calculator()
    reset_provenance_tracker()
    reset_explainability_provider()
    reset_pipeline()
    reset_evidence_service()
