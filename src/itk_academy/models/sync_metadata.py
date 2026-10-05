from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from itk_academy.db.base import Base
from itk_academy.models.enums import SyncStatus


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status", native_enum=True),
        nullable=False,
        default=SyncStatus.IDLE,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )
