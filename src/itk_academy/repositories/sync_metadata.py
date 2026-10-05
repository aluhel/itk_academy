from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from itk_academy.models.enums import SyncStatus
from itk_academy.models.sync_metadata import SyncMetadata


class SqlAlchemySyncMetadataRepository:
    SINGLETON_ID = 1

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SyncMetadata | None:
        stmt = select(SyncMetadata).where(SyncMetadata.id == self.SINGLETON_ID)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self) -> SyncMetadata:
        existing = await self.get()
        if existing is not None:
            return existing

        record = SyncMetadata(id=self.SINGLETON_ID, sync_status=SyncStatus.IDLE)
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def update(
        self,
        *,
        last_sync_time: datetime | None = None,
        last_changed_at: datetime | None = None,
        sync_status: SyncStatus | None = None,
        last_error: str | None = None,
    ) -> SyncMetadata:
        record = await self.get_or_create()
        if last_sync_time is not None:
            record.last_sync_time = last_sync_time
        if last_changed_at is not None:
            record.last_changed_at = last_changed_at
        if sync_status is not None:
            record.sync_status = sync_status
        if last_error is not None:
            record.last_error = last_error
        record.updated_at = datetime.now(tz=UTC)
        await self._session.commit()
        await self._session.refresh(record)
        return record
