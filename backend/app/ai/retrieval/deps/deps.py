from app.ai.embeddings.deps.deps import get_embedding_service
from app.ai.knowledge.services.deps import get_knowledge_service
from app.ai.retrieval.rerankers.rerankers import MockReranker
from app.ai.retrieval.services.services import RetrievalService
from app.ai.vector.deps.deps import get_vector_service

_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService(
            embedding_service=get_embedding_service(),
            vector_service=get_vector_service(),
            knowledge_service=get_knowledge_service(),
            reranker=MockReranker(),
        )
    return _retrieval_service


def set_retrieval_service(service: RetrievalService) -> None:
    global _retrieval_service
    _retrieval_service = service


def reset_retrieval_service() -> None:
    global _retrieval_service
    _retrieval_service = None
