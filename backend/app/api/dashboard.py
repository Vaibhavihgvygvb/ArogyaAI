from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.dashboard import DoctorDashboardResponse, PatientDashboardResponse, AdminDashboardResponse
from app.services.dashboard_service import DashboardService
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/doctor",
    response_model=DoctorDashboardResponse,
    summary="Doctor dashboard",
    description="Aggregated dashboard for doctors: profile, appointments, patients, visits, prescriptions, notifications, stats.",
    responses={
        200: {"description": "Doctor dashboard data"},
        403: {"description": "Not a doctor account"},
    },
)
def get_doctor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access the doctor dashboard",
        )
    return DashboardService.get_doctor_dashboard(db, current_user)


@router.get(
    "/patient",
    response_model=PatientDashboardResponse,
    summary="Patient dashboard",
    description="Aggregated dashboard for patients: profile, appointments, visits, prescriptions, medications, notifications, timeline.",
    responses={
        200: {"description": "Patient dashboard data"},
        403: {"description": "Not a patient account"},
    },
)
def get_patient_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can access the patient dashboard",
        )
    return DashboardService.get_patient_dashboard(db, current_user)


@router.get(
    "/admin",
    response_model=AdminDashboardResponse,
    summary="Admin dashboard",
    description="Aggregated platform dashboard for admins: user counts, system stats, growth metrics, recent activity.",
    responses={
        200: {"description": "Admin dashboard data"},
        403: {"description": "Not an admin account"},
    },
)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access the admin dashboard",
        )
    return DashboardService.get_admin_dashboard(db, current_user)
