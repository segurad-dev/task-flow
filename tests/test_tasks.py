"""Тесты CRUD задач: создание, чтение, обновление, удаление, кэш, уведомления.

Паттерн тестирования: Arrange → Act → Assert
- Arrange: подготовка данных (создать задачу)
- Act: выполнить тестируемое действие (обновить статус)
- Assert: проверить результат (status == "in_progress")
"""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_create_task(auth_client):
    """Создание задачи возвращает статус 201 и начальный статус 'todo'.

    Проверяем два инварианта:
    1. HTTP-код 201 Created (не 200, не 400)
    2. Начальный статус всегда "todo" (не зависит от переданных данных)
    """
    r = await auth_client.post("/tasks/", json={"title": "Задача", "project_id": 1})
    assert r.status_code == 201
    assert r.json()["status"] == "todo"


@pytest.mark.asyncio
async def test_get_task_not_found(auth_client):
    """Запрос несуществующей задачи возвращает ошибку 404.

    ID 99999 гарантированно не существует в тестовой БД.
    Проверяем что роутер корректно обрабатывает отсутствующий ресурс.
    """
    assert (await auth_client.get("/tasks/99999")).status_code == 404


@pytest.mark.asyncio
async def test_update_task_status(auth_client):
    """Обновление статуса задачи возвращает новый статус в ответе.

    Arrange: создаём задачу (статус по умолчанию "todo")
    Act: PATCH со статусом "in_progress"
    Assert: ответ содержит обновлённый статус
    """
    task_id = (
        await auth_client.post("/tasks/", json={"title": "T", "project_id": 1})
    ).json()["id"]
    r = await auth_client.patch(f"/tasks/{task_id}", json={"status": "in_progress"})
    assert r.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_delete_task(auth_client):
    """Удаление задачи возвращает 204, последующий GET — 404.

    Проверяем не только код ответа DELETE (204 No Content),
    но и реальное удаление через GET: задача должна исчезнуть из БД.
    """
    task_id = (
        await auth_client.post("/tasks/", json={"title": "Del", "project_id": 1})
    ).json()["id"]
    assert (await auth_client.delete(f"/tasks/{task_id}")).status_code == 204
    assert (await auth_client.get(f"/tasks/{task_id}")).status_code == 404


@pytest.mark.asyncio
async def test_create_task_no_auth(client):
    """Создание задачи без токена возвращает ошибку 401.

    Используем client (без auth), а не auth_client.
    Проверяем что эндпоинт защищён: FastAPI вернёт 401 до вызова обработчика.
    """
    assert (
        await client.post("/tasks/", json={"title": "T", "project_id": 1})
    ).status_code == 401


@pytest.mark.asyncio
async def test_get_tasks_no_auth(client):
    """Получение списка задач без токена возвращает ошибку 401."""
    assert (await client.get("/tasks/")).status_code == 401


@pytest.mark.asyncio
async def test_cache_invalidated_after_create(auth_client):
    """После создания задачи кэш инвалидируется и новая задача видна в списке.

    Воспроизводим сценарий инвалидации:
    1. GET /tasks/ → кэш заполняется (нет задачи "Новая")
    2. POST /tasks/ → задача создана, кэш удалён
    3. GET /tasks/ → кэш пуст, запрос к БД, видим "Новую"

    Без инвалидации шаг 3 вернул бы устаревший кэш без "Новой".
    """
    await auth_client.get("/tasks/")  # заполняем кэш
    await auth_client.post("/tasks/", json={"title": "Новая", "project_id": 1})
    r = await auth_client.get("/tasks/")
    assert any(t["title"] == "Новая" for t in r.json())


@pytest.mark.asyncio
async def test_notification_sent_on_status_change(auth_client):
    """При смене статуса задачи вызывается send_notification.delay ровно один раз.

    Мы не тестируем реальную отправку уведомления (это потребовало бы
    запущенного RabbitMQ + Worker). Вместо этого мокаем .delay() и проверяем
    что роутер вызвал его с правильным намерением.

    unittest.mock.patch подменяет send_notification.delay в модуле app.routers.tasks
    на MagicMock. После блока with — оригинал восстанавливается.

    mock.assert_called_once() проверяет что .delay() вызвали ровно 1 раз.
    Если бы роутер вызвал дважды или ни разу — тест упал бы.
    """
    task_id = (await auth_client.post("/tasks/", json={"title": "T", "project_id": 1})).json()["id"]
    with patch("app.routers.tasks.send_notification.delay") as mock:
        await auth_client.patch(f"/tasks/{task_id}", json={"status": "done"})
        mock.assert_called_once()
