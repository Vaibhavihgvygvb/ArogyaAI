from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.search import SearchResponse, SearchResultItem, SEARCHABLE_ENTITY_TYPES
from app.services.search_service import SearchService
from app.api.deps import get_current_user

router = APIRouter(tags=["Search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Global search across all entities",
    description="Search across users, doctors, patients, visits, appointments, prescriptions, prescription items, medicines, medical records, notifications, and audit logs. Results are filtered by role and ownership.",
)
def global_search(
    q: str = Query(min_length=1, max_length=200, description="Search query"),
    entity: str | None = Query(default=None, description="Filter to specific entity type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort by created_at"),
    date_from: str | None = Query(default=None, description="ISO datetime filter start"),
    date_to: str | None = Query(default=None, description="ISO datetime filter end"),
    doctor_id: int | None = Query(default=None, description="Filter by doctor ID"),
    patient_id: int | None = Query(default=None, description="Filter by patient ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if entity and entity not in SEARCHABLE_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type. Must be one of: {', '.join(sorted(SEARCHABLE_ENTITY_TYPES))}",
        )

    from datetime import datetime as dt

    try:
        dt_from = dt.fromisoformat(date_from) if date_from else None
        dt_to = dt.fromisoformat(date_to) if date_to else None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}",
        )

    items, total = SearchService.global_search(
        db=db,
        query=q,
        user=current_user,
        entity=entity,
        page=page,
        page_size=page_size,
        sort_order=sort_order,
        date_from=dt_from,
        date_to=dt_to,
        doctor_id=doctor_id,
        patient_id=patient_id,
    )

    return SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        query=q,
    )
