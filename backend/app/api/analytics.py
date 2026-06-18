from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    DoctorAnalyticsResponse,
    PatientAnalyticsResponse,
    PlatformAnalyticsResponse,
    SystemAnalyticsResponse,
)
from app.api.deps import get_current_user, require_roles
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/platform",
    response_model=PlatformAnalyticsResponse,
    summary="Platform analytics",
    description="Aggregated platform-wide entity counts, activity trends, and growth metrics. Admin only.",
    responses={
        200: {"description": "Platform analytics data"},
        403: {"description": "Admin access required"},
    },
)
def get_platform_analytics(
    date_from: date | None = Query(None, description="Filter start date (inclusive)"),
    date_to: date | None = Query(None, description="Filter end date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return AnalyticsService.get_platform_analytics(db, date_from, date_to)


@router.get(
    "/doctor",
    response_model=DoctorAnalyticsResponse,
    summary="Doctor analytics",
    description="Personal analytics for the authenticated doctor: KPIs, averages, recent activity.",
    responses={
        200: {"description": "Doctor analytics data"},
        403: {"description": "Doctor access required"},
    },
)
def get_doctor_analytics(
    date_from: date | None = Query(None, description="Filter start date (inclusive)"),
    date_to: date | None = Query(None, description="Filter end date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
):
    return AnalyticsService.get_doctor_analytics(db, current_user, date_from, date_to)


@router.get(
    "/patient",
    response_model=PatientAnalyticsResponse,
    summary="Patient analytics",
    description="Personal analytics for the authenticated patient: clinical summary, timeline.",
    responses={
        200: {"description": "Patient analytics data"},
        403: {"description": "Patient access required"},
    },
)
def get_patient_analytics(
    date_from: date | None = Query(None, description="Filter start date (inclusive)"),
    date_to: date | None = Query(None, description="Filter end date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PATIENT)),
):
    return AnalyticsService.get_patient_analytics(db, current_user, date_from, date_to)


@router.get(
    "/system",
    response_model=SystemAnalyticsResponse,
    summary="System analytics",
    description="System-wide analytics: most active doctors, registration trends, utilization rates. Admin only.",
    responses={
        200: {"description": "System analytics data"},
        403: {"description": "Admin access required"},
    },
)
def get_system_analytics(
    date_from: date | None = Query(None, description="Filter start date (inclusive)"),
    date_to: date | None = Query(None, description="Filter end date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return AnalyticsService.get_system_analytics(db, date_from, date_to)


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Analytics summary",
    description="High-level summary cards with total counts across all entities. Admin only.",
    responses={
        200: {"description": "Analytics summary cards"},
        403: {"description": "Admin access required"},
    },
)
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return AnalyticsService.get_analytics_summary(db)
