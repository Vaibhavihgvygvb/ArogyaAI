from datetime import date, datetime, time

from pydantic import BaseModel

from app.models.enums import AppointmentStatus


# ---------------------------------------------------------------------------
# Shared summary-card types
# ---------------------------------------------------------------------------

class StatCard(BaseModel):
    label: str
    value: int
    trend: str | None = None


class RecentAppointment(BaseModel):
    id: int
    patient_name: str | None = None
    doctor_name: str | None = None
    appointment_date: date
    appointment_time: time
    reason: str
    status: AppointmentStatus


class RecentVisit(BaseModel):
    id: int
    patient_name: str | None = None
    doctor_name: str | None = None
    visit_date: datetime
    diagnosis: str | None = None
    status: str | None = None


class RecentPrescription(BaseModel):
    id: int
    patient_name: str | None = None
    doctor_name: str | None = None
    diagnosis: str
    created_at: datetime


class NotificationSummary(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Doctor Dashboard
# ---------------------------------------------------------------------------

class DoctorDashboardResponse(BaseModel):
    profile: dict | None = None
    todays_appointments: list[RecentAppointment] = []
    upcoming_appointments: list[RecentAppointment] = []
    completed_appointments: int = 0
    pending_appointments: int = 0
    total_patients: int = 0
    recent_visits: list[RecentVisit] = []
    recent_prescriptions: list[RecentPrescription] = []
    notifications: list[NotificationSummary] = []
    medical_record_stats: dict = {}
    summary_cards: list[StatCard] = []


# ---------------------------------------------------------------------------
# Patient Dashboard
# ---------------------------------------------------------------------------

class TimelineEvent(BaseModel):
    type: str
    title: str
    description: str | None = None
    date: datetime | None = None


class ActiveMedication(BaseModel):
    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None


class PatientDashboardResponse(BaseModel):
    profile: dict | None = None
    upcoming_appointments: list[RecentAppointment] = []
    medical_history_summary: dict = {}
    prescriptions: list[RecentPrescription] = []
    active_medications: list[ActiveMedication] = []
    recent_visits: list[RecentVisit] = []
    notifications: list[NotificationSummary] = []
    timeline_preview: list[TimelineEvent] = []
    health_summary_cards: list[StatCard] = []


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------

class RegistrationSummary(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime


class PlatformActivity(BaseModel):
    period: str
    label: str
    value: int


class AdminDashboardResponse(BaseModel):
    total_users: int = 0
    total_doctors: int = 0
    total_patients: int = 0
    total_appointments: int = 0
    total_visits: int = 0
    total_prescriptions: int = 0
    total_medical_records: int = 0
    total_medicines: int = 0
    total_notifications: int = 0
    total_audit_logs: int = 0
    system_stats: dict = {}
    platform_activity: list[PlatformActivity] = []
    growth_metrics: dict = {}
    recent_registrations: list[RegistrationSummary] = []
    recent_appointments: list[RecentAppointment] = []
    recent_prescriptions: list[RecentPrescription] = []
    summary_cards: list[StatCard] = []
