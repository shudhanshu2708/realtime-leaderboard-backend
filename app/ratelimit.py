from fastapi import HTTPException, Request


def rate_limit(name: str, limit: int, window_seconds: int):
    """Allow limit requests per window_seconds per client IP, counted in Redis."""

    async def dependency(request: Request):
        redis = request.app.state.redis
        ip = request.client.host if request.client else "unknown"
        key = f"rl:{name}:{ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > limit:
            raise HTTPException(429, "Too many requests. Please slow down.")

    return dependency
