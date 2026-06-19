from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    ACTIVE_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_KEEP_ALIVE: str = "5m"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = ""
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_MODEL: str = ""
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 0.9
    DEFAULT_MAX_TOKENS: int = 2048
    DEFAULT_CONTEXT_WINDOW: int = 4096
    DEFAULT_TIMEOUT_SECONDS: int = 60
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_SECONDS: float = 1.0
    STREAMING_ENABLED: bool = True
    EMBEDDING_MODEL: str = ""
    SAFETY_LEVEL: str = "standard"
    SAFETY_ENABLED: bool = True
    MEMORY_ENABLED: bool = True
    MEMORY_MAX_TOKENS: int = 4096
    PROMPT_CACHE_ENABLED: bool = True
    GATEWAY_TIMEOUT_SECONDS: int = 120
    ENABLED_PROVIDERS: str = "ollama,openai"

    KNOWLEDGE_ENABLED: bool = True
    KNOWLEDGE_STORAGE_PATH: str = "data/knowledge/documents"
    KNOWLEDGE_CATALOG_PATH: str = "data/knowledge/catalog.json"
    KNOWLEDGE_MAX_FILE_SIZE_MB: int = 10
    KNOWLEDGE_DEFAULT_CHUNK_SIZE: int = 500
    KNOWLEDGE_DEFAULT_CHUNK_OVERLAP: int = 50

    EMBEDDING_ENABLED: bool = True
    EMBEDDING_DEFAULT_PROVIDER: str = "mock"
    EMBEDDING_DEFAULT_MODEL: str = "mock-embedding-v1"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 50
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_RETRY_DELAY_MS: int = 100
    EMBEDDING_STORAGE_PATH: str = "data/knowledge/embeddings"
    EMBEDDING_CACHE_ENABLED: bool = True
    EMBEDDING_VALIDATE_VECTORS: bool = True
    EMBEDDING_MAX_CHUNK_CHARS: int = 16384

    VECTOR_ENABLED: bool = True
    VECTOR_DEFAULT_PROVIDER: str = "memory"
    VECTOR_STORE_PATH: str = "data/vectors"
    VECTOR_COLLECTION_NAME: str = "arogyaai_vectors"
    VECTOR_DEFAULT_TOP_K: int = 10
    VECTOR_MAX_TOP_K: int = 200

    RETRIEVAL_ENABLED: bool = True
    RETRIEVAL_DEFAULT_TOP_K: int = 10
    RETRIEVAL_MAX_TOP_K: int = 100
    RETRIEVAL_DEFAULT_RERANKER: str = "mock"
    RETRIEVAL_MAX_CONTEXT_TOKENS: int = 2048
    RETRIEVAL_ALLOW_RAG: bool = True

    MEDICAL_ENABLED: bool = True
    MEDICAL_DEFAULT_SPECIALTY: str = "general_medicine"
    MEDICAL_DEFAULT_TOP_K: int = 10
    MEDICAL_MAX_CONTEXT_TOKENS: int = 4096
    MEDICAL_MIN_CONFIDENCE_THRESHOLD: float = 0.3
    MEDICAL_REWRITE_ENABLED: bool = True
    MEDICAL_SAFETY_ENABLED: bool = True
    MEDICAL_CITATIONS_REQUIRED: bool = True
    MEDICAL_REASONING_ENABLED: bool = True
