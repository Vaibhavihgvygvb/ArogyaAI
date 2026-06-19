class RetrievalError(Exception):
    pass


class RetrievalProviderError(RetrievalError):
    pass


class EmbeddingQueryError(RetrievalError):
    pass


class ChunkNotFoundError(RetrievalError):
    pass


class RAGGenerationError(RetrievalError):
    pass


class RerankerError(RetrievalError):
    pass


class ContextWindowExceededError(RetrievalError):
    pass


class InvalidQueryError(RetrievalError):
    pass
