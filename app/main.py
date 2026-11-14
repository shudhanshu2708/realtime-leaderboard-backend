from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import SessionLocal, init_db
from .leaderboard import LeaderboardService
from .redis_client import create_redis
from .routers import auth, leaderboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    redis = getattr(app.state, "redis", None) or create_redis()
    app.state.redis = redis
    app.state.leaderboard = LeaderboardService(redis)
    async with SessionLocal() as session:
        await app.state.leaderboard.rebuild_cache(session)  # rebuild Redis from MySQL on startup
    yield
    await redis.aclose()


app = FastAPI(title="Real-Time Leaderboard API", version="1.0.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(leaderboard.router)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error bodies keep the same shape as the Java version: {"error": ..., "message": ...}
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "path", "query"))
    msg = first.get("msg", "Validation failed")
    return JSONResponse(status_code=400, content={
        "error": "Invalid request", "message": f"{field}: {msg}" if field else msg})


@app.exception_handler(StarletteHTTPException)
async def http_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail},
                        headers=getattr(exc, "headers", None))
