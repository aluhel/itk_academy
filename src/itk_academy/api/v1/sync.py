from fastapi import APIRouter, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from itk_academy.worker.tasks import sync_events

router = APIRouter()


class SyncTriggerResponse(BaseModel):
    task_id: str
    status: str


@router.post(
    "/sync/trigger",
    response_model=SyncTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger events synchronization",
)
async def trigger_sync() -> SyncTriggerResponse:
    # `delay()` синхронно пишет задачу в Postgres-брокер — выносим в threadpool,
    # чтобы не блокировать event loop.
    task = await run_in_threadpool(sync_events.delay)
    return SyncTriggerResponse(task_id=task.id, status="queued")
