import time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ai.vector.deps.deps import get_vector_service
from app.ai.vector.exceptions.exceptions import VectorStoreError
from app.ai.vector.schemas.schemas import (
    ClearResponse,
    IndexRequest,
    IndexResponse,
    IndexResult,
    SearchByVectorRequest,
    SearchResponse,
    SearchResult,
    SearchTextRequest,
    VectorDeleteResponse,
    VectorStats,
)
from app.ai.vector.services.services import VectorService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai/vector", tags=["Vector Platform"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search similar vectors by vector",
)
async def search_by_vector(
    request: SearchByVectorRequest,
    service: VectorService = Depends(get_vector_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.search_by_vector(
            query_vector=request.query_vector,
            top_k=request.top_k,
            filters=request.filters,
            include_vectors=request.include_vectors,
        )
    except VectorStoreError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/index",
    response_model=IndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index vectors into the vector store",
)
async def index_vectors(
    request: IndexRequest,
    service: VectorService = Depends(get_vector_service),
    current_user: User = Depends(get_current_user),
):
    from app.ai.embeddings.deps.deps import get_embedding_service

    embedding_service = get_embedding_service()
    records, total = await embedding_service.list_embeddings(
        knowledge_id=request.knowledge_id,
        chunk_id=None,
        status="completed",
        offset=0,
        limit=10000,
    )

    if not records:
        return IndexResponse(
            status="completed",
            result=IndexResult(indexed_count=0, skipped_count=0, errors=[]),
        )

    vectors_to_index = []
    errors = []
    skipped = 0

    for record in records:
        vector_data = await embedding_service.get_embedding(record.id)
        if vector_data is None:
            skipped += 1
            continue
        metadata = {
            "chunk_id": record.chunk_id,
            "knowledge_id": record.knowledge_id,
            "chunk_index": record.chunk_index,
            "provider": record.provider.value,
            "model": record.model,
            "dimension": record.dimension,
            "version": record.version,
            **record.metadata,
        }
        vectors_to_index.append((record.id, vector_data.vector, metadata))

    indexed = await service.index_batch(vectors_to_index)

    return IndexResponse(
        status="completed",
        result=IndexResult(
            indexed_count=len(indexed),
            skipped_count=skipped,
            errors=errors,
        ),
    )


@router.get(
    "/stats",
    response_model=VectorStats,
    summary="Get vector store statistics",
)
async def get_stats(
    service: VectorService = Depends(get_vector_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_stats()


@router.delete(
    "/clear",
    response_model=ClearResponse,
    summary="Clear all vectors from the store",
)
async def clear_vectors(
    service: VectorService = Depends(get_vector_service),
    current_user: User = Depends(get_current_user),
):
    previous_count = await service.clear()
    return ClearResponse(cleared=True, previous_count=previous_count)


@router.delete(
    "/{embedding_id}",
    response_model=VectorDeleteResponse,
    summary="Delete a vector from the store",
)
async def delete_vector(
    embedding_id: str,
    service: VectorService = Depends(get_vector_service),
    current_user: User = Depends(get_current_user),
):
    deleted = await service.delete(embedding_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vector not found")
    return VectorDeleteResponse(deleted=True, embedding_id=embedding_id)
