"""Тесты эндпоинтов аналитики."""

import pytest


@pytest.mark.asyncio
async def test_project_stats(auth_client):
    """Статистика проекта корректно считает выполненные задачи и completion_rate.

    Создаёт проект, добавляет задачу, переводит в статус done,
    затем проверяет что done=1 и completion_rate=100%.
    """
    project_id = (await auth_client.post("/projects/", json={"title": "П"})).json()["id"]
    task_id = (await auth_client.post("/tasks/", json={"title": "З", "project_id": project_id})).json()["id"]
    await auth_client.patch(f"/tasks/{task_id}", json={"status": "done"})
    r = await auth_client.get(f"/analytics/project/{project_id}")
    assert r.status_code == 200
    assert r.json()["done"] == 1
    assert r.json()["completion_rate"] == 100.0
