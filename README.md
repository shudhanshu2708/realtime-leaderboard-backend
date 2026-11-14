# Real-Time Leaderboard API (FastAPI)

Python port of the Java/Spring Boot project. **FastAPI, MySQL, Redis, JWT and Server-Sent Events (SSE).**
Same endpoints, same JSON field names (camelCase), same data model.

| Java / Spring | Python / FastAPI |
|---|---|
| Spring Web | FastAPI |
| Spring Data JPA (Hibernate) | SQLAlchemy 2.0 (async) + aiomysql |
| StringRedisTemplate | redis-py (`redis.asyncio`) |
| Spring Security + jjwt | PyJWT + bcrypt, `Depends(current_user)` |
| `SseEmitter` | `StreamingResponse` + per-client `asyncio.Queue` |
| `@Valid` DTO records | Pydantic models |

## Requirements
- Python 3.11+
- Docker Desktop (or local MySQL 8+ and Redis 7+)

## Run locally
```bash
docker compose up -d                  # MySQL + Redis
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```
- API: http://localhost:8080
- Interactive docs (Swagger): http://localhost:8080/docs

Configuration via environment variables or a `.env` file (see `.env.example`):
`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_EXPIRATION_SECONDS`.

## Endpoints
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | no | `{"username","password"}` → 201 `{"token","tokenType"}`; 409 if taken |
| POST | `/api/auth/login` | no | 401 on bad credentials |
| POST | `/api/scores` | JWT | `{"points": 1..1000000}` adds to your total |
| GET | `/api/leaderboard` | no | top 10 |
| GET | `/api/leaderboard/top/{n}` | no | n = 1..100 |
| GET | `/api/leaderboard/me` | JWT | your rank/score (rank 0 = not ranked yet) |
| GET | `/api/leaderboard/stream` | no | SSE: snapshot on connect, then top-10 after each score |

Quick SSE test: `curl -N http://localhost:8080/api/leaderboard/stream`

## Tests
```bash
pip install -r requirements-dev.txt
pytest
```
Tests use SQLite + fakeredis, so no Docker is needed.

## Project structure
```text
app/
├── main.py          app setup, startup (create tables, rebuild Redis), error handlers
├── config.py        settings from env
├── database.py      async SQLAlchemy engine/session
├── models.py        AppUser, ScoreEntry
├── schemas.py       request/response models
├── security.py      JWT, bcrypt, current_user dependency
├── leaderboard.py   Redis ranking + SSE broadcast
└── routers/         auth.py, leaderboard.py
```

## Known limitations (same as the original, plus notes)
1. **Ties:** equal scores are ordered by Redis (lexicographic member order). Define a tie-break policy.
2. **SSE scaling:** subscribers are in process memory; with several instances use Redis Pub/Sub.
3. **Idempotency:** add a client request ID + unique constraint to stop duplicate submissions on retry.
4. **Consistency:** the DB commit and Redis increment aren't atomic. The DB commit happens first, so
   a crash can leave Redis behind; the startup rebuild repairs it.
5. **Rate limiting / roles** are not included.
6. **Schema:** `create_all` only creates missing tables. Use Alembic migrations for real deployments.
7. Change `JWT_SECRET` before deploying.
