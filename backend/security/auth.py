"""
IntentGuard — API Key Authentication & Access Control

Provides constant-time API key verification for protected mutating endpoints.
In development mode (API_KEY unset), requests pass through transparently
to guarantee zero friction for localhost recorded demos.
"""

import hmac
import logging
from typing import Optional
from fastapi import HTTPException, Security, Request, status
from fastapi.security import APIKeyHeader

from backend.config import get_settings

logger = logging.getLogger("intentguard.security.auth")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def check_api_key(request: Request, api_key_header: Optional[str] = None) -> bool:
    """
    Validate API key using constant-time comparison.
    
    Returns:
        True if authentication succeeds or dev bypass is active.
    Raises:
        HTTPException(401) if authentication is enforced and fails.
    """
    settings = get_settings()
    configured_key = settings.api_key

    # 1. Dev/Demo bypass: If no API key is configured in settings, allow request
    if not configured_key or configured_key.strip() == "":
        return True

    # 2. Extract key from X-API-Key header or Authorization: Bearer <key>
    candidate_key = api_key_header or request.headers.get("X-API-Key")
    if not candidate_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            candidate_key = auth_header[7:].strip()

    if not candidate_key:
        logger.warning(f"[AUTH] Missing API key for protected endpoint: {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Missing API key in X-API-Key or Authorization header.",
            },
        )

    # 3. Constant-time comparison to prevent timing side-channel attacks
    if not hmac.compare_digest(candidate_key.strip(), configured_key.strip()):
        logger.warning(f"[AUTH] Invalid API key attempt for endpoint: {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Invalid API key provided.",
            },
        )

    return True


async def require_api_key(request: Request, key: Optional[str] = Security(API_KEY_HEADER)):
    """FastAPI dependency for protecting sensitive endpoints."""
    check_api_key(request, key)
