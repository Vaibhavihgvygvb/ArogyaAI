from app.schemas.visit import VisitBase, VisitCreate, VisitUpdate, VisitResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate, Token, ChangePasswordRequest, RefreshTokenRequest
from app.schemas.doctor import DoctorUpdate, DoctorResponse
from app.schemas.patient import PatientUpdate, PatientResponse
from app.schemas.appointment import AppointmentBase, AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.schemas.prescription import PrescriptionBase, PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse
from app.schemas.prescription_item import PrescriptionItemBase, PrescriptionItemCreate, PrescriptionItemUpdate, PrescriptionItemResponse
from app.schemas.medicine import MedicineBase, MedicineCreate, MedicineUpdate, MedicineResponse
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate, MedicalRecordResponse
from app.schemas.notification import NotificationCreate, NotificationUpdate, NotificationResponse, NotificationListResponse, NotificationFilters, NotificationMarkReadRequest, NotificationMarkAllReadRequest
from app.schemas.search import SearchResponse, SearchResultItem
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

