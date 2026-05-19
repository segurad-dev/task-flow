import pytest


@pytest.mark.asyncio
async def test_create_task(auth_client):
    r = await auth_client.post("/tasks/", json={"title": "Задача", "project_id": 1})
    assert r.status_code == 201
    assert r.json()["status"] == "todo"


@pytest.mark.asyncio
async def test_get_task_not_found(auth_client):
    assert (await auth_client.get("/tasks/99999")).status_code == 404


@pytest.mark.asyncio
async def test_update_task_status(auth_client):
    task_id = (
        await auth_client.post("/tasks/", json={"title": "T", "project_id": 1})
    ).json()["id"]
    r = await auth_client.patch(f"/tasks/{task_id}", json={"status": "in_progress"})
    assert r.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_delete_task(auth_client):
    task_id = (
        await auth_client.post("/tasks/", json={"title": "Del", "project_id": 1})
    ).json()["id"]
    assert (await auth_client.delete(f"/tasks/{task_id}")).status_code == 204
    assert (await auth_client.get(f"/tasks/{task_id}")).status_code == 404
