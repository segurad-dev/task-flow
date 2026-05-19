import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    r = await client.post(
        "/auth/register", json={"email": "u@test.com", "username": "u", "password": "p"}
    )
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    data = {"email": "dup@test.com", "username": "dup", "password": "p"}
    await client.post("/auth/register", json=data)
    r = await client.post("/auth/register", json=data)
    assert r.status_code == 400
