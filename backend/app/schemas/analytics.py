from datetime import date, datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
#  Shared types
# ---------------------------------------------------------------------------

class EntityCount(BaseModel):
    entity: str
    total: int


class ActivityTrend(BaseModel):
    period: str
    date: date
    count: int


class GrowthMetric(BaseModel):
    metric: str
    current: int
    previous: int | None = None
    growth_pct: float | None = None


class SummaryCard(BaseModel):
    label: str
    value: int
    trend: str | None = None


# ---------------------------------------------------------------------------
#  Platform Analytics
# ---------------------------------------------------------------------------

class PlatformAnalyticsResponse(BaseModel):
    entity_counts: list[EntityCount] = []
    daily_activity: list[ActivityTrend] = []
    weekly_activity: list[ActivityTrend] = []
    monthly_activity: list[ActivityTrend] = []
    growth_metrics: list[GrowthMetric] = []


# ---------------------------------------------------------------------------
#  Doctor Analytics
# ---------------------------------------------------------------------------

class DoctorAnalyticsResponse(BaseModel):
    doctor_id: int
    doctor_name: str
    specialization: str | None = None
    appointments_completed: int = 0
    upcoming_appointments: int = 0
    patients_treated: int = 0
    visits_completed: int = 0
    prescriptions_written: int = 0
    medical_records_created: int = 0
    avg_appointments_per_day: float = 0.0
    avg_patients_per_week: float = 0.0
    recent_activity: list[ActivityTrend] = []


# ---------------------------------------------------------------------------
#  Patient Analytics
# ---------------------------------------------------------------------------

class PatientAnalyticsResponse(BaseModel):
    patient_id: int
    patient_name: str
    total_visits: int = 0
    total_appointments: int = 0
    completed_appointments: int = 0
    cancelled_appointments: int = 0
    total_prescriptions: int = 0
    total_medical_records: int = 0
    medication_count: int = 0
    timeline_summary: list[ActivityTrend] = []


# ---------------------------------------------------------------------------
#  System Analytics
# ---------------------------------------------------------------------------

class SystemAnalyticsResponse(BaseModel):
    most_active_doctors: list[dict] = []
    daily_registrations: list[ActivityTrend] = []
    monthly_registrations: list[ActivityTrend] = []
    appointment_utilization: float = 0.0
    prescription_trends: list[ActivityTrend] = []
    visit_trends: list[ActivityTrend] = []
    notification_trends: list[ActivityTrend] = []


# ---------------------------------------------------------------------------
#  Summary
# ---------------------------------------------------------------------------

class AnalyticsSummaryResponse(BaseModel):
    summary_cards: list[SummaryCard] = []
