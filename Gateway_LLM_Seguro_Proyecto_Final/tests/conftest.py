import os

os.environ["ENVIRONMENT"] = "test"
os.environ["GATEWAY_CLIENT_KEYS"] = "test-client-key"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["RATE_LIMIT_REQUESTS"] = "2"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
os.environ["SYSTEM_PROMPT_CANARY"] = "TEST_CANARY_123"
os.environ["SECURITY_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.dependencies import get_provider, get_rate_limiter


@pytest.fixture(autouse=True)
def reset_caches():
    get_settings.cache_clear()
    get_provider.cache_clear()
    get_rate_limiter.cache_clear()
    yield
    get_settings.cache_clear()
    get_provider.cache_clear()
    get_rate_limiter.cache_clear()


@pytest.fixture
def client():
    from importlib import reload
    import app.main as main

    reload(main)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"X-Gateway-Key": "test-client-key"}
