from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.ai.knowledge.schemas.schemas import (
    ChunkingStrategy,
    DeleteResponse,
    DocumentFormat,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
    DocumentVersionsResponse,
    ImportRequest,
    ImportResponse,
)
from app.ai.knowledge.services.deps import get_knowledge_service
from app.ai.knowledge.services.services import KnowledgeService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai/knowledge", tags=["Knowledge Platform"])


@router.post(
    "/import",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import a document into the knowledge base",
)
async def import_document(
    file: UploadFile = File(...),
    chunk_size: int | None = Query(None, description="Chunk size in characters"),
    chunk_overlap: int | None = Query(None, description="Chunk overlap in characters"),
    chunking_strategy: ChunkingStrategy | None = Query(None, description="Chunking strategy"),
    service: KnowledgeService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    config = ImportRequest(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunking_strategy=chunking_strategy,
    )
    result = await service.import_document(file.file, file.filename or "unknown", config)
    if result.status == DocumentStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or "Import failed",
        )
    return ImportResponse(
        document_id=result.document_id,
        filename=result.filename,
        format=result.format,
        status=result.status,
        chunk_count=result.chunk_count,
        message=f"Document imported successfully with {result.chunk_count} chunks",
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all documents in the knowledge base",
)
async def list_documents(
    status_filter: DocumentStatus | None = Query(None, alias="status"),
    format_filter: str | None = Query(None, alias="format"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: KnowledgeService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    entries, total = await service.list_documents(
        status=status_filter,
        format=format_filter,
        offset=offset,
        limit=limit,
    )
    return DocumentListResponse(documents=entries, total=total)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document by ID",
)
async def get_document(
    document_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    doc = await service.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        format=doc.format,
        size_bytes=doc.size_bytes,
        checksum=doc.checksum,
        status=doc.status,
        version=doc.version,
        metadata=doc.metadata,
        chunks=doc.chunks,
        error=doc.error,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteResponse,
    summary="Delete a document from the knowledge base",
)
async def delete_document(
    document_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    deleted = await service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DeleteResponse(deleted=True, document_id=document_id)


@router.get(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionsResponse,
    summary="Get version history for a document",
)
async def get_document_versions(
    document_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    try:
        versions = await service.get_document_versions(document_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentVersionsResponse(
        document_id=document_id,
        filename="",
        versions=versions,
    )


@router.get(
    "/stats",
    summary="Get knowledge base statistics",
)
async def get_stats(
    service: KnowledgeService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    entries, total = await service.list_documents(limit=1000)
    formats: dict[str, int] = {}
    statuses: dict[str, int] = {}
    total_chunks = 0
    for entry in entries:
        formats[entry.format] = formats.get(entry.format, 0) + 1
        statuses[entry.status] = statuses.get(entry.status, 0) + 1
    return {
        "total_documents": total,
        "formats": formats,
        "statuses": statuses,
    }
