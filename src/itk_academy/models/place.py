import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from itk_academy.db.base import Base


class Place(Base):
    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    seats_pattern: Mapped[str] = mapped_column(String(500), nullable=False)

    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    events: Mapped[list["Event"]] = relationship(  # noqa: F821
        back_populates="place",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
