import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.dependencies import get_provider, get_rate_limiter
from app.logging_config import configure_logging
from app.models import ChatRequest, ChatResponse
from app.providers.base import LLMProvider
from app.security.auth import authenticate_client
from app.security.input_guard import sanitize_user_input
from app.security.output_guard import inspect_model_output
from app.security.rate_limit import BaseRateLimiter

settings = get_settings()
logger = configure_logging(settings.log_level)

app = FastAPI(
    title="Secure LLM Gateway",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "client_id": getattr(request.state, "client_id", None),
            },
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "REQUEST_REJECTED")
        message = exc.detail.get("message", "Request rejected")
    else:
        code = "REQUEST_REJECTED"
        message = "Request rejected"

    return JSONResponse(
        status_code=exc.status_code,
        content={"request_id": request_id, "error": code, "message": message},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.error(
        "unhandled_error",
        extra={
            "request_id": request_id,
            "endpoint": request.url.path,
            "security_event": "internal_error",
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "request_id": request_id,
            "error": "INTERNAL_ERROR",
            "message": "The gateway could not complete the request",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    x_gateway_key: str | None = Header(default=None, alias="X-Gateway-Key"),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_provider),
    limiter: BaseRateLimiter = Depends(get_rate_limiter),
):
    request_id = request.state.request_id
    client_id = authenticate_client(request, settings, x_gateway_key)

    # LLM10
    if settings.security_enabled:
        decision = await limiter.check(client_id)
        if not decision.allowed:
            logger.warning(
                "rate_limit_blocked",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "client_id": client_id,
                    "security_event": "rate_limit",
                },
            )
            raise HTTPException(
                status_code=429,
                detail={"code": "RATE_LIMITED", "message": "Request limit exceeded"},
                headers={"Retry-After": str(decision.retry_after)},
            )

    # LLM01
    user_message = payload.message
    if settings.security_enabled:
        result = sanitize_user_input(payload.message)
        if not result.allowed:
            logger.warning(
                "input_blocked",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "client_id": client_id,
                    "security_event": result.reason,
                },
            )
            raise HTTPException(
                status_code=400,
                detail={"code": "INPUT_REJECTED", "message": "Input rejected by security policy"},
            )
        user_message = result.sanitized

    # LLM02
    try:
        output = await provider.generate(
            system_prompt=settings.protected_system_prompt,
            user_message=user_message,
            model=settings.llm_model,
        )
    except Exception:
        logger.error(
            "upstream_provider_failure",
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "client_id": client_id,
                "provider": provider.name,
                "model": settings.llm_model,
            },
        )
        raise HTTPException(
            status_code=502,
            detail={"code": "UPSTREAM_ERROR", "message": "The language model provider is unavailable"},
        )

    # LLM07
    if settings.security_enabled:
        guard = inspect_model_output(output, settings.system_prompt, settings.system_prompt_canary)
        if not guard.allowed:
            logger.warning(
                "model_output_blocked",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "client_id": client_id,
                    "provider": provider.name,
                    "model": settings.llm_model,
                    "security_event": guard.reason,
                },
            )
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "UPSTREAM_OUTPUT_BLOCKED",
                    "message": "Model output was blocked by gateway security policy",
                },
            )

    return ChatResponse(
        request_id=request_id,
        provider=provider.name,
        model=settings.llm_model,
        output=output,
    )
