from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.cache.service import CacheService
from app.core.config import settings
from app.models.medicine import Medicine
from app.schemas.medicine import (
    MedicineCreate,
    MedicineUpdate,
    VALID_DOSAGE_FORMS,
    VALID_ROUTES,
)


class MedicineValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


class MedicineService:

    @staticmethod
    def _validate_dosage_form(dosage_form: str) -> None:
        if dosage_form not in VALID_DOSAGE_FORMS:
            raise MedicineValidationError(
                f"Invalid dosage form '{dosage_form}'. Valid values: {', '.join(sorted(VALID_DOSAGE_FORMS))}",
                status_code=400,
            )

    @staticmethod
    def _validate_route(route: str) -> None:
        if route not in VALID_ROUTES:
            raise MedicineValidationError(
                f"Invalid route '{route}'. Valid values: {', '.join(sorted(VALID_ROUTES))}",
                status_code=400,
            )

    @staticmethod
    def _check_duplicate(
        db: Session, generic_name: str, strength: str, dosage_form: str,
        exclude_id: int | None = None,
    ) -> None:
        stmt = select(Medicine).where(
            Medicine.generic_name == generic_name,
            Medicine.strength == strength,
            Medicine.dosage_form == dosage_form,
        )
        if exclude_id is not None:
            stmt = stmt.where(Medicine.id != exclude_id)
        existing = db.scalar(stmt)
        if existing:
            raise MedicineValidationError(
                f"Medicine '{generic_name} {strength} ({dosage_form})' already exists",
                status_code=409,
            )

    @staticmethod
    def create_medicine(
        db: Session, medicine_data: MedicineCreate
    ) -> Medicine:
        MedicineService._validate_dosage_form(medicine_data.dosage_form)
        MedicineService._validate_route(medicine_data.route)
        MedicineService._check_duplicate(
            db, medicine_data.generic_name, medicine_data.strength, medicine_data.dosage_form
        )

        medicine = Medicine(**medicine_data.model_dump())
        db.add(medicine)
        db.commit()
        db.refresh(medicine)
        CacheService.invalidate_namespace(CacheService.NAMESPACE_MEDICINE)
        return medicine

    @staticmethod
    def get_medicine(db: Session, medicine_id: int) -> Medicine | None:
        cache_key = CacheService.build_key(CacheService.NAMESPACE_MEDICINE, "item", str(medicine_id))
        cached = CacheService.get(cache_key)
        if cached is not None:
            return Medicine(**cached) if cached else None
        result = db.get(Medicine, medicine_id)
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_MEDICINE)
        return result

    @staticmethod
    def list_medicines(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        generic_name: str | None = None,
        manufacturer: str | None = None,
        drug_class: str | None = None,
        dosage_form: str | None = None,
        route: str | None = None,
        is_active: bool | None = None,
    ) -> list[Medicine]:
        cache_key = CacheService.build_key(
            CacheService.NAMESPACE_MEDICINE, "list",
            str(skip), str(limit),
            str(generic_name or ""), str(manufacturer or ""),
            str(drug_class or ""), str(dosage_form or ""),
            str(route or ""), str(is_active or ""),
        )
        cached = CacheService.get(cache_key)
        if cached is not None:
            return [Medicine(**m) for m in cached]

        stmt = select(Medicine)
        if generic_name:
            stmt = stmt.where(Medicine.generic_name.ilike(f"%{generic_name}%"))
        if manufacturer:
            stmt = stmt.where(Medicine.manufacturer.ilike(f"%{manufacturer}%"))
        if drug_class:
            stmt = stmt.where(Medicine.drug_class.ilike(f"%{drug_class}%"))
        if dosage_form:
            stmt = stmt.where(Medicine.dosage_form == dosage_form)
        if route:
            stmt = stmt.where(Medicine.route == route)
        if is_active is not None:
            stmt = stmt.where(Medicine.is_active == is_active)

        stmt = stmt.offset(skip).limit(limit)
        result = list(db.scalars(stmt).all())
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_MEDICINE)
        return result

    @staticmethod
    def update_medicine(
        db: Session, medicine_id: int, medicine_update: MedicineUpdate
    ) -> Medicine | None:
        medicine = db.get(Medicine, medicine_id)
        if not medicine:
            return None

        if not medicine.is_active:
            raise MedicineValidationError(
                "Cannot update an inactive medicine", status_code=400
            )

        update_data = medicine_update.model_dump(exclude_unset=True)

        if "dosage_form" in update_data:
            MedicineService._validate_dosage_form(update_data["dosage_form"])
        if "route" in update_data:
            MedicineService._validate_route(update_data["route"])

        generic_name = update_data.get("generic_name", medicine.generic_name)
        strength = update_data.get("strength", medicine.strength)
        dosage_form = update_data.get("dosage_form", medicine.dosage_form)
        MedicineService._check_duplicate(db, generic_name, strength, dosage_form, exclude_id=medicine_id)

        for key, value in update_data.items():
            setattr(medicine, key, value)
        db.commit()
        db.refresh(medicine)
        CacheService.invalidate_namespace(CacheService.NAMESPACE_MEDICINE)
        return medicine

    @staticmethod
    def delete_medicine(db: Session, medicine_id: int) -> Medicine | None:
        medicine = db.get(Medicine, medicine_id)
        if not medicine:
            return None
        db.delete(medicine)
        db.commit()
        CacheService.invalidate_namespace(CacheService.NAMESPACE_MEDICINE)
        return medicine

    @staticmethod
    def search_medicines(
        db: Session,
        q: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Medicine]:
        cache_key = CacheService.build_key(
            CacheService.NAMESPACE_MEDICINE, "search", q, str(skip), str(limit),
        )
        cached = CacheService.get(cache_key)
        if cached is not None:
            return [Medicine(**m) for m in cached]

        pattern = f"%{q}%"
        stmt = (
            select(Medicine)
            .where(
                or_(
                    Medicine.generic_name.ilike(pattern),
                    Medicine.brand_name.ilike(pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = list(db.scalars(stmt).all())
        CacheService.set(cache_key, result, ttl=settings.CACHE_TTL_MEDICINE)
        return result
