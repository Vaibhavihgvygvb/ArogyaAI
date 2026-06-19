from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ai.embeddings.deps.deps import get_embedding_service
from app.ai.embeddings.exceptions.exceptions import EmbeddingError
from app.ai.embeddings.schemas.schemas import (
    BatchGenerateResponse,
    BatchRequest,
    BatchResponse,
    EmbeddingDetailResponse,
    EmbeddingListResponse,
    EmbeddingProviderType,
    EmbeddingStatus,
    GenerateAllRequest,
    GenerateRequest,
    GenerateResponse,
    PipelineConfig,
    ProviderInfo,
    RebuildRequest,
    ReindexRequest,
)
from app.ai.embeddings.services.services import EmbeddingService
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter(prefix="/ai/embeddings", tags=["Embedding Platform"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate embedding for a single chunk",
)
async def generate_embedding(
    request: GenerateRequest,
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
):
    from app.ai.embeddings.providers.mock import MockEmbeddingProvider

    if not request.document_id or not request.chunk_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_id and chunk_ids are required",
        )
    try:
        provider = MockEmbeddingProvider()
        vector = await service.generate(
            content="test",
            chunk_id=request.chunk_ids[0],
            document_id=request.document_id,
            provider=provider,
        )
        return GenerateResponse(
            embedding_id=vector.id,
            knowledge_id=vector.knowledge_id,
            chunk_id=vector.chunk_id,
            provider=vector.provider,
            model=vector.model,
            dimension=vector.dimension,
            version=vector.version,
            status=vector.status,
        )
    except EmbeddingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/generate-all",
    response_model=BatchGenerateResponse,
    summary="Generate embeddings for all knowledge base chunks",
)
async def generate_all_embeddings(
    request: GenerateAllRequest,
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
):
    from app.ai.embeddings.providers.mock import MockEmbeddingProvider

    try:
        provider = MockEmbeddingProvider()
        batch = await service.generate_batch(
            chunks=[],
            provider=provider,
        )
        return BatchGenerateResponse(
            batch_id=batch.id,
            status=batch.status,
            total_chunks=batch.total_chunks,
            processed_chunks=batch.processed_chunks,
            failed_chunks=batch.failed_chunks,
        )
    except EmbeddingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/batches",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a batch of chunks for embedding generation",
)
async def create_batch(
    request: BatchRequest,
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
):
    from app.ai.embeddings.providers.mock import MockEmbeddingProvider

    try:
        cfg = PipelineConfig(
            batch_size=request.batch_size,
            skip_cache=request.skip_cache,
        )
        provider = MockEmbeddingProvider()
        batch = await service.generate_batch(
            chunks=request.chunks,
            provider=provider,
            config=cfg,
        )
        return BatchResponse(
            batch_id=batch.id,
            status=batch.status,
            total_chunks=batch.total_chunks,
            processed_chunks=batch.processed_chunks,
            failed_chunks=batch.failed_chunks,
        )
    except EmbeddingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=EmbeddingListResponse,
    summary="List all embeddings with optional filters",
)
async def list_embeddings(
    knowledge_id: str | None = Query(None, description="Filter by knowledge document ID"),
    chunk_id: str | None = Query(None, description="Filter by chunk ID"),
    status: str | None = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(get_current_user),
):
    records, total = await service.list_embeddings(
        knowledge_id=knowledge_id,
        chunk_id=chunk_id,
        status=status,
        offset=offset,
        limit=limit,
    )
    return EmbeddingListResponse(embeddings=records, total=total)


@router.get(
    "/{embedding_id}",
    response_model=EmbeddingDetailResponse,
    summary="Get embedding details by ID",
)
async def get_embedding(
    embedding_id: str,
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(get_current_user),
):
    record = await service.get_record(embedding_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Embedding not found")
    return EmbeddingDetailResponse(
        id=record.id,
        knowledge_id=record.knowledge_id,
        chunk_id=record.chunk_id,
        chunk_index=record.chunk_index,
        provider=record.provider,
        model=record.model,
        dimension=record.dimension,
        version=record.version,
        checksum=record.checksum,
        content_hash=record.content_hash,
        status=record.status,
        metadata=record.metadata,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "/rebuild",
    response_model=BatchGenerateResponse,
    summary="Rebuild embeddings (regenerate with cache bypass)",
)
async def rebuild_embeddings(
    request: RebuildRequest,
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
):
    from app.ai.embeddings.providers.mock import MockEmbeddingProvider

    try:
        provider = MockEmbeddingProvider()
        batch = await service.rebuild(
            chunks=[],
            provider=provider,
        )
        return BatchGenerateResponse(
            batch_id=batch.id,
            status=batch.status,
            total_chunks=batch.total_chunks,
            processed_chunks=batch.processed_chunks,
            failed_chunks=batch.failed_chunks,
        )
    except EmbeddingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/reindex",
    response_model=BatchGenerateResponse,
    summary="Reindex existing embeddings (regenerate with new version)",
)
async def reindex_embeddings(
    request: ReindexRequest,
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
):
    from app.ai.embeddings.providers.mock import MockEmbeddingProvider

    try:
        chunks = []
        for eid in request.embedding_ids:
            record = await service.get_record(eid)
            if record is None:
                continue
            vector_data = await service.get_embedding(eid)
            content = "reindex_content"
            if vector_data:
                content = "reindex_content"
            from app.ai.embeddings.schemas.schemas import ChunkReference
            from app.ai.embeddings.utils.utils import compute_content_hash
            chunk = ChunkReference(
                chunk_id=record.chunk_id,
                document_id=record.knowledge_id,
                content=content,
                content_hash=compute_content_hash(content),
                chunk_index=record.chunk_index,
            )
            chunks.append(chunk)

        provider = MockEmbeddingProvider()
        cfg = PipelineConfig(skip_cache=True)
        batch = await service.generate_batch(chunks=chunks, provider=provider, config=cfg)
        return BatchGenerateResponse(
            batch_id=batch.id,
            status=batch.status,
            total_chunks=batch.total_chunks,
            processed_chunks=batch.processed_chunks,
            failed_chunks=batch.failed_chunks,
        )
    except EmbeddingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{embedding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an embedding",
)
async def delete_embedding(
    embedding_id: str,
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR)),
):
    deleted = await service.delete_embedding(embedding_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Embedding not found")


@router.get(
    "/providers",
    response_model=list[ProviderInfo],
    summary="List available embedding providers",
)
async def list_providers(
    service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(get_current_user),
):
    providers = await service.get_providers()
    return [ProviderInfo(**p) for p in providers]
