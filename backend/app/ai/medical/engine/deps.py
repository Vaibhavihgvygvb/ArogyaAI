from app.ai.medical.engine.interfaces import QueryUnderstandingEngineABC
from app.ai.medical.engine.services import QueryUnderstandingEngine

_engine: QueryUnderstandingEngineABC | None = None


def get_query_understanding_engine() -> QueryUnderstandingEngineABC:
    global _engine
    if _engine is None:
        _engine = QueryUnderstandingEngine()
    return _engine


def set_query_understanding_engine(engine: QueryUnderstandingEngineABC) -> None:
    global _engine
    _engine = engine


def reset_query_understanding_engine() -> None:
    global _engine
    _engine = None
