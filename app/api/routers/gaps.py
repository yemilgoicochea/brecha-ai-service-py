"""Admin router for gap indicators CRUD."""

import logging
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.security import get_current_user, require_admin
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()

supabase_service = SupabaseService()


class GapCreate(BaseModel):
    sector_id: int
    name: str
    indicator_type: Literal["COBERTURA", "CALIDAD"]
    indicator_code: Optional[str] = None
    unit_measure: Optional[str] = None
    geographic_level: Optional[str] = None
    function_name: Optional[str] = None
    division_name: Optional[str] = None
    group_functional: Optional[str] = None
    service_name: Optional[str] = None
    typology: Optional[str] = None
    definition: Optional[str] = None
    justification: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    government_level_ids: List[int] = []


class GapUpdate(BaseModel):
    sector_id: Optional[int] = None
    name: Optional[str] = None
    indicator_type: Optional[Literal["COBERTURA", "CALIDAD"]] = None
    indicator_code: Optional[str] = None
    unit_measure: Optional[str] = None
    geographic_level: Optional[str] = None
    function_name: Optional[str] = None
    division_name: Optional[str] = None
    group_functional: Optional[str] = None
    service_name: Optional[str] = None
    typology: Optional[str] = None
    definition: Optional[str] = None
    justification: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    is_active: Optional[bool] = None
    government_level_ids: Optional[List[int]] = None


def _generate_indicator_code() -> str:
    """Generate a collision-safe indicator code: BRE-XXXXXXXX (8 hex chars from UUID4)."""
    return f"BRE-{uuid.uuid4().hex[:8].upper()}"


def _sync_government_levels(gap_id: int, level_ids: List[int]) -> None:
    """Replace all government levels for a gap (delete + re-insert)."""
    supabase_service.client.table("indicator_government_levels") \
        .delete().eq("gap_indicator_id", gap_id).execute()

    if level_ids:
        rows = [{"gap_indicator_id": gap_id, "government_level_id": lvl} for lvl in level_ids]
        supabase_service.client.table("indicator_government_levels").insert(rows).execute()


