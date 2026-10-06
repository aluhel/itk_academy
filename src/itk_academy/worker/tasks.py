import asyncio

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from itk_academy.config import get_settings
from itk_academy.db.uow import SqlAlchemyUnitOfWork
from itk_academy.events_provider.client import EventsProviderClient
from itk_academy.repositories.events import SqlAlchemyEventRepository
from itk_academy.repositories.places import SqlAlchemyPlaceRepository
from itk_academy.repositories.sync_metadata import SqlAlchemySyncMetadataRepository
from itk_academy.services.sync import SyncEventsUsecase
from itk_academy.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _run_sync() -> dict:
    settings = get_settings()

    # Свой engine на каждый запуск таски, чтобы не тащить пул между event loop'ами.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as session:
            client = EventsProviderClient(
                base_url=settings.events_provider_url,
                api_key=settings.events_provider_api_key,
            )
            try:
                usecase = SyncEventsUsecase(
                    client=client,
                    events=SqlAlchemyEventRepository(session),
                    places=SqlAlchemyPlaceRepository(session),
                    sync_metadata=SqlAlchemySyncMetadataRepository(session),
                    uow=SqlAlchemyUnitOfWork(session),
                )
                return await usecase.do()
            finally:
                await client.aclose()
    finally:
        await engine.dispose()


@celery_app.task(name="itk_academy.sync_events", bind=True, max_retries=3)
def sync_events(self) -> dict:
    logger.info("sync_task_started", task_id=self.request.id)
    try:
        result = asyncio.run(_run_sync())
        logger.info("sync_task_finished", result=result)
        return result
    except Exception as exc:
        logger.exception("sync_task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
