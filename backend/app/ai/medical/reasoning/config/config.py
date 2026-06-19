from pydantic_settings import BaseSettings


class ReasoningSettings(BaseSettings):
    REASONING_ENABLED: bool = True
    REASONING_DEFAULT_APPROACH: str = "evidence_synthesis"
    REASONING_MAX_RETRIEVAL_QUERIES: int = 5
    REASONING_DEFAULT_TOP_K: int = 15
    REASONING_MAX_CONTEXT_TOKENS: int = 4096
    REASONING_COMPRESSION_ENABLED: bool = True
    REASONING_DEFAULT_COMPRESSION_STRATEGY: str = "extractive"
    REASONING_CITATION_REQUIRED: bool = True
    REASONING_MIN_CONFIDENCE: float = 0.3
    REASONING_SAFETY_ENABLED: bool = True
    REASONING_PARALLEL_RETRIEVAL: bool = True
    REASONING_DIVERSITY_WEIGHT: float = 0.3
    REASONING_MAX_CHUNKS_PER_QUERY: int = 10
    REASONING_MERGE_STRATEGY: str = "score_weighted"

    @property
    def supported_approaches(self) -> list[str]:
        return [
            "clinical_reasoning",
            "evidence_synthesis",
            "comparative_analysis",
            "differential_diagnosis",
            "treatment_planning",
            "risk_assessment",
            "contextual_information",
            "general_answer",
        ]

    @property
    def compression_strategies(self) -> list[str]:
        return ["none", "extractive", "abstractive", "hybrid"]

    @property
    def merge_strategies(self) -> list[str]:
        return ["round_robin", "score_weighted", "max"]
