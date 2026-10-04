import asyncio
import time
from dataclasses import dataclass

@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class BaseRateLimiter:
    async def check(self, client_id: str) -> RateLimitDecision:
        raise NotImplementedError


class InMemoryFixedWindowLimiter(BaseRateLimiter):
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._counts: dict[str, tuple[int, int]] = {}
        self._lock = asyncio.Lock()

    async def check(self, client_id: str) -> RateLimitDecision:
        now = int(time.time())
        bucket = now // self.window_seconds
        key = f"{client_id}:{bucket}"
        retry_after = self.window_seconds - (now % self.window_seconds)

        async with self._lock:
            count, stored_bucket = self._counts.get(key, (0, bucket))
            if stored_bucket != bucket:
                count = 0
            count += 1
            self._counts[key] = (count, bucket)

        allowed = count <= self.limit
        return RateLimitDecision(
            allowed=allowed,
            limit=self.limit,
            remaining=max(0, self.limit - count),
            retry_after=retry_after if not allowed else 0,
        )


class RedisFixedWindowLimiter(BaseRateLimiter):
    def __init__(self, redis_url: str, limit: int, window_seconds: int):
        try:
            from redis.asyncio import Redis
        except ImportError as exc:
            raise RuntimeError("The 'redis' package is required when REDIS_URL is configured") from exc
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.limit = limit
        self.window_seconds = window_seconds

    async def check(self, client_id: str) -> RateLimitDecision:
        now = int(time.time())
        bucket = now // self.window_seconds
        key = f"llm-gateway:rl:{client_id}:{bucket}"
        retry_after = self.window_seconds - (now % self.window_seconds)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, self.window_seconds + 2)
            count, _ = await pipe.execute()

        allowed = int(count) <= self.limit
        return RateLimitDecision(
            allowed=allowed,
            limit=self.limit,
            remaining=max(0, self.limit - int(count)),
            retry_after=retry_after if not allowed else 0,
        )
