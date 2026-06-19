class VectorStoreError(Exception):
    pass


class SearchError(VectorStoreError):
    pass


class IndexError(VectorStoreError):
    pass


class ProviderNotFoundError(VectorStoreError):
    pass


class DimensionMismatchError(VectorStoreError):
    pass


class EmptyVectorError(VectorStoreError):
    pass
