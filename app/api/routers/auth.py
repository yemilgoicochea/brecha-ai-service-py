"""Authentication router for login, register, and user management."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from app.core.security import get_current_user
from app.services.auth_service import AuthService
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()

# Services
auth_service = AuthService()
supabase_service = SupabaseService()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., min_length=1, max_length=150, description="First name")
    last_name: str = Field(..., min_length=1, max_length=150, description="Last name")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Login response with token."""

    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """User data response."""

    id: str
    email: str
    name: str
    last_name: str


def build_user_payload(user: Dict[str, Any]) -> Dict[str, Any]:
    """Build a normalized user payload for API responses."""
    first_name = (user.get("name") or "").strip()
    last_name = (user.get("last_name") or "").strip()
    full_name = " ".join(part for part in [first_name, last_name] if part).strip()

    return {
        "id": user["id"],
        "email": user["email"],
        "name": full_name or first_name or user["email"],
        "last_name": last_name,
        "role": user.get("role_name", "user"),
    }


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account.",
)
async def register(request: RegisterRequest) -> LoginResponse:
    """
    Register a new user.

    Args:
        request: Registration request with email, first name, last name, and password

    Returns:
        Login response with access token
    """
    try:
        # Check if user exists
        existing_user = supabase_service.get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password
        password_hash = pwd_context.hash(request.password)

        # Get user role ID
        role_id = supabase_service.get_role_id_by_name("user")
        if not role_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role configuration error",
            )

        # Create user
        user = supabase_service.create_user(
            email=request.email,
            name=request.name,
            last_name=request.last_name,
            password_hash=password_hash,
            role_id=role_id,
        )

        # Create token
        token = auth_service.create_token({
            "sub": user["id"],
            "email": user["email"],
            "role": "user",
        })

        logger.info(f"User registered: {user['id']}")

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=build_user_payload(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user",
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with email and password.",
)
async def login(request: LoginRequest) -> LoginResponse:
    """
    Login user and return access token.

    Args:
        request: Login request with email and password

    Returns:
        Login response with access token
    """
    try:
        # Get user
        user = supabase_service.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Verify password
        if not pwd_context.verify(request.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Create token
        token = auth_service.create_token({
            "sub": user["id"],
            "email": user["email"],
            "role": user.get("role_name", "user"),
        })

        logger.info(f"User logged in: {user['id']}")

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=build_user_payload(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.get(
    "/me",
    summary="Get current user token payload",
)
async def me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout user (client-side token invalidation).",
)
async def logout() -> Dict[str, str]:
    """
    Logout user.

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint is for future use with token blacklisting.

    Returns:
        Success message
    """
    logger.info("User logged out")
    return {"message": "Logged out successfully"}
