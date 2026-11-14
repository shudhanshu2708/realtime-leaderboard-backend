import os

# Use SQLite + fake Redis so tests need no Docker. Must be set before importing the app.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

import fakeredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app, lifespan


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.state.redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    async with lifespan(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    app.state.redis = None
