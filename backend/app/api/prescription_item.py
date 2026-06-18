from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.schemas.prescription_item import (
    PrescriptionItemCreate,
    PrescriptionItemUpdate,
    PrescriptionItemResponse,
)
from app.services.prescription_item_service import (
    PrescriptionItemService,
    PrescriptionItemValidationError,
)
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/prescriptions", tags=["Prescription Items"])


@router.post(
    "/{prescription_id}/items",
    response_model=PrescriptionItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a medicine item to a prescription",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid item data"},
        status.HTTP_403_FORBIDDEN: {"description": "Doctor or Admin access required"},
        status.HTTP_404_NOT_FOUND: {"description": "Prescription not found"},
    },
)
def create_prescription_item(
    prescription_id: int,
    item_data: PrescriptionItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    try:
        return PrescriptionItemService.create_item(db, prescription_id, item_data)
    except PrescriptionItemValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "/{prescription_id}/items",
    response_model=list[PrescriptionItemResponse],
    summary="List items for a prescription",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Prescription not found"},
    },
)
def list_prescription_items(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor_id = None
    patient_id = None
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if doctor:
            doctor_id = doctor.id
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            patient_id = patient.id

    try:
        return PrescriptionItemService.list_items(
            db, prescription_id,
            user_role=current_user.role,
            user_doctor_id=doctor_id,
            user_patient_id=patient_id,
        )
    except PrescriptionItemValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get(
    "/items/{item_id}",
    response_model=PrescriptionItemResponse,
    summary="Get a prescription item by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Item not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def get_prescription_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = PrescriptionItemService.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    prescription = db.get(Prescription, item.prescription_id)
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or prescription.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    elif current_user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or prescription.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return item


@router.patch(
    "/items/{item_id}",
    response_model=PrescriptionItemResponse,
    summary="Update a prescription item",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Item not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def update_prescription_item(
    item_id: int,
    item_update: PrescriptionItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    item = PrescriptionItemService.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    prescription = db.get(Prescription, item.prescription_id)
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or prescription.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        return PrescriptionItemService.update_item(db, item_id, item_update)
    except PrescriptionItemValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prescription item",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Item not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Access denied"},
    },
)
def delete_prescription_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN)),
):
    item = PrescriptionItemService.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    prescription = db.get(Prescription, item.prescription_id)
    if current_user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or prescription.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    PrescriptionItemService.delete_item(db, item_id)
