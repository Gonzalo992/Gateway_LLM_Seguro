from functools import lru_cache

from app.config import get_settings
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.security.rate_limit import InMemoryFixedWindowLimiter, RedisFixedWindowLimiter


@lru_cache
def get_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "mock":
        return MockProvider(settings.mock_leak_mode, settings.mock_failure_mode)
    return OpenAICompatibleProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "",
        timeout_seconds=settings.llm_timeout_seconds,
    )


@lru_cache
def get_rate_limiter():
    settings = get_settings()
    if settings.redis_url:
        return RedisFixedWindowLimiter(
            redis_url=settings.redis_url,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return InMemoryFixedWindowLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
