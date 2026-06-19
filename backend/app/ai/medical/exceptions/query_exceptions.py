class QueryUnderstandingError(Exception):
    pass


class IntentError(QueryUnderstandingError):
    pass


class RewriteError(QueryUnderstandingError):
    pass


class EntityError(QueryUnderstandingError):
    pass


class SpecialtyError(QueryUnderstandingError):
    pass


class UrgencyError(QueryUnderstandingError):
    pass


class AudienceError(QueryUnderstandingError):
    pass


class LanguageError(QueryUnderstandingError):
    pass


class ContextError(QueryUnderstandingError):
    pass


class TaxonomyError(QueryUnderstandingError):
    pass


class ValidationError(QueryUnderstandingError):
    pass
