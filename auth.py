"""
auth.py — Supabase Auth verification helper for mobile app endpoints.

Provides FastAPI dependencies:
  - get_current_user(): requires valid Bearer token, raises 401 if invalid
  - get_optional_user(): returns None instead of raising if no/invalid token
"""
import os
import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("minpaku-dx.auth")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_supabase_client = None
_supabase_available = False

if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        _supabase_available = True
        logger.info("Supabase Auth initialized")
    except Exception as e:
        logger.warning("Supabase Auth初期化失敗（モバイルアプリ認証が無効）: %s", e)
else:
    logger.warning("SUPABASE_URL/SUPABASE_SERVICE_KEY が未設定 — モバイルアプリ認証が無効です")

# Optional bearer — allows endpoints to work without auth header present
_bearer_scheme = HTTPBearer(auto_error=False)


def _verify_token(token: str) -> dict:
    """
    Verify a Supabase access token and return user info dict.
    Returns: {"id": str, "email": str}
    Raises: HTTPException(401) if invalid.
    """
    if not _supabase_available or not _supabase_client:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured")

    try:
        user_response = _supabase_client.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return {
            "id": user.id,
            "email": user.email or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Supabase token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI dependency: extracts Bearer token, verifies with Supabase Auth.
    Returns user dict {"id": str, "email": str}.
    Raises 401 if token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return _verify_token(credentials.credentials)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict | None:
    """
    FastAPI dependency: same as get_current_user but returns None instead of raising.
    Useful for endpoints that optionally use auth.
    """
    if not credentials:
        return None
    try:
        return _verify_token(credentials.credentials)
    except HTTPException:
        return None
