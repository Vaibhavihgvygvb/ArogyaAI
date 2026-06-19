class KnowledgeError(Exception):
    pass


class DocumentNotFoundError(KnowledgeError):
    pass


class DocumentAlreadyExistsError(KnowledgeError):
    pass


class InvalidDocumentError(KnowledgeError):
    pass


class UnsupportedFormatError(InvalidDocumentError):
    pass


class FileSizeExceededError(InvalidDocumentError):
    pass


class EncodingError(InvalidDocumentError):
    pass


class ChecksumMismatchError(InvalidDocumentError):
    pass


class ContentQualityError(InvalidDocumentError):
    pass


class ParseError(KnowledgeError):
    pass


class NormalizationError(KnowledgeError):
    pass


class CleaningError(KnowledgeError):
    pass


class ChunkingError(KnowledgeError):
    pass


class ValidationError(KnowledgeError):
    pass


class StorageError(KnowledgeError):
    pass


class CatalogError(KnowledgeError):
    pass


class PipelineError(KnowledgeError):
    pass
