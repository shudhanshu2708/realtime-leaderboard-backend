import asyncio

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import SessionLocal, get_session
from ..leaderboard import LeaderboardService
from ..models import AppUser
from ..schemas import LeaderboardRow, ScoreRequest, ScoreResponse
from ..security import current_user

router = APIRouter(prefix="/api", tags=["leaderboard"])


def get_service(request: Request) -> LeaderboardService:
    return request.app.state.leaderboard


@router.post("/scores", response_model=ScoreResponse, response_model_by_alias=True)
async def add_score(req: ScoreRequest, user: AppUser = Depends(current_user),
                    session: AsyncSession = Depends(get_session),
                    service: LeaderboardService = Depends(get_service)):
    return await service.add_score(session, user, req.points)


@router.get("/leaderboard", response_model=list[LeaderboardRow], response_model_by_alias=True)
async def leaderboard(session: AsyncSession = Depends(get_session),
                      service: LeaderboardService = Depends(get_service)):
    return await service.top(session, 10)


@router.get("/leaderboard/top/{n}", response_model=list[LeaderboardRow], response_model_by_alias=True)
async def top(n: int = Path(ge=1, le=100), session: AsyncSession = Depends(get_session),
              service: LeaderboardService = Depends(get_service)):
    return await service.top(session, n)


@router.get("/leaderboard/me", response_model=LeaderboardRow, response_model_by_alias=True)
async def my_rank(user: AppUser = Depends(current_user),
                  service: LeaderboardService = Depends(get_service)):
    return await service.my_rank(user)


@router.get("/leaderboard/stream")
async def stream(request: Request, service: LeaderboardService = Depends(get_service)):
    async def events():
        queue = service.register()
        try:
            async with SessionLocal() as session:  # short-lived session for the initial snapshot
                yield await service.snapshot_event(session)
            while not await request.is_disconnected():
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # comment line keeps proxies from closing the stream
        finally:
            service.unregister(queue)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
