"""Authentication service for JWT token management."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jwt import PyJWT, decode, encode

from app.core.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Service for managing JWT authentication."""

    def __init__(self):
        """Initialize auth service."""
        self.secret = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_hours = settings.JWT_EXPIRATION_HOURS
        self.jwt = PyJWT()

    def create_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT token.

        Args:
            data: Dictionary with token claims
            expires_delta: Optional token expiration delta

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.expiration_hours)

        to_encode.update({"exp": expire})

        encoded_jwt = encode(
            to_encode,
            self.secret,
            algorithm=self.algorithm,
        )

        logger.info(f"Created token for user: {data.get('sub', 'unknown')}")
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
            )
            return payload
        except Exception as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None

    def get_user_from_token(self, token: str) -> Optional[str]:
        """
        Extract user ID from token.

        Args:
            token: JWT token

        Returns:
            User ID or None if invalid
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")
        return None
