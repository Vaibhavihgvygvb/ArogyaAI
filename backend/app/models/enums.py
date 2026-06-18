import enum


class UserRole(enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"
    CAREGIVER = "caregiver"
    RECEPTIONIST = "receptionist"


class AppointmentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class NotificationType(enum.Enum):
    SYSTEM = "system"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    APPOINTMENT = "appointment"
    PRESCRIPTION = "prescription"
    MEDICAL_RECORD = "medical_record"
    LAB_REPORT = "lab_report"
    EMERGENCY = "emergency"
    MENTAL_HEALTH = "mental_health"
    AI = "ai"


class NotificationPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(enum.Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
