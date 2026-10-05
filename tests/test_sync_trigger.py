from unittest.mock import MagicMock, patch

from httpx import AsyncClient


async def test_trigger_sync_enqueues_task(client: AsyncClient) -> None:
    fake_task = MagicMock()
    fake_task.id = "test-task-id-1234"

    with patch(
        "itk_academy.api.v1.sync.sync_events.delay",
        return_value=fake_task,
    ) as mock_delay:
        response = await client.post("/api/sync/trigger")

    assert response.status_code == 200
    assert response.json() == {"task_id": "test-task-id-1234", "status": "queued"}
    mock_delay.assert_called_once()