def _get_government_levels_for_gap(gap_id: int) -> List[Dict[str, Any]]:
    """Return government levels associated with a gap."""
    try:
        response = (
            supabase_service.client.table("indicator_government_levels")
            .select("government_level_id, government_levels(id, code, name)")
            .eq("gap_indicator_id", gap_id)
            .execute()
        )
        levels = []
        for row in response.data:
            gl = row.get("government_levels")
            if isinstance(gl, dict):
                levels.append({"id": gl["id"], "code": gl["code"], "name": gl["name"]})
            else:
                levels.append({"id": row["government_level_id"]})
        return levels
    except Exception:
        return []


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get(
    "/government-levels",
    summary="List government levels",
    description="Returns all government levels. Available to all authenticated users.",
)
async def list_government_levels(
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    try:
        response = (
            supabase_service.client.table("government_levels")
            .select("id, code, name, description")
            .eq("is_active", True)
            .order("id")
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Error listing government levels: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving government levels",
        )


@router.get(
    "/gaps",
    summary="List gap indicators",
    description="List all gap indicators with optional filters. Admin only.",
)
async def list_gaps(
    sector_id: Optional[int] = Query(None),
    indicator_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        query = (
            supabase_service.client.table("gap_indicators")
            .select(
                "id, sector_id, indicator_code, name, indicator_type, unit_measure, is_active, created_at, sectors(name)",
                count="exact",
            )
        )
        if sector_id is not None:
            query = query.eq("sector_id", sector_id)
        if indicator_type:
            query = query.eq("indicator_type", indicator_type)
        if is_active is not None:
            query = query.eq("is_active", is_active)

        offset = (page - 1) * limit
        response = query.order("name").range(offset, offset + limit - 1).execute()

        items = []
        for g in response.data:
            sector_name = None
            if isinstance(g.get("sectors"), dict):
                sector_name = g["sectors"].get("name")
            items.append({
                "id": g["id"],
                "sector_id": g["sector_id"],
                "sector_name": sector_name,
                "indicator_code": g.get("indicator_code"),
                "name": g["name"],
                "indicator_type": g["indicator_type"],
                "unit_measure": g.get("unit_measure"),
                "is_active": g["is_active"],
                "created_at": g["created_at"],
            })

        total = response.count or 0
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, -(-total // limit)),
        }
    except Exception as e:
        logger.error(f"Error listing gaps: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving gap indicators",
        )


@router.get(
    "/gaps/{gap_id}",
    summary="Get gap indicator by ID",
    description="Returns full gap indicator detail including government levels. Admin only.",
)
async def get_gap(
    gap_id: int,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        response = (
            supabase_service.client.table("gap_indicators")
            .select("*, sectors(id, name, code)")
            .eq("id", gap_id)
            .single()
            .execute()
        )
        g = response.data
        sector_info = g.pop("sectors", None)
        if isinstance(sector_info, dict):
            g["sector_name"] = sector_info.get("name")
            g["sector_code"] = sector_info.get("code")

        g["government_levels"] = _get_government_levels_for_gap(gap_id)
        return g
    except Exception as e:
        logger.error(f"Gap {gap_id} not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gap indicator not found",
        )


@router.post(
    "/gaps",
    status_code=status.HTTP_201_CREATED,
    summary="Create gap indicator",
    description="Create a new gap indicator with its government levels. Admin only.",
)
async def create_gap(
    data: GapCreate,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        government_level_ids = data.government_level_ids
        payload = data.model_dump(exclude={"government_level_ids"}, exclude_none=True)

        if not payload.get("indicator_code"):
            payload["indicator_code"] = _generate_indicator_code()

        response = (
            supabase_service.client.table("gap_indicators")
            .insert(payload)
            .execute()
        )
        gap = response.data[0]
        _sync_government_levels(gap["id"], government_level_ids)

        gap["government_levels"] = _get_government_levels_for_gap(gap["id"])
        logger.info(f"Gap indicator {gap['id']} created by admin {admin.get('sub')}")
        return gap
    except Exception as e:
        logger.error(f"Error creating gap: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating gap indicator",
        )


@router.put(
    "/gaps/{gap_id}",
    summary="Update gap indicator",
    description="Update gap indicator and its government levels. Admin only.",
)
async def update_gap(
    gap_id: int,
    data: GapUpdate,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        government_level_ids = data.government_level_ids
        payload = data.model_dump(exclude={"government_level_ids"}, exclude_none=True)

        if not payload and government_level_ids is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        if payload:
            response = (
                supabase_service.client.table("gap_indicators")
                .update(payload)
                .eq("id", gap_id)
                .execute()
            )
            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Gap indicator not found",
                )

        if government_level_ids is not None:
            _sync_government_levels(gap_id, government_level_ids)

        updated = (
            supabase_service.client.table("gap_indicators")
            .select("*")
            .eq("id", gap_id)
            .single()
            .execute()
        )
        gap = updated.data
        gap["government_levels"] = _get_government_levels_for_gap(gap_id)
        logger.info(f"Gap indicator {gap_id} updated by admin {admin.get('sub')}")
        return gap
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating gap {gap_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating gap indicator",
        )


@router.delete(
    "/gaps/{gap_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate gap indicator",
    description="Soft delete: sets is_active=False. Admin only.",
)
async def delete_gap(
    gap_id: int,
    admin: Dict[str, Any] = Depends(require_admin),
) -> Dict[str, Any]:
    try:
        response = (
            supabase_service.client.table("gap_indicators")
            .update({"is_active": False})
            .eq("id", gap_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gap indicator not found",
            )
        logger.info(f"Gap indicator {gap_id} deactivated by admin {admin.get('sub')}")
        return {"id": gap_id, "is_active": False, "message": "Gap indicator deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating gap {gap_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deactivating gap indicator",
        )
