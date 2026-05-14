"""Admin router for sectors management."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_admin
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()

supabase_service = SupabaseService()


@router.get(
    "/sectors",
    summary="List all sectors",
    description="Returns all sectors with their gap indicator count. Admin only.",
)
async def list_sectors(
    admin: Dict[str, Any] = Depends(require_admin),
) -> list:
    try:
        response = (
            supabase_service.client.table("sectors")
            .select("*, gap_indicators(count)")
            .order("name")
            .execute()
        )
        sectors = []
        for s in response.data:
            gap_count = 0
            if isinstance(s.get("gap_indicators"), list) and s["gap_indicators"]:
                gap_count = s["gap_indicators"][0].get("count", 0)
            sectors.append({
                "id": s["id"],
                "code": s["code"],
                "name": s["name"],
                "transparency_name": s.get("transparency_name"),
                "pdf_filename": s.get("pdf_filename"),
                "is_active": s["is_active"],
                "created_at": s["created_at"],
                "gap_count": gap_count,
            })
        return sectors
    except Exception as e:
        logger.error(f"Error listing sectors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving sectors",
        )


@router.get(
    "/sectors/{sector_id}",
    summary="Get sector by ID",
    description="Returns sector details. Admin only.",
)
async def get_sector(
    sector_id: int,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        response = (
            supabase_service.client.table("sectors")
            .select("*")
            .eq("id", sector_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Sector {sector_id} not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sector not found",
        )


@router.patch(
    "/sectors/{sector_id}/toggle",
    summary="Toggle sector active status",
    description="Activates or deactivates a sector. Admin only.",
)
async def toggle_sector(
    sector_id: int,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        current = (
            supabase_service.client.table("sectors")
            .select("is_active")
            .eq("id", sector_id)
            .single()
            .execute()
        )
        if not current.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sector not found",
            )

        new_status = not current.data["is_active"]
        response = (
            supabase_service.client.table("sectors")
            .update({"is_active": new_status})
            .eq("id", sector_id)
            .execute()
        )
        return {"id": sector_id, "is_active": new_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling sector {sector_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating sector",
        )
