"""Supabase service for database operations."""

import logging
from typing import Any, Dict, Optional

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for managing Supabase operations."""

    def __init__(self):
        """Initialize Supabase service."""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("Supabase credentials not configured")

            self.client: Client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY,
            )
            logger.info("Supabase service initialized")
        except Exception as e:
            logger.warning(f"Supabase not fully configured: {str(e)}")
            self.client = None

    def create_project_query(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new project query record.

        Args:
            user_id: UUID of the user
            title: Project title
            description: Optional project description
            metadata: Optional metadata

        Returns:
            Created query record
        """
        if not self.client:
            raise RuntimeError("Supabase not configured")

        try:
            data = {
                "user_id": user_id,
                "title": title,
                "description": description,
                "status": "pending",
                "metadata": metadata or {},
            }

            response = self.client.table("project_queries").insert(data).execute()
            logger.info(f"Created project query: {response.data[0]['id']}")
            return response.data[0]

        except Exception as e:
            logger.error(f"Failed to create project query: {str(e)}")
            raise

    def get_role_id_by_name(self, role_name: str) -> Optional[int]:
        """Get role ID by role name."""
        if not self.client:
            return None

        try:
            response = (
                self.client.table("roles")
                .select("id")
                .eq("name", role_name)
                .single()
                .execute()
            )
            return response.data["id"]
        except Exception as e:
            logger.warning(f"Role '{role_name}' not found: {str(e)}")
            return None

    def get_role_name_by_id(self, role_id: int) -> Optional[str]:
        """Get role name by ID."""
        if not self.client or not role_id:
            return None
        try:
            response = (
                self.client.table("roles")
                .select("name")
                .eq("id", role_id)
                .single()
                .execute()
            )
            return response.data["name"]
        except Exception:
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email, then fetches role name separately."""
        if not self.client:
            return None

        try:
            response = (
                self.client.table("users")
                .select("*")
                .eq("email", email)
                .single()
                .execute()
            )
            user = response.data
            if user and user.get("role_id"):
                user["role_name"] = self.get_role_name_by_id(user["role_id"]) or "user"
            return user
        except Exception:
            return None

    def create_user(
        self,
        email: str,
        name: str,
        last_name: str,
        password_hash: str,
        role_id: int = 2,  # Default to regular user
    ) -> Dict[str, Any]:
        """Create a new user."""
        if not self.client:
            raise RuntimeError("Supabase not configured")

        try:
            data = {
                "email": email,
                "name": name,
                "last_name": last_name,
                "password_hash": password_hash,
                "role_id": role_id,
            }

            response = self.client.table("users").insert(data).execute()
            logger.info(f"Created user: {response.data[0]['id']}")
            return response.data[0]

        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise

    def update_last_login(self, user_id: str) -> None:
        """Update the last_login timestamp for a user."""
        if not self.client:
            return

        try:
            from datetime import datetime, timezone
            self.client.table("users").update(
                {"last_login": datetime.now(timezone.utc).isoformat()}
            ).eq("id", user_id).execute()
            logger.info(f"Updated last_login for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update last_login for user {user_id}: {str(e)}")
