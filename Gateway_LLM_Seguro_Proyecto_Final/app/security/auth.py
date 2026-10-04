import hashlib
import hmac

from fastapi import HTTPException, Request, status

from app.config import Settings


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def authenticate_client(request: Request, settings: Settings, x_gateway_key: str | None) -> str:
    if not x_gateway_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Gateway credential is required"},
        )

    valid = any(hmac.compare_digest(x_gateway_key, candidate) for candidate in settings.allowed_client_keys)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_INVALID", "message": "Gateway credential is invalid"},
        )

    client_id = fingerprint(x_gateway_key)
    request.state.client_id = client_id
    return client_id
