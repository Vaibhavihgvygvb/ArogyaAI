from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cache.service import CacheService
from app.core.config import settings
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.doctor import Doctor
from app.models.enums import AppointmentStatus, UserRole
from app.models.medical_record import MedicalRecord
from app.models.medicine import Medicine
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.user import User
from app.models.visit import Visit
from app.schemas.analytics import (
    ActivityTrend,
    AnalyticsSummaryResponse,
    DoctorAnalyticsResponse,
    EntityCount,
    GrowthMetric,
    PatientAnalyticsResponse,
    PlatformAnalyticsResponse,
    SummaryCard,
    SystemAnalyticsResponse,
)
from app.services.doctor_service import DoctorService
from app.services.patient_service import PatientService

_TODAY = date.today()


def _date_filter(model_field, date_from: date | None, date_to: date | None):
    clauses = []
    if date_from:
        clauses.append(model_field >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        clauses.append(model_field <= datetime.combine(date_to, datetime.max.time()))
    return clauses


def _parse_bucket_date(raw: str | None, group_by: str) -> date:
    if raw is None:
        return date.today()
    try:
        if group_by == "day":
            return datetime.strptime(raw, "%Y-%m-%d").date()
        if group_by == "week":
            parts = raw.split("-W")
            year = int(parts[0])
            week = int(parts[1])
            return date.fromisocalendar(year, week)[0]
        if group_by == "month":
            return datetime.strptime(raw, "%Y-%m").date()
    except (ValueError, TypeError):
        pass
    return date.today()


def _date_trunc_sqlite(expr, group_by: str):
    if group_by == "day":
        return func.date(expr)
    if group_by == "week":
        return func.strftime("%Y-%W", expr)
    if group_by == "month":
        return func.strftime("%Y-%m", expr)
    return func.date(expr)


class AnalyticsService:

    # ------------------------------------------------------------------
    #  Platform Analytics
    # ------------------------------------------------------------------

    @staticmethod
    def get_platform_analytics(
        db: Session,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PlatformAnalyticsResponse:
        cache_key = CacheService.build_key(
            CacheService.NAMESPACE_ANALYTICS, "platform",
            str(date_from or ""), str(date_to or ""),
        )
        cached = CacheService.get(cache_key)
        if cached is not None:
            return PlatformAnalyticsResponse.model_validate_json(cached)

        entity_counts = AnalyticsService._entity_counts(db, date_from, date_to)
        daily = AnalyticsService._time_series(db, Appointment, Appointment.created_at, "day", date_from, date_to, label="appointments")
        weekly = AnalyticsService._time_series(db, Appointment, Appointment.created_at, "week", date_from, date_to, label="appointments")
        monthly = AnalyticsService._time_series(db, Appointment, Appointment.created_at, "month", date_from, date_to, label="appointments")
        growth = AnalyticsService._growth_metrics(db, date_from, date_to)

        result = PlatformAnalyticsResponse(
            entity_counts=entity_counts,
            daily_activity=daily,
            weekly_activity=weekly,
            monthly_activity=monthly,
            growth_metrics=growth,
        )
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_ANALYTICS)
        return result

    # ------------------------------------------------------------------
    #  Doctor Analytics
    # ------------------------------------------------------------------

    @staticmethod
    def get_doctor_analytics(
        db: Session,
        user: User,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> DoctorAnalyticsResponse:
        cache_key = CacheService.build_key(
            CacheService.NAMESPACE_ANALYTICS, "doctor", str(user.id),
            str(date_from or ""), str(date_to or ""),
        )
        cached = CacheService.get(cache_key)
        if cached is not None:
            return DoctorAnalyticsResponse.model_validate_json(cached)

        doctor = DoctorService.get_doctor_by_user_id(db, user.id)
        if not doctor:
            return DoctorAnalyticsResponse(doctor_id=0, doctor_name="")

        doctor_id = doctor.id
        base_clauses = _date_filter(Appointment.created_at, date_from, date_to)

        appointments_completed = AnalyticsService._count(
            db, Appointment,
            Appointment.doctor_id == doctor_id,
            Appointment.status == AppointmentStatus.COMPLETED,
            *base_clauses,
        )
        upcoming = AnalyticsService._count(
            db, Appointment,
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date >= _TODAY,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
        )
        patients_treated = AnalyticsService._count_distinct(
            db, Visit, Visit.patient_id,
            Visit.doctor_id == doctor_id,
        )
        visits = AnalyticsService._count(db, Visit, Visit.doctor_id == doctor_id)
        prescriptions = AnalyticsService._count(db, Prescription, Prescription.doctor_id == doctor_id)
        med_records = AnalyticsService._count(db, MedicalRecord, MedicalRecord.doctor_id == doctor_id)

        avg_appts = AnalyticsService._avg_per_day(appointments_completed, date_from, date_to)
        avg_patients = AnalyticsService._avg_per_week(patients_treated, date_from, date_to)

        recent = AnalyticsService._doctor_recent_activity(db, doctor_id, date_from, date_to)

        result = DoctorAnalyticsResponse(
            doctor_id=doctor.id,
            doctor_name=doctor.full_name,
            specialization=doctor.specialization,
            appointments_completed=appointments_completed,
            upcoming_appointments=upcoming,
            patients_treated=patients_treated,
            visits_completed=visits,
            prescriptions_written=prescriptions,
            medical_records_created=med_records,
            avg_appointments_per_day=avg_appts,
            avg_patients_per_week=avg_patients,
            recent_activity=recent,
        )
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_ANALYTICS)
        return result

    # ------------------------------------------------------------------
    #  Patient Analytics
    # ------------------------------------------------------------------

    @staticmethod
    def get_patient_analytics(
        db: Session,
        user: User,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PatientAnalyticsResponse:
        cache_key = CacheService.build_key(
            CacheService.NAMESPACE_ANALYTICS, "patient", str(user.id),
            str(date_from or ""), str(date_to or ""),
        )
        cached = CacheService.get(cache_key)
        if cached is not None:
            return PatientAnalyticsResponse.model_validate_json(cached)

        patient = PatientService.get_patient_by_user_id(db, user.id)
        if not patient:
            return PatientAnalyticsResponse(patient_id=0, patient_name="")

        patient_id = patient.id
        base_clauses = _date_filter(Appointment.created_at, date_from, date_to)

        total_visits = AnalyticsService._count(db, Visit, Visit.patient_id == patient_id)
        total_appts = AnalyticsService._count(db, Appointment, Appointment.patient_id == patient_id)
        completed_appts = AnalyticsService._count(
            db, Appointment,
            Appointment.patient_id == patient_id,
            Appointment.status == AppointmentStatus.COMPLETED,
        )
        cancelled_appts = AnalyticsService._count(
            db, Appointment,
            Appointment.patient_id == patient_id,
            Appointment.status == AppointmentStatus.CANCELLED,
        )
        total_rx = AnalyticsService._count(db, Prescription, Prescription.patient_id == patient_id)
        total_mr = AnalyticsService._count(db, MedicalRecord, MedicalRecord.patient_id == patient_id)
        med_count = AnalyticsService._count(
            db, PrescriptionItem,
            PrescriptionItem.prescription_id == Prescription.id,
        )
        timeline = AnalyticsService._patient_timeline_summary(db, patient_id, date_from, date_to)

        result = PatientAnalyticsResponse(
            patient_id=patient.id,
            patient_name=patient.full_name,
            total_visits=total_visits,
            total_appointments=total_appts,
            completed_appointments=completed_appts,
            cancelled_appointments=cancelled_appts,
            total_prescriptions=total_rx,
            total_medical_records=total_mr,
            medication_count=med_count,
            timeline_summary=timeline,
        )
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_ANALYTICS)
        return result

    # ------------------------------------------------------------------
    #  System Analytics
    # ------------------------------------------------------------------

    @staticmethod
    def get_system_analytics(
        db: Session,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> SystemAnalyticsResponse:
        cache_key = CacheService.build_key(
            CacheService.NAMESPACE_ANALYTICS, "system",
            str(date_from or ""), str(date_to or ""),
        )
        cached = CacheService.get(cache_key)
        if cached is not None:
            return SystemAnalyticsResponse.model_validate_json(cached)

        most_active = AnalyticsService._most_active_doctors(db, limit=10)
        daily_regs = AnalyticsService._time_series(db, User, User.created_at, "day", date_from, date_to, label="registrations")
        monthly_regs = AnalyticsService._time_series(db, User, User.created_at, "month", date_from, date_to, label="registrations")
        util = AnalyticsService._appointment_utilization(db, date_from, date_to)
        rx_trends = AnalyticsService._time_series(db, Prescription, Prescription.created_at, "month", date_from, date_to, label="prescriptions")
        visit_trends = AnalyticsService._time_series(db, Visit, Visit.created_at, "month", date_from, date_to, label="visits")
        notif_trends = AnalyticsService._time_series(db, Notification, Notification.created_at, "month", date_from, date_to, label="notifications")

        result = SystemAnalyticsResponse(
            most_active_doctors=most_active,
            daily_registrations=daily_regs,
            monthly_registrations=monthly_regs,
            appointment_utilization=util,
            prescription_trends=rx_trends,
            visit_trends=visit_trends,
            notification_trends=notif_trends,
        )
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_ANALYTICS)
        return result

    # ------------------------------------------------------------------
    #  Summary
    # ------------------------------------------------------------------

    @staticmethod
    def get_analytics_summary(db: Session) -> AnalyticsSummaryResponse:
        cache_key = CacheService.build_key(CacheService.NAMESPACE_ANALYTICS, "summary")
        cached = CacheService.get(cache_key)
        if cached is not None:
            return AnalyticsSummaryResponse.model_validate_json(cached)

        total_users = AnalyticsService._count(db, User)
        total_doctors = AnalyticsService._count(db, Doctor)
        total_patients = AnalyticsService._count(db, Patient)
        total_visits = AnalyticsService._count(db, Visit)
        total_appts = AnalyticsService._count(db, Appointment)
        total_rx = AnalyticsService._count(db, Prescription)
        total_mr = AnalyticsService._count(db, MedicalRecord)

        result = AnalyticsSummaryResponse(
            summary_cards=[
                SummaryCard(label="Total Users", value=total_users),
                SummaryCard(label="Doctors", value=total_doctors),
                SummaryCard(label="Patients", value=total_patients),
                SummaryCard(label="Visits", value=total_visits),
                SummaryCard(label="Appointments", value=total_appts),
                SummaryCard(label="Prescriptions", value=total_rx),
                SummaryCard(label="Medical Records", value=total_mr),
            ]
        )
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_ANALYTICS)
        return result

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count(db: Session, model, *filters) -> int:
        stmt = select(func.count(model.id))
        for f in filters:
            stmt = stmt.where(f)
        return db.scalar(stmt) or 0

    @staticmethod
    def _count_distinct(db: Session, model, column, *filters) -> int:
        subq = select(column).distinct()
        for f in filters:
            subq = subq.where(f)
        return db.scalar(select(func.count()).select_from(subq.subquery())) or 0

    @staticmethod
    def _entity_counts(
        db: Session,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[EntityCount]:
        models = [
            ("users", User),
            ("doctors", Doctor),
            ("patients", Patient),
            ("appointments", Appointment),
            ("visits", Visit),
            ("prescriptions", Prescription),
            ("prescription_items", PrescriptionItem),
            ("medicines", Medicine),
            ("medical_records", MedicalRecord),
            ("notifications", Notification),
            ("audit_logs", AuditLog),
        ]
        results = []
        for label, model_cls in models:
            clauses = _date_filter(model_cls.created_at, date_from, date_to) if hasattr(model_cls, "created_at") else []
            count = AnalyticsService._count(db, model_cls, *clauses)
            results.append(EntityCount(entity=label, total=count))
        return results

    @staticmethod
    def _time_series(
        db: Session,
        model,
        date_column,
        group_by: str,
        date_from: date | None = None,
        date_to: date | None = None,
        label: str = "activity",
    ) -> list[ActivityTrend]:
        trunc = _date_trunc_sqlite(date_column, group_by)
        stmt = select(trunc, func.count(model.id)).group_by(trunc).order_by(trunc)
        clauses = _date_filter(date_column, date_from, date_to)
        for f in clauses:
            stmt = stmt.where(f)
        rows = db.execute(stmt).all()
        results = []
        for r in rows:
            raw = r[0]
            parsed = _parse_bucket_date(raw, group_by)
            results.append(ActivityTrend(period=group_by, date=parsed, count=r[1]))
        return results

    @staticmethod
    def _growth_metrics(
        db: Session,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[GrowthMetric]:
        cutoff = date.today() - timedelta(days=30) if not date_from else date_from - timedelta(days=30)

        current_users = AnalyticsService._count(db, User)
        prior_users = AnalyticsService._count(
            db, User,
            User.created_at < cutoff,
        ) if not date_from else AnalyticsService._count(
            db, User,
            User.created_at < date_from,
        )
        user_growth = round((current_users - prior_users) / prior_users * 100, 1) if prior_users else 0.0

        current_patients = AnalyticsService._count(db, Patient)
        prior_patients = AnalyticsService._count(
            db, Patient,
            Patient.created_at < cutoff,
        ) if not date_from else AnalyticsService._count(
            db, Patient,
            Patient.created_at < date_from,
        )
        patient_growth = round((current_patients - prior_patients) / prior_patients * 100, 1) if prior_patients else 0.0

        current_doctors = AnalyticsService._count(db, Doctor)
        prior_doctors = AnalyticsService._count(
            db, Doctor,
            Doctor.created_at < cutoff,
        ) if not date_from else AnalyticsService._count(
            db, Doctor,
            Doctor.created_at < date_from,
        )
        doctor_growth = round((current_doctors - prior_doctors) / prior_doctors * 100, 1) if prior_doctors else 0.0

        return [
            GrowthMetric(metric="users", current=current_users, previous=prior_users, growth_pct=user_growth),
            GrowthMetric(metric="doctors", current=current_doctors, previous=prior_doctors, growth_pct=doctor_growth),
            GrowthMetric(metric="patients", current=current_patients, previous=prior_patients, growth_pct=patient_growth),
        ]

    @staticmethod
    def _avg_per_day(total: int, date_from: date | None, date_to: date | None) -> float:
        if not total:
            return 0.0
        start = date_from or _TODAY - timedelta(days=30)
        end = date_to or _TODAY
        days = max((end - start).days, 1)
        return round(total / days, 2)

    @staticmethod
    def _avg_per_week(total: int, date_from: date | None, date_to: date | None) -> float:
        if not total:
            return 0.0
        start = date_from or _TODAY - timedelta(days=30)
        end = date_to or _TODAY
        weeks = max((end - start).days / 7, 1)
        return round(total / weeks, 2)

    @staticmethod
    def _doctor_recent_activity(
        db: Session,
        doctor_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 10,
    ) -> list[ActivityTrend]:
        trunc = func.date(Appointment.appointment_date)
        stmt = select(
            trunc,
            func.count(Appointment.id),
        ).where(
            Appointment.doctor_id == doctor_id,
        )
        for clause in _date_filter(Appointment.appointment_date, date_from, date_to):
            stmt = stmt.where(clause)
        stmt = stmt.group_by(trunc).order_by(trunc.desc()).limit(limit)
        rows = db.execute(stmt).all()
        return [
            ActivityTrend(period="day", date=_parse_bucket_date(r[0], "day"), count=r[1])
            for r in rows
        ]

    @staticmethod
    def _patient_timeline_summary(
        db: Session,
        patient_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 10,
    ) -> list[ActivityTrend]:
        trunc = func.date(Appointment.appointment_date)
        stmt = select(
            trunc,
            func.count(Appointment.id),
        ).where(
            Appointment.patient_id == patient_id,
        )
        for clause in _date_filter(Appointment.appointment_date, date_from, date_to):
            stmt = stmt.where(clause)
        stmt = stmt.group_by(trunc).order_by(trunc.desc()).limit(limit)
        rows = db.execute(stmt).all()
        return [
            ActivityTrend(period="day", date=_parse_bucket_date(r[0], "day"), count=r[1])
            for r in rows
        ]

    @staticmethod
    def _most_active_doctors(db: Session, limit: int = 10) -> list[dict]:
        stmt = (
            select(
                Doctor.id,
                Doctor.full_name,
                Doctor.specialization,
                func.count(Appointment.id).label("total_appointments"),
            )
            .join(Appointment, Appointment.doctor_id == Doctor.id)
            .group_by(Doctor.id)
            .order_by(func.count(Appointment.id).desc())
            .limit(limit)
        )
        rows = db.execute(stmt).all()
        return [
            {
                "doctor_id": r[0],
                "doctor_name": r[1],
                "specialization": r[2],
                "total_appointments": r[3],
            }
            for r in rows
        ]

    @staticmethod
    def _appointment_utilization(
        db: Session,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> float:
        base_clauses = _date_filter(Appointment.created_at, date_from, date_to)
        total = AnalyticsService._count(db, Appointment, *base_clauses)
        if not total:
            return 0.0
        completed = AnalyticsService._count(
            db, Appointment,
            Appointment.status == AppointmentStatus.COMPLETED,
            *base_clauses,
        )
        return round(completed / total * 100, 1)
