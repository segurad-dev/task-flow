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


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post(
        "/auth/register", json={"email": "l@test.com", "username": "l", "password": "pass"}
    )
    r = await client.post("/auth/login", data={"username": "l@test.com", "password": "pass"})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    r = await client.post("/auth/login", data={"username": "l@test.com", "password": "wrong"})
    assert r.status_code == 401
