from datetime import date, datetime, timezone

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.medical_record import MedicalRecord
from app.models.medicine import Medicine
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.schemas.dashboard import (
    DoctorDashboardResponse,
    PatientDashboardResponse,
    AdminDashboardResponse,
    StatCard,
    RecentAppointment,
    RecentVisit,
    RecentPrescription,
    NotificationSummary,
    TimelineEvent,
    ActiveMedication,
    PlatformActivity,
    RegistrationSummary,
)
from app.services.doctor_service import DoctorService
from app.services.patient_service import PatientService
from app.services.user_service import UserService

_APPOINTMENT_UPCOMING_STATUSES = {
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.CHECKED_IN,
    AppointmentStatus.IN_PROGRESS,
}
_TODAY = date.today()


class DashboardService:

    # ------------------------------------------------------------------
    #  Doctor Dashboard
    # ------------------------------------------------------------------

    @staticmethod
    def get_doctor_dashboard(db: Session, user: User) -> DoctorDashboardResponse:
        doctor = DoctorService.get_doctor_by_user_id(db, user.id)
        if not doctor:
            return DoctorDashboardResponse()

        doctor_id = doctor.id
        doctor_profile = {
            "id": doctor.id,
            "full_name": doctor.full_name,
            "email": doctor.email,
            "phone_number": doctor.phone_number,
            "specialization": doctor.specialization,
            "clinic_name": doctor.clinic_name,
        }

        today_appts = DashboardService._get_todays_appointments(db, doctor_id)
        upcoming_appts = DashboardService._get_upcoming_appointments(db, doctor_id)
        completed_count = DashboardService._count_completed_appointments(db, doctor_id)
        pending_count = DashboardService._count_pending_appointments(db, doctor_id)
        total_patients = DashboardService._count_doctor_patients(db, doctor_id)

        recent_visits = DashboardService._get_doctor_recent_visits(db, doctor_id, limit=5)
        recent_prescriptions = DashboardService._get_doctor_recent_prescriptions(db, doctor_id, limit=5)

        notifications = DashboardService._get_user_notifications(db, user.id, limit=5)

        mr_stats = DashboardService._get_doctor_medical_record_stats(db, doctor_id)

        summary_cards = [
            StatCard(label="Total Patients", value=total_patients,
                     trend=f"{total_patients} unique"),
            StatCard(label="Today's Appointments", value=len(today_appts)),
            StatCard(label="Pending", value=pending_count),
            StatCard(label="Completed", value=completed_count),
        ]

        return DoctorDashboardResponse(
            profile=doctor_profile,
            todays_appointments=today_appts,
            upcoming_appointments=upcoming_appts,
            completed_appointments=completed_count,
            pending_appointments=pending_count,
            total_patients=total_patients,
            recent_visits=recent_visits,
            recent_prescriptions=recent_prescriptions,
            notifications=notifications,
            medical_record_stats=mr_stats,
            summary_cards=summary_cards,
        )

    # ------------------------------------------------------------------
    #  Patient Dashboard
    # ------------------------------------------------------------------

    @staticmethod
    def get_patient_dashboard(db: Session, user: User) -> PatientDashboardResponse:
        patient = PatientService.get_patient_by_user_id(db, user.id)
        if not patient:
            return PatientDashboardResponse()

        patient_id = patient.id
        patient_profile = {
            "id": patient.id,
            "full_name": patient.full_name,
            "phone_number": patient.phone_number,
            "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
            "gender": patient.gender,
            "emergency_contact": patient.emergency_contact,
        }

        upcoming_appts = DashboardService._get_patient_upcoming_appointments(db, patient_id)

        visit_count = DashboardService._count_entity(db, Visit, Visit.patient_id == patient_id)
        rx_count = DashboardService._count_entity(db, Prescription, Prescription.patient_id == patient_id)
        mr_count = DashboardService._count_entity(db, MedicalRecord, MedicalRecord.patient_id == patient_id)

        medical_history_summary = {
            "total_visits": visit_count,
            "total_prescriptions": rx_count,
            "total_medical_records": mr_count,
        }

        recent_prescriptions = DashboardService._get_patient_recent_prescriptions(db, patient_id, limit=5)
        active_meds = DashboardService._get_active_medications(db, patient_id)
        recent_visits = DashboardService._get_patient_recent_visits(db, patient_id, limit=5)
        notifications = DashboardService._get_user_notifications(db, user.id, limit=5)
        timeline = DashboardService._get_patient_timeline(db, patient_id, limit=5)

        health_cards = [
            StatCard(label="Total Visits", value=visit_count),
            StatCard(label="Prescriptions", value=rx_count),
            StatCard(label="Medical Records", value=mr_count),
            StatCard(label="Upcoming Appointments", value=len(upcoming_appts)),
        ]

        return PatientDashboardResponse(
            profile=patient_profile,
            upcoming_appointments=upcoming_appts,
            medical_history_summary=medical_history_summary,
            prescriptions=recent_prescriptions,
            active_medications=active_meds,
            recent_visits=recent_visits,
            notifications=notifications,
            timeline_preview=timeline,
            health_summary_cards=health_cards,
        )

    # ------------------------------------------------------------------
    #  Admin Dashboard
    # ------------------------------------------------------------------

    @staticmethod
    def get_admin_dashboard(db: Session, user: User) -> AdminDashboardResponse:
        total_users = DashboardService._count_entity(db, User)
        total_doctors = DashboardService._count_entity(db, Doctor)
        total_patients = DashboardService._count_entity(db, Patient)
        total_appointments = DashboardService._count_entity(db, Appointment)
        total_visits = DashboardService._count_entity(db, Visit)
        total_prescriptions = DashboardService._count_entity(db, Prescription)
        total_medical_records = DashboardService._count_entity(db, MedicalRecord)
        total_medicines = db.scalar(select(func.count(Medicine.id)).where(Medicine.is_active == True)) or 0

        total_notifications = DashboardService._count_entity(db, Notification)
        total_audit_logs = DashboardService._count_entity(db, AuditLog)

        system_stats = {
            "doctor_to_patient_ratio": round(total_patients / total_doctors, 2) if total_doctors else 0,
            "appointment_completion_rate": DashboardService._get_completion_rate(db, Appointment),
            "visit_with_diagnosis_pct": DashboardService._get_visit_diagnosis_rate(db),
        }

        platform_activity = [
            PlatformActivity(period="all", label="Appointments", value=total_appointments),
            PlatformActivity(period="all", label="Visits", value=total_visits),
            PlatformActivity(period="all", label="Prescriptions", value=total_prescriptions),
            PlatformActivity(period="all", label="Medical Records", value=total_medical_records),
        ]

        growth_metrics = {
            "total_users": total_users,
            "total_doctors": total_doctors,
            "total_patients": total_patients,
        }

        recent_regs = DashboardService._get_recent_registrations(db, limit=10)
        recent_appts = DashboardService._get_admin_recent_appointments(db, limit=10)
        recent_rxs = DashboardService._get_admin_recent_prescriptions(db, limit=10)

        summary_cards = [
            StatCard(label="Total Users", value=total_users),
            StatCard(label="Doctors", value=total_doctors),
            StatCard(label="Patients", value=total_patients),
            StatCard(label="Appointments", value=total_appointments),
            StatCard(label="Visits", value=total_visits),
            StatCard(label="Prescriptions", value=total_prescriptions),
        ]

        return AdminDashboardResponse(
            total_users=total_users,
            total_doctors=total_doctors,
            total_patients=total_patients,
            total_appointments=total_appointments,
            total_visits=total_visits,
            total_prescriptions=total_prescriptions,
            total_medical_records=total_medical_records,
            total_medicines=total_medicines,
            total_notifications=total_notifications,
            total_audit_logs=total_audit_logs,
            system_stats=system_stats,
            platform_activity=platform_activity,
            growth_metrics=growth_metrics,
            recent_registrations=recent_regs,
            recent_appointments=recent_appts,
            recent_prescriptions=recent_rxs,
            summary_cards=summary_cards,
        )

    # ------------------------------------------------------------------
    #  Helper – COUNT
    # ------------------------------------------------------------------

    @staticmethod
    def _count_entity(db: Session, model, *filters) -> int:
        stmt = select(func.count(model.id))
        for f in filters:
            stmt = stmt.where(f)
        return db.scalar(stmt) or 0

    # ------------------------------------------------------------------
    #  Appointment helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_todays_appointments(db: Session, doctor_id: int) -> list[RecentAppointment]:
        rows = db.scalars(
            select(Appointment)
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == _TODAY,
            )
            .order_by(Appointment.appointment_time)
        ).all()
        return [
            RecentAppointment(
                id=a.id,
                patient_name=_get_patient_name(db, a.patient_id),
                appointment_date=a.appointment_date,
                appointment_time=a.appointment_time,
                reason=a.reason,
                status=a.status,
            )
            for a in rows
        ]

    @staticmethod
    def _get_upcoming_appointments(db: Session, doctor_id: int) -> list[RecentAppointment]:
        rows = db.scalars(
            select(Appointment)
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date > _TODAY,
                Appointment.status.in_(_APPOINTMENT_UPCOMING_STATUSES),
            )
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
        ).all()
        return [
            RecentAppointment(
                id=a.id,
                patient_name=_get_patient_name(db, a.patient_id),
                appointment_date=a.appointment_date,
                appointment_time=a.appointment_time,
                reason=a.reason,
                status=a.status,
            )
            for a in rows
        ]

    @staticmethod
    def _count_completed_appointments(db: Session, doctor_id: int) -> int:
        return DashboardService._count_entity(
            db, Appointment,
            Appointment.doctor_id == doctor_id,
            Appointment.status == AppointmentStatus.COMPLETED,
        )

    @staticmethod
    def _count_pending_appointments(db: Session, doctor_id: int) -> int:
        return DashboardService._count_entity(
            db, Appointment,
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(_APPOINTMENT_UPCOMING_STATUSES),
        )

    @staticmethod
    def _count_doctor_patients(db: Session, doctor_id: int) -> int:
        subq = select(Visit.patient_id).where(Visit.doctor_id == doctor_id).distinct().subquery()
        return db.scalar(select(func.count()).select_from(subq)) or 0

    @staticmethod
    def _get_patient_upcoming_appointments(db: Session, patient_id: int) -> list[RecentAppointment]:
        rows = db.scalars(
            select(Appointment)
            .where(
                Appointment.patient_id == patient_id,
                or_(
                    Appointment.appointment_date > _TODAY,
                    Appointment.appointment_date == _TODAY,
                ),
            )
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
        ).all()
        return [
            RecentAppointment(
                id=a.id,
                doctor_name=_get_doctor_name(db, a.doctor_id),
                appointment_date=a.appointment_date,
                appointment_time=a.appointment_time,
                reason=a.reason,
                status=a.status,
            )
            for a in rows
        ]

    # ------------------------------------------------------------------
    #  Visit helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_doctor_recent_visits(db: Session, doctor_id: int, limit: int) -> list[RecentVisit]:
        rows = db.scalars(
            select(Visit)
            .where(Visit.doctor_id == doctor_id)
            .order_by(Visit.created_at.desc())
            .limit(limit)
        ).all()
        return [
            RecentVisit(
                id=v.id,
                patient_name=_get_patient_name(db, v.patient_id),
                visit_date=v.visit_date,
                diagnosis=v.diagnosis,
                status=v.status,
            )
            for v in rows
        ]

    @staticmethod
    def _get_patient_recent_visits(db: Session, patient_id: int, limit: int) -> list[RecentVisit]:
        rows = db.scalars(
            select(Visit)
            .where(Visit.patient_id == patient_id)
            .order_by(Visit.created_at.desc())
            .limit(limit)
        ).all()
        return [
            RecentVisit(
                id=v.id,
                doctor_name=_get_doctor_name(db, v.doctor_id),
                visit_date=v.visit_date,
                diagnosis=v.diagnosis,
                status=v.status,
            )
            for v in rows
        ]

    @staticmethod
    def _get_visit_diagnosis_rate(db: Session) -> float:
        total = DashboardService._count_entity(db, Visit)
        if not total:
            return 0.0
        with_diag = DashboardService._count_entity(
            db, Visit,
            Visit.diagnosis.isnot(None),
            Visit.diagnosis != "",
        )
        return round(with_diag / total * 100, 1)

    # ------------------------------------------------------------------
    #  Prescription helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_doctor_recent_prescriptions(db: Session, doctor_id: int, limit: int) -> list[RecentPrescription]:
        rows = db.scalars(
            select(Prescription)
            .where(Prescription.doctor_id == doctor_id)
            .order_by(Prescription.created_at.desc())
            .limit(limit)
        ).all()
        return [
            RecentPrescription(
                id=r.id,
                patient_name=_get_patient_name(db, r.patient_id),
                diagnosis=r.diagnosis,
                created_at=r.created_at,
            )
            for r in rows
        ]

    @staticmethod
    def _get_patient_recent_prescriptions(db: Session, patient_id: int, limit: int) -> list[RecentPrescription]:
        rows = db.scalars(
            select(Prescription)
            .where(Prescription.patient_id == patient_id)
            .order_by(Prescription.created_at.desc())
            .limit(limit)
        ).all()
        return [
            RecentPrescription(
                id=r.id,
                doctor_name=_get_doctor_name(db, r.doctor_id),
                diagnosis=r.diagnosis,
                created_at=r.created_at,
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    #  Medication helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_active_medications(db: Session, patient_id: int) -> list[ActiveMedication]:
        rows = db.scalars(
            select(PrescriptionItem)
            .join(Prescription, PrescriptionItem.prescription_id == Prescription.id)
            .where(Prescription.patient_id == patient_id)
            .order_by(PrescriptionItem.created_at.desc())
            .limit(20)
        ).all()
        seen: set[str] = set()
        results: list[ActiveMedication] = []
        for item in rows:
            key = item.medicine_name.lower()
            if key not in seen:
                seen.add(key)
                results.append(ActiveMedication(
                    medicine_name=item.medicine_name,
                    dosage=item.dosage,
                    frequency=item.frequency,
                    duration=item.duration,
                ))
        return results

    # ------------------------------------------------------------------
    #  Notification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_notifications(db: Session, user_id: int, limit: int) -> list[NotificationSummary]:
        rows = db.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        ).all()
        return [
            NotificationSummary(
                id=n.id,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in rows
        ]

    # ------------------------------------------------------------------
    #  Medical record stats
    # ------------------------------------------------------------------

    @staticmethod
    def _get_doctor_medical_record_stats(db: Session, doctor_id: int) -> dict:
        total = DashboardService._count_entity(db, MedicalRecord, MedicalRecord.doctor_id == doctor_id)
        with_bmi = DashboardService._count_entity(
            db, MedicalRecord,
            MedicalRecord.doctor_id == doctor_id,
            MedicalRecord.bmi.isnot(None),
        )
        return {
            "total_records": total,
            "records_with_bmi": with_bmi,
        }

    # ------------------------------------------------------------------
    #  Patient timeline
    # ------------------------------------------------------------------

    @staticmethod
    def _get_patient_timeline(db: Session, patient_id: int, limit: int) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []

        visits = db.scalars(
            select(Visit).where(Visit.patient_id == patient_id)
            .order_by(Visit.created_at.desc()).limit(limit)
        ).all()
        for v in visits:
            events.append(TimelineEvent(
                type="visit",
                title=f"Visit {v.id}",
                description=v.diagnosis,
                date=v.created_at,
            ))

        prescriptions = db.scalars(
            select(Prescription).where(Prescription.patient_id == patient_id)
            .order_by(Prescription.created_at.desc()).limit(limit)
        ).all()
        for r in prescriptions:
            events.append(TimelineEvent(
                type="prescription",
                title=f"Prescription #{r.id}",
                description=r.diagnosis,
                date=r.created_at,
            ))

        appointments = db.scalars(
            select(Appointment).where(Appointment.patient_id == patient_id)
            .order_by(Appointment.created_at.desc()).limit(limit)
        ).all()
        for a in appointments:
            events.append(TimelineEvent(
                type="appointment",
                title=f"Appointment #{a.id}",
                description=a.reason,
                date=a.created_at,
            ))

        records = db.scalars(
            select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.created_at.desc()).limit(limit)
        ).all()
        for mr in records:
            events.append(TimelineEvent(
                type="medical_record",
                title=f"Medical Record #{mr.id}",
                description=mr.diagnosis,
                date=mr.created_at,
            ))

        events.sort(key=lambda e: e.date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return events[:limit]

    # ------------------------------------------------------------------
    #  Admin helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_completion_rate(db: Session, model) -> float:
        total = DashboardService._count_entity(db, model)
        if not total:
            return 0.0
        completed = DashboardService._count_entity(
            db, model,
            model.status == AppointmentStatus.COMPLETED,
        )
        return round(completed / total * 100, 1)

    @staticmethod
    def _get_recent_registrations(db: Session, limit: int) -> list[RegistrationSummary]:
        rows = db.scalars(
            select(User).order_by(User.created_at.desc()).limit(limit)
        ).all()
        return [
            RegistrationSummary(
                id=u.id,
                email=u.email,
                role=u.role.value,
                created_at=u.created_at,
            )
            for u in rows
        ]

    @staticmethod
    def _get_admin_recent_appointments(db: Session, limit: int) -> list[RecentAppointment]:
        rows = db.scalars(
            select(Appointment).order_by(Appointment.created_at.desc()).limit(limit)
        ).all()
        return [
            RecentAppointment(
                id=a.id,
                patient_name=_get_patient_name(db, a.patient_id),
                doctor_name=_get_doctor_name(db, a.doctor_id),
                appointment_date=a.appointment_date,
                appointment_time=a.appointment_time,
                reason=a.reason,
                status=a.status,
            )
            for a in rows
        ]

    @staticmethod
    def _get_admin_recent_prescriptions(db: Session, limit: int) -> list[RecentPrescription]:
        rows = db.scalars(
            select(Prescription).order_by(Prescription.created_at.desc()).limit(limit)
        ).all()
        return [
            RecentPrescription(
                id=r.id,
                patient_name=_get_patient_name(db, r.patient_id),
                doctor_name=_get_doctor_name(db, r.doctor_id),
                diagnosis=r.diagnosis,
                created_at=r.created_at,
            )
            for r in rows
        ]


# ------------------------------------------------------------------
#  Module-level helpers (avoid circular imports in static methods)
# ------------------------------------------------------------------

def _get_patient_name(db: Session, patient_id: int) -> str | None:
    p = db.get(Patient, patient_id)
    return p.full_name if p else None


def _get_doctor_name(db: Session, doctor_id: int) -> str | None:
    d = db.get(Doctor, doctor_id)
    return d.full_name if d else None
