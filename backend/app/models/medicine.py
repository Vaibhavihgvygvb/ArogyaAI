from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strength: Mapped[str] = mapped_column(String(100), nullable=False)
    dosage_form: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(100), nullable=False)
    drug_class: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contraindications: Mapped[str | None] = mapped_column(Text, nullable=True)
    side_effects: Mapped[str | None] = mapped_column(Text, nullable=True)
    drug_interactions: Mapped[str | None] = mapped_column(Text, nullable=True)
    pregnancy_category: Mapped[str | None] = mapped_column(String(10), nullable=True)
    storage_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )
