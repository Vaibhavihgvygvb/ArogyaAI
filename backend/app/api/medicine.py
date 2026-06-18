from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.medicine import MedicineCreate, MedicineUpdate, MedicineResponse
from app.services.medicine_service import MedicineService, MedicineValidationError
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.post(
    "",
    response_model=MedicineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new medicine",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid medicine data"},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
        status.HTTP_409_CONFLICT: {"description": "Duplicate medicine"},
    },
)
def create_medicine(
    medicine_data: MedicineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    try:
        return MedicineService.create_medicine(db, medicine_data)
    except MedicineValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "",
    response_model=list[MedicineResponse],
    summary="List medicines",
    description="Supports filtering by generic_name, manufacturer, drug_class, dosage_form, route, and is_active.",
)
def list_medicines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    generic_name: str | None = Query(None),
    manufacturer: str | None = Query(None),
    drug_class: str | None = Query(None),
    dosage_form: str | None = Query(None),
    route: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MedicineService.list_medicines(
        db,
        skip=skip,
        limit=limit,
        generic_name=generic_name,
        manufacturer=manufacturer,
        drug_class=drug_class,
        dosage_form=dosage_form,
        route=route,
        is_active=is_active,
    )


@router.get(
    "/search",
    response_model=list[MedicineResponse],
    summary="Search medicines",
    description="Case-insensitive partial search on generic_name and brand_name.",
)
def search_medicines(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MedicineService.search_medicines(db, q=q, skip=skip, limit=limit)


@router.get(
    "/{medicine_id}",
    response_model=MedicineResponse,
    summary="Get a medicine by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Medicine not found"},
    },
)
def get_medicine(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    medicine = MedicineService.get_medicine(db, medicine_id)
    if not medicine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
    return medicine


@router.patch(
    "/{medicine_id}",
    response_model=MedicineResponse,
    summary="Update a medicine",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Medicine not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Cannot update inactive medicine"},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
        status.HTTP_409_CONFLICT: {"description": "Duplicate medicine"},
    },
)
def update_medicine(
    medicine_id: int,
    medicine_update: MedicineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    medicine = MedicineService.get_medicine(db, medicine_id)
    if not medicine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
    try:
        return MedicineService.update_medicine(db, medicine_id, medicine_update)
    except MedicineValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.delete(
    "/{medicine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a medicine",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Medicine not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
    },
)
def delete_medicine(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    medicine = MedicineService.get_medicine(db, medicine_id)
    if not medicine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
    MedicineService.delete_medicine(db, medicine_id)
