from app.ai.evidence.config import EvidenceConfig


class TestEvidenceConfig:
    def test_default_values(self):
        cfg = EvidenceConfig()
        assert cfg.EVIDENCE_ENABLED is True
        assert cfg.EVIDENCE_MIN_CONFIDENCE_THRESHOLD == 0.5
        assert cfg.EVIDENCE_CITATION_REQUIRED is True
        assert cfg.EVIDENCE_DEFAULT_STYLE == "ama"
        assert cfg.EVIDENCE_MAX_SPANS == 50
        assert cfg.EVIDENCE_MAX_CITATIONS == 100
        assert cfg.EVIDENCE_MAX_SOURCES == 50
        assert cfg.EVIDENCE_COVERAGE_MIN_SCORE == 0.3
        assert cfg.EVIDENCE_CONFLICT_THRESHOLD == 0.15
        assert cfg.EVIDENCE_PROVENANCE_ENABLED is True
        assert cfg.EVIDENCE_EXPLANATION_ENABLED is True
        assert cfg.EVIDENCE_SUITABLE_FOR_AI_THRESHOLD == 0.4

    def test_override_via_constructor(self):
        cfg = EvidenceConfig(
            EVIDENCE_ENABLED=False,
            EVIDENCE_MIN_CONFIDENCE_THRESHOLD=0.8,
            EVIDENCE_CITATION_REQUIRED=False,
            EVIDENCE_DEFAULT_STYLE="vancouver",
            EVIDENCE_MAX_SPANS=100,
            EVIDENCE_MAX_CITATIONS=200,
            EVIDENCE_MAX_SOURCES=10,
            EVIDENCE_COVERAGE_MIN_SCORE=0.5,
            EVIDENCE_CONFLICT_THRESHOLD=0.3,
            EVIDENCE_PROVENANCE_ENABLED=False,
            EVIDENCE_EXPLANATION_ENABLED=False,
            EVIDENCE_SUITABLE_FOR_AI_THRESHOLD=0.7,
        )
        assert cfg.EVIDENCE_ENABLED is False
        assert cfg.EVIDENCE_MIN_CONFIDENCE_THRESHOLD == 0.8
        assert cfg.EVIDENCE_CITATION_REQUIRED is False
        assert cfg.EVIDENCE_DEFAULT_STYLE == "vancouver"
        assert cfg.EVIDENCE_MAX_SPANS == 100
        assert cfg.EVIDENCE_MAX_CITATIONS == 200
        assert cfg.EVIDENCE_MAX_SOURCES == 10
        assert cfg.EVIDENCE_COVERAGE_MIN_SCORE == 0.5
        assert cfg.EVIDENCE_CONFLICT_THRESHOLD == 0.3
        assert cfg.EVIDENCE_PROVENANCE_ENABLED is False
        assert cfg.EVIDENCE_EXPLANATION_ENABLED is False
        assert cfg.EVIDENCE_SUITABLE_FOR_AI_THRESHOLD == 0.7

    def test_type_correctness(self):
        cfg = EvidenceConfig()
        assert isinstance(cfg.EVIDENCE_ENABLED, bool)
        assert isinstance(cfg.EVIDENCE_MIN_CONFIDENCE_THRESHOLD, float)
        assert isinstance(cfg.EVIDENCE_CITATION_REQUIRED, bool)
        assert isinstance(cfg.EVIDENCE_DEFAULT_STYLE, str)
        assert isinstance(cfg.EVIDENCE_MAX_SPANS, int)
        assert isinstance(cfg.EVIDENCE_MAX_CITATIONS, int)
        assert isinstance(cfg.EVIDENCE_MAX_SOURCES, int)
        assert isinstance(cfg.EVIDENCE_COVERAGE_MIN_SCORE, float)
        assert isinstance(cfg.EVIDENCE_CONFLICT_THRESHOLD, float)
        assert isinstance(cfg.EVIDENCE_PROVENANCE_ENABLED, bool)
        assert isinstance(cfg.EVIDENCE_EXPLANATION_ENABLED, bool)
        assert isinstance(cfg.EVIDENCE_SUITABLE_FOR_AI_THRESHOLD, float)

    def test_partial_override(self):
        cfg = EvidenceConfig(EVIDENCE_ENABLED=False)
        assert cfg.EVIDENCE_ENABLED is False
        assert cfg.EVIDENCE_MIN_CONFIDENCE_THRESHOLD == 0.5
        assert cfg.EVIDENCE_DEFAULT_STYLE == "ama"
        assert cfg.EVIDENCE_MAX_SPANS == 50
