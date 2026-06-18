import inspect
import re
from datetime import datetime

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload

from app.cache.service import CacheService
from app.core.config import settings
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.medicine import Medicine
from app.models.medical_record import MedicalRecord
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.schemas.search import SearchResultItem


_MAX_QUERY_LENGTH = 200
_MAX_PAGE_SIZE = 100


def _truncate(text: str | None, max_len: int = 200) -> str | None:
    if not text:
        return None
    return text[:max_len] + "..." if len(text) > max_len else text


def _generate_highlight(text: str | None, query: str, context_chars: int = 60) -> str | None:
    if not text or not query:
        return None
    lower = text.lower()
    q_lower = query.lower()
    idx = lower.find(q_lower)
    if idx == -1:
        return None
    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(query) + context_chars)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


class SearchService:

    @staticmethod
    def _get_doctor_id(db: Session, user_id: int) -> int | None:
        doctor = db.scalar(select(Doctor).where(Doctor.user_id == user_id))
        return doctor.id if doctor else None

    @staticmethod
    def _get_patient_id(db: Session, user_id: int) -> int | None:
        patient = db.scalar(select(Patient).where(Patient.user_id == user_id))
        return patient.id if patient else None

    @staticmethod
    def _search_users(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
    ) -> tuple[list[SearchResultItem], int]:
        if user.role != UserRole.ADMIN:
            return [], 0

        stmt = select(User)
        where_clauses = [
            User.email.ilike(f"%{query}%"),
            User.role.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            where_clauses.append(User.id == int(query))
        stmt = stmt.where(or_(*where_clauses))

        if date_from:
            stmt = stmt.where(User.created_at >= date_from)
        if date_to:
            stmt = stmt.where(User.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for u in rows:
            results.append(SearchResultItem(
                entity_type="user",
                entity_id=u.id,
                title=u.email,
                subtitle=f"Role: {u.role.value}",
                summary=f"Active: {u.is_active}, Verified: {u.is_verified}",
                created_at=u.created_at,
                highlight=_generate_highlight(u.email, query),
            ))
        return results, total

    @staticmethod
    def _search_doctors(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
        doctor_id_filter: int | None = None,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(Doctor)
        like_clauses = [
            Doctor.full_name.ilike(f"%{query}%"),
            Doctor.email.ilike(f"%{query}%"),
            Doctor.specialization.ilike(f"%{query}%"),
            Doctor.clinic_name.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(Doctor.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role == UserRole.DOCTOR:
            doctor_id = SearchService._get_doctor_id(db, user.id)
            if doctor_id is not None:
                stmt = stmt.where(Doctor.id == doctor_id)
        elif user.role == UserRole.PATIENT:
            return [], 0

        if doctor_id_filter is not None:
            stmt = stmt.where(Doctor.id == doctor_id_filter)
        if date_from:
            stmt = stmt.where(Doctor.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Doctor.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Doctor.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for d in rows:
            results.append(SearchResultItem(
                entity_type="doctor",
                entity_id=d.id,
                title=d.full_name,
                subtitle=d.specialization or "General",
                summary=f"{d.clinic_name or 'N/A'} | {d.email}",
                created_at=d.created_at,
                highlight=_generate_highlight(d.full_name, query) or _generate_highlight(d.specialization, query),
            ))
        return results, total

    @staticmethod
    def _search_patients(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
        patient_id_filter: int | None = None,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(Patient)
        like_clauses = [
            Patient.full_name.ilike(f"%{query}%"),
            Patient.phone_number.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(Patient.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role == UserRole.PATIENT:
            patient_id = SearchService._get_patient_id(db, user.id)
            if patient_id is not None:
                stmt = stmt.where(Patient.id == patient_id)
        elif user.role == UserRole.DOCTOR:
            doctor_id = SearchService._get_doctor_id(db, user.id)
            if doctor_id is not None:
                stmt = stmt.where(
                    Patient.id.in_(
                        select(Visit.patient_id).where(Visit.doctor_id == doctor_id).distinct()
                    )
                )

        if patient_id_filter is not None:
            stmt = stmt.where(Patient.id == patient_id_filter)
        if date_from:
            stmt = stmt.where(Patient.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Patient.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Patient.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for p in rows:
            results.append(SearchResultItem(
                entity_type="patient",
                entity_id=p.id,
                title=p.full_name,
                subtitle=p.gender or "N/A",
                summary=f"Phone: {p.phone_number} | DOB: {p.date_of_birth or 'N/A'}",
                created_at=p.created_at,
                highlight=_generate_highlight(p.full_name, query),
            ))
        return results, total

    @staticmethod
    def _search_visits(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
        doctor_id_filter: int | None = None,
        patient_id_filter: int | None = None,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(Visit)
        like_clauses = [
            Visit.diagnosis.ilike(f"%{query}%"),
            Visit.symptoms.ilike(f"%{query}%"),
            Visit.instructions.ilike(f"%{query}%"),
            Visit.status.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(Visit.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role == UserRole.DOCTOR:
            doctor_id = SearchService._get_doctor_id(db, user.id)
            if doctor_id is not None:
                stmt = stmt.where(Visit.doctor_id == doctor_id)
        elif user.role == UserRole.PATIENT:
            patient_id = SearchService._get_patient_id(db, user.id)
            if patient_id is not None:
                stmt = stmt.where(Visit.patient_id == patient_id)

        if doctor_id_filter is not None:
            stmt = stmt.where(Visit.doctor_id == doctor_id_filter)
        if patient_id_filter is not None:
            stmt = stmt.where(Visit.patient_id == patient_id_filter)
        if date_from:
            stmt = stmt.where(Visit.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Visit.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Visit.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for v in rows:
            results.append(SearchResultItem(
                entity_type="visit",
                entity_id=v.id,
                title=f"Visit #{v.id}",
                subtitle=v.diagnosis or "No diagnosis",
                summary=f"Doctor: {v.doctor_id}, Patient: {v.patient_id}, Status: {v.status or 'N/A'}",
                created_at=v.created_at,
                highlight=_generate_highlight(v.diagnosis, query),
            ))
        return results, total

    @staticmethod
    def _search_appointments(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
        doctor_id_filter: int | None = None,
        patient_id_filter: int | None = None,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(Appointment)
        like_clauses = [
            Appointment.reason.ilike(f"%{query}%"),
            Appointment.status.ilike(f"%{query}%"),
            Appointment.notes.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(Appointment.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role == UserRole.DOCTOR:
            doctor_id = SearchService._get_doctor_id(db, user.id)
            if doctor_id is not None:
                stmt = stmt.where(Appointment.doctor_id == doctor_id)
        elif user.role == UserRole.PATIENT:
            patient_id = SearchService._get_patient_id(db, user.id)
            if patient_id is not None:
                stmt = stmt.where(Appointment.patient_id == patient_id)

        if doctor_id_filter is not None:
            stmt = stmt.where(Appointment.doctor_id == doctor_id_filter)
        if patient_id_filter is not None:
            stmt = stmt.where(Appointment.patient_id == patient_id_filter)
        if date_from:
            stmt = stmt.where(Appointment.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Appointment.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Appointment.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for a in rows:
            results.append(SearchResultItem(
                entity_type="appointment",
                entity_id=a.id,
                title=f"Appointment #{a.id}",
                subtitle=a.reason,
                summary=f"Date: {a.appointment_date}, Status: {a.status.value if hasattr(a.status, 'value') else a.status}",
                created_at=a.created_at,
                highlight=_generate_highlight(a.reason, query),
            ))
        return results, total

    @staticmethod
    def _search_prescriptions(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
        doctor_id_filter: int | None = None,
        patient_id_filter: int | None = None,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(Prescription)
        like_clauses = [
            Prescription.diagnosis.ilike(f"%{query}%"),
            Prescription.notes.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(Prescription.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role == UserRole.DOCTOR:
            doctor_id = SearchService._get_doctor_id(db, user.id)
            if doctor_id is not None:
                stmt = stmt.where(Prescription.doctor_id == doctor_id)
        elif user.role == UserRole.PATIENT:
            patient_id = SearchService._get_patient_id(db, user.id)
            if patient_id is not None:
                stmt = stmt.where(Prescription.patient_id == patient_id)

        if doctor_id_filter is not None:
            stmt = stmt.where(Prescription.doctor_id == doctor_id_filter)
        if patient_id_filter is not None:
            stmt = stmt.where(Prescription.patient_id == patient_id_filter)
        if date_from:
            stmt = stmt.where(Prescription.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Prescription.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Prescription.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for p in rows:
            results.append(SearchResultItem(
                entity_type="prescription",
                entity_id=p.id,
                title=f"Prescription #{p.id}",
                subtitle=_truncate(p.diagnosis, 100),
                summary=f"Doctor: {p.doctor_id}, Patient: {p.patient_id}",
                created_at=p.created_at,
                highlight=_generate_highlight(p.diagnosis, query),
            ))
        return results, total

    @staticmethod
    def _search_prescription_items(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(PrescriptionItem)
        like_clauses = [
            PrescriptionItem.medicine_name.ilike(f"%{query}%"),
            PrescriptionItem.dosage.ilike(f"%{query}%"),
            PrescriptionItem.frequency.ilike(f"%{query}%"),
            PrescriptionItem.instructions.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(PrescriptionItem.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role == UserRole.DOCTOR:
            doctor_id = SearchService._get_doctor_id(db, user.id)
            if doctor_id is not None:
                stmt = stmt.where(
                    PrescriptionItem.prescription_id.in_(
                        select(Prescription.id).where(Prescription.doctor_id == doctor_id)
                    )
                )
        elif user.role == UserRole.PATIENT:
            patient_id = SearchService._get_patient_id(db, user.id)
            if patient_id is not None:
                stmt = stmt.where(
                    PrescriptionItem.prescription_id.in_(
                        select(Prescription.id).where(Prescription.patient_id == patient_id)
                    )
                )

        if date_from:
            stmt = stmt.where(PrescriptionItem.created_at >= date_from)
        if date_to:
            stmt = stmt.where(PrescriptionItem.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(PrescriptionItem.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for pi in rows:
            results.append(SearchResultItem(
                entity_type="prescription_item",
                entity_id=pi.id,
                title=pi.medicine_name,
                subtitle=f"{pi.strength or ''} {pi.dosage or ''}".strip() or "N/A",
                summary=f"Frequency: {pi.frequency or 'N/A'} | Duration: {pi.duration or 'N/A'}",
                created_at=pi.created_at,
                highlight=_generate_highlight(pi.medicine_name, query),
            ))
        return results, total

    @staticmethod
    def _search_medicines(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(Medicine)
        like_clauses = [
            Medicine.generic_name.ilike(f"%{query}%"),
            Medicine.brand_name.ilike(f"%{query}%"),
            Medicine.manufacturer.ilike(f"%{query}%"),
            Medicine.drug_class.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(Medicine.id == int(query))
        stmt = stmt.where(or_(*like_clauses)).where(Medicine.is_active == True)

        if date_from:
            stmt = stmt.where(Medicine.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Medicine.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Medicine.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for m in rows:
            brand = f" ({m.brand_name})" if m.brand_name else ""
            results.append(SearchResultItem(
                entity_type="medicine",
                entity_id=m.id,
                title=f"{m.generic_name}{brand}",
                subtitle=f"{m.strength} - {m.dosage_form}",
                summary=f"Manufacturer: {m.manufacturer or 'N/A'} | Class: {m.drug_class or 'N/A'}",
                created_at=m.created_at,
                highlight=_generate_highlight(m.generic_name, query) or _generate_highlight(m.brand_name, query),
            ))
        return results, total

    @staticmethod
    def _search_medical_records(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
        doctor_id_filter: int | None = None,
        patient_id_filter: int | None = None,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(MedicalRecord)
        like_clauses = [
            MedicalRecord.chief_complaint.ilike(f"%{query}%"),
            MedicalRecord.diagnosis.ilike(f"%{query}%"),
            MedicalRecord.assessment.ilike(f"%{query}%"),
            MedicalRecord.treatment_plan.ilike(f"%{query}%"),
            MedicalRecord.notes.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(MedicalRecord.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role == UserRole.DOCTOR:
            doctor_id = SearchService._get_doctor_id(db, user.id)
            if doctor_id is not None:
                stmt = stmt.where(MedicalRecord.doctor_id == doctor_id)
        elif user.role == UserRole.PATIENT:
            patient_id = SearchService._get_patient_id(db, user.id)
            if patient_id is not None:
                stmt = stmt.where(MedicalRecord.patient_id == patient_id)

        if doctor_id_filter is not None:
            stmt = stmt.where(MedicalRecord.doctor_id == doctor_id_filter)
        if patient_id_filter is not None:
            stmt = stmt.where(MedicalRecord.patient_id == patient_id_filter)
        if date_from:
            stmt = stmt.where(MedicalRecord.created_at >= date_from)
        if date_to:
            stmt = stmt.where(MedicalRecord.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(MedicalRecord.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for r in rows:
            results.append(SearchResultItem(
                entity_type="medical_record",
                entity_id=r.id,
                title=f"Record #{r.id}",
                subtitle=_truncate(r.chief_complaint, 100) or "No chief complaint",
                summary=f"Diagnosis: {_truncate(r.diagnosis, 100)}",
                created_at=r.created_at,
                highlight=_generate_highlight(r.chief_complaint, query) or _generate_highlight(r.diagnosis, query),
            ))
        return results, total

    @staticmethod
    def _search_notifications(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
    ) -> tuple[list[SearchResultItem], int]:
        stmt = select(Notification)
        like_clauses = [
            Notification.title.ilike(f"%{query}%"),
            Notification.message.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(Notification.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if user.role != UserRole.ADMIN:
            stmt = stmt.where(Notification.user_id == user.id)

        if date_from:
            stmt = stmt.where(Notification.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Notification.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for n in rows:
            results.append(SearchResultItem(
                entity_type="notification",
                entity_id=n.id,
                title=n.title,
                subtitle=_truncate(n.message, 100),
                summary=f"Type: {n.notification_type.value}, Priority: {n.priority.value}, Status: {n.status.value}",
                created_at=n.created_at,
                highlight=_generate_highlight(n.title, query) or _generate_highlight(n.message, query),
            ))
        return results, total

    @staticmethod
    def _search_audit_logs(
        db: Session, query: str, user: User,
        date_from: datetime | None, date_to: datetime | None,
        skip: int, limit: int,
    ) -> tuple[list[SearchResultItem], int]:
        if user.role != UserRole.ADMIN:
            return [], 0

        stmt = select(AuditLog)
        like_clauses = [
            AuditLog.action.ilike(f"%{query}%"),
            AuditLog.resource.ilike(f"%{query}%"),
            AuditLog.details.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            like_clauses.append(AuditLog.id == int(query))
        stmt = stmt.where(or_(*like_clauses))

        if date_from:
            stmt = stmt.where(AuditLog.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AuditLog.created_at <= date_to)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)).all()

        results = []
        for a in rows:
            results.append(SearchResultItem(
                entity_type="audit_log",
                entity_id=a.id,
                title=a.action,
                subtitle=a.resource or "N/A",
                summary=_truncate(a.details, 150),
                created_at=a.created_at,
                highlight=_generate_highlight(a.action, query) or _generate_highlight(a.details, query),
            ))
        return results, total

    @staticmethod
    def global_search(
        db: Session,
        query: str,
        user: User,
        entity: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_order: str = "desc",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        doctor_id: int | None = None,
        patient_id: int | None = None,
    ) -> tuple[list[SearchResultItem], int]:
        if not query or len(query.strip()) == 0:
            return [], 0
        query = query.strip()[:_MAX_QUERY_LENGTH]
        skip = (page - 1) * page_size

        cache_key = CacheService.build_key(
            CacheService.NAMESPACE_SEARCH, entity or "all",
            str(user.id), query, str(page), str(page_size),
            sort_order, str(date_from or ""), str(date_to or ""),
            str(doctor_id or ""), str(patient_id or ""),
        )
        cached = CacheService.get(cache_key)
        if cached is not None:
            items_data, total = cached
            items = [SearchResultItem(**i) if isinstance(i, dict) else i for i in items_data]
            return items, total

        if entity:
            method_name = f"_search_{entity}"
            method = getattr(SearchService, method_name, None)
            if method is None:
                return [], 0
            sig = inspect.signature(method)
            kwargs = {}
            for name, value in [("doctor_id_filter", doctor_id), ("patient_id_filter", patient_id)]:
                if value is not None and name in sig.parameters:
                    kwargs[name] = value
            results, total = method(
                db, query, user, date_from, date_to, skip, page_size, **kwargs,
            )
            if sort_order == "asc":
                results.reverse()
            CacheService.set(cache_key, (results, total), ttl=settings.CACHE_TTL_SEARCH)
            return results, total

        all_results: list[SearchResultItem] = []
        entity_types = [
            "users", "doctors", "patients", "visits", "appointments",
            "prescriptions", "prescription_items", "medicines",
            "medical_records", "notifications", "audit_logs",
        ]

        for et in entity_types:
            method = getattr(SearchService, f"_search_{et}")
            items, _ = method(db, query, user, date_from, date_to, 0, page_size)
            all_results.extend(items)

        all_results.sort(key=lambda r: r.created_at or datetime.min, reverse=(sort_order != "asc"))
        total = len(all_results)
        paginated = all_results[skip:skip + page_size]
        CacheService.set(cache_key, (paginated, total), ttl=settings.CACHE_TTL_SEARCH)
        return paginated, total
