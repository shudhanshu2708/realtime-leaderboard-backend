import asyncio

import pytest

pytestmark = pytest.mark.asyncio


async def register(client, name, pw="strongpass123"):
    r = await client.post("/api/auth/register", json={"username": name, "password": pw})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def test_register_login_and_duplicates(client):
    r = await client.post("/api/auth/register", json={"username": "alice", "password": "strongpass123"})
    assert r.status_code == 201 and r.json()["tokenType"] == "Bearer"
    assert (await client.post("/api/auth/register",
                              json={"username": "alice", "password": "strongpass123"})).status_code == 409
    ok = await client.post("/api/auth/login", json={"username": "alice", "password": "strongpass123"})
    assert ok.status_code == 200 and ok.json()["token"]
    bad = await client.post("/api/auth/login", json={"username": "alice", "password": "wrongpass"})
    assert bad.status_code == 401
    assert bad.json() == {"error": "Invalid username or password"}


async def test_validation_error_shape(client):
    r = await client.post("/api/auth/register", json={"username": "al", "password": "x"})
    assert r.status_code == 400
    assert r.json()["error"] == "Invalid request"


async def test_scores_requires_auth(client):
    assert (await client.post("/api/scores", json={"points": 5})).status_code == 401
    assert (await client.get("/api/leaderboard/me")).status_code == 401
    bad = await client.post("/api/scores", json={"points": 5}, headers={"Authorization": "Bearer junk"})
    assert bad.status_code == 401


async def test_scoring_ranking_and_top(client):
    a, b = await register(client, "alice"), await register(client, "bob")
    r = await client.post("/api/scores", json={"points": 25}, headers=a)
    assert r.status_code == 200
    body = r.json()
    assert body["added"] == 25 and body["totalScore"] == 25 and body["rank"] == 1 and "recordedAt" in body
    await client.post("/api/scores", json={"points": 40}, headers=b)
    await client.post("/api/scores", json={"points": 20}, headers=a)  # alice = 45

    rows = (await client.get("/api/leaderboard")).json()
    assert [(x["rank"], x["username"], x["score"]) for x in rows] == [(1, "alice", 45), (2, "bob", 40)]
    assert set(rows[0]) == {"rank", "userId", "username", "score"}

    me = (await client.get("/api/leaderboard/me", headers=b)).json()
    assert me["rank"] == 2 and me["score"] == 40

    top1 = (await client.get("/api/leaderboard/top/1")).json()
    assert len(top1) == 1 and top1[0]["username"] == "alice"
    assert (await client.get("/api/leaderboard/top/101")).status_code == 400
    assert (await client.get("/api/leaderboard/top/0")).status_code == 400


async def test_points_validation(client):
    h = await register(client, "carol")
    assert (await client.post("/api/scores", json={"points": 0}, headers=h)).status_code == 400
    assert (await client.post("/api/scores", json={"points": 1_000_001}, headers=h)).status_code == 400


async def test_unranked_user_rank_zero(client):
    h = await register(client, "dave")
    me = (await client.get("/api/leaderboard/me", headers=h)).json()
    assert me["rank"] == 0 and me["score"] == 0


async def test_cache_rebuild_from_db(client):
    from app.database import SessionLocal
    from app.main import app
    h = await register(client, "erin")
    await client.post("/api/scores", json={"points": 70}, headers=h)
    await app.state.redis.flushall()  # simulate lost Redis
    assert (await client.get("/api/leaderboard")).json() == []
    async with SessionLocal() as s:
        await app.state.leaderboard.rebuild_cache(s)
    assert (await client.get("/api/leaderboard")).json()[0]["score"] == 70


async def test_sse_snapshot_and_push(client):
    from app.main import app
    h = await register(client, "frank")
    service = app.state.leaderboard
    # Exercise the stream generator's contract directly (httpx's ASGI transport buffers responses).
    q = service.register()
    from app.database import SessionLocal
    async with SessionLocal() as s:
        first = await service.snapshot_event(s)
    assert first.startswith("event: leaderboard\ndata: ")
    await client.post("/api/scores", json={"points": 9}, headers=h)
    msg = await asyncio.wait_for(q.get(), 2)
    assert msg.startswith("event: leaderboard") and '"frank"' in msg and '"userId"' in msg
    service.unregister(q)
