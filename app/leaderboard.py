"""Leaderboard logic: MySQL = durable history, Redis sorted set = fast ranking index."""
import asyncio
import json
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AppUser, ScoreEntry
from .schemas import LeaderboardRow, ScoreResponse

KEY = "leaderboard:global"


class LeaderboardService:
    def __init__(self, redis: Redis):
        self.redis = redis
        # SSE subscribers live in this process's memory (same limitation as the Java version).
        self._clients: set[asyncio.Queue[str]] = set()

    async def rebuild_cache(self, session: AsyncSession) -> None:
        rows = (await session.execute(
            select(ScoreEntry.user_id, func.sum(ScoreEntry.points)).group_by(ScoreEntry.user_id)
        )).all()
        if rows:
            await self.redis.zadd(KEY, {str(uid): float(total) for uid, total in rows})

    async def add_score(self, session: AsyncSession, user: AppUser, points: int) -> ScoreResponse:
        session.add(ScoreEntry(user_id=user.id, points=points))
        await session.commit()  # commit durable record first, then update the cache
        member = str(user.id)
        total = await self.redis.zincrby(KEY, points, member)
        reverse_rank = await self.redis.zrevrank(KEY, member)
        rank = 0 if reverse_rank is None else reverse_rank + 1
        response = ScoreResponse(added=points, total_score=total, rank=rank,
                                 recorded_at=datetime.now(timezone.utc))
        await self._publish(session)
        return response

    async def top(self, session: AsyncSession, limit: int) -> list[LeaderboardRow]:
        entries = await self.redis.zrevrange(KEY, 0, limit - 1, withscores=True)
        if not entries:
            return []
        ids = [int(member) for member, _ in entries]
        users = (await session.execute(select(AppUser).where(AppUser.id.in_(ids)))).scalars().all()
        by_id = {u.id: u for u in users}
        result, rank = [], 1
        for member, score in entries:
            user = by_id.get(int(member))
            if user:
                result.append(LeaderboardRow(rank=rank, user_id=user.id, username=user.username, score=score))
                rank += 1
        return result

    async def my_rank(self, user: AppUser) -> LeaderboardRow:
        member = str(user.id)
        rank = await self.redis.zrevrank(KEY, member)
        score = await self.redis.zscore(KEY, member)
        return LeaderboardRow(rank=0 if rank is None else rank + 1, user_id=user.id,
                              username=user.username, score=score or 0)

    # ---- SSE ----
    @staticmethod
    def _format(rows: list[LeaderboardRow]) -> str:
        data = json.dumps([r.model_dump(by_alias=True) for r in rows])
        return f"event: leaderboard\ndata: {data}\n\n"

    def register(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._clients.add(q)
        return q

    def unregister(self, q: asyncio.Queue[str]) -> None:
        self._clients.discard(q)

    async def snapshot_event(self, session: AsyncSession) -> str:
        return self._format(await self.top(session, 10))

    async def _publish(self, session: AsyncSession) -> None:
        if not self._clients:
            return
        message = self._format(await self.top(session, 10))
        for q in list(self._clients):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:  # slow client: drop it
                self._clients.discard(q)
