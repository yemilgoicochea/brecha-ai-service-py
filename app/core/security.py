"""Security utilities for JWT token handling."""

import logging
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

security = HTTPBearer()
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        Token payload with user information

    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials

    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Require admin role. Use as dependency on admin-only endpoints.

    Raises:
        HTTPException: 403 if user is not admin
    """
    logger.info(f"require_admin check — payload: {current_user}")
    if current_user.get("role") != "admin":
        logger.warning(f"Admin access denied — role={current_user.get('role')!r}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
