from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, String, Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"
    __table_args__ = (
        UniqueConstraint("visit_id", name="uq_medical_record_visit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(
        ForeignKey("visits.id"), nullable=False, index=True
    )
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)

    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    history_of_present_illness: Mapped[str | None] = mapped_column(Text, nullable=True)
    past_medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    surgical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergy_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    medication_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_history: Mapped[str | None] = mapped_column(Text, nullable=True)

    physical_examination: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)

    treatment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)
    blood_pressure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pulse: Mapped[int | None] = mapped_column(Float, nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    oxygen_saturation: Mapped[float | None] = mapped_column(Float, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )

    visit: Mapped[Visit] = relationship(back_populates="medical_record")
    doctor: Mapped[Doctor] = relationship(back_populates="medical_records")
    patient: Mapped[Patient] = relationship(back_populates="medical_records")
