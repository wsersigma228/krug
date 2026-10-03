import os

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# Refuse the application database before importing the app.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://myuser:1234@localhost:5432/test_db"
)
if make_url(TEST_DATABASE_URL).database != "test_db":
    raise RuntimeError("Tests require a separate database named test_db")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-only-secret-key-not-for-use-outside-tests"

from backend.database import get_db
from backend.main import api


@pytest.fixture(scope="session", autouse=True)
def migrate_test_database():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def generous_auth_limits(monkeypatch):
    monkeypatch.setattr("backend.rate_limit.RATE_LIMIT_PER_MINUTE", 10000)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(
        TEST_DATABASE_URL.replace("postgresql+psycopg://", "postgresql+psycopg_async://"),
        poolclass=NullPool,
    )
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        await transaction.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db):
    async def override_db():
        yield db
    api.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
        yield client
    api.dependency_overrides.clear()


@pytest_asyncio.fixture
async def accounts(client):
    from uuid import uuid4
    users = []
    for role in ("author", "reader"):
        username = f"{role}_{uuid4().hex[:10]}"
        response = await client.post("/users", json={
            "username": username, "password": "test-password", "email": f"{username}@example.com",
        })
        assert response.status_code == 201, response.text
        user = response.json()
        tokens = (await client.post("/login", json={"username": username, "password": "test-password"})).json()
        user["tokens"] = tokens
        user["headers"] = {"Authorization": f"Bearer {tokens['access_token']}"}
        users.append(user)
    return users
