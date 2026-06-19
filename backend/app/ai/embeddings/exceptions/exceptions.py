class EmbeddingError(Exception):
    pass


class ProviderError(EmbeddingError):
    pass


class DimensionMismatchError(EmbeddingError):
    pass


class EmptyChunkError(EmbeddingError):
    pass


class OversizedChunkError(EmbeddingError):
    pass


class ChecksumMismatchError(EmbeddingError):
    pass


class DuplicateEmbeddingError(EmbeddingError):
    pass


class VersionMismatchError(EmbeddingError):
    pass


class InvalidMetadataError(EmbeddingError):
    pass


class StorageError(EmbeddingError):
    pass


class CacheError(EmbeddingError):
    pass


class PipelineError(EmbeddingError):
    pass


class BatchError(EmbeddingError):
    pass


class DocumentNotFoundError(EmbeddingError):
    pass


class ChunkNotFoundError(EmbeddingError):
    pass
