"""Ubigeo router — cascading dropdowns for department / province / district (INEI Peru)."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)
router = APIRouter()

supabase_service = SupabaseService()


@router.get(
    "/departments",
    summary="List all departments",
    description="Returns all 25 Peruvian departments ordered alphabetically.",
)
async def list_departments() -> List[Dict[str, Any]]:
    try:
        # Query the view that returns DISTINCT departments directly
        response = (
            supabase_service.client.table("v_ubigeo_departments")
            .select("department_code, department")
            .order("department")
            .execute()
        )
        return [{"code": r["department_code"], "name": r["department"]} for r in response.data]
    except Exception as e:
        logger.error(f"Error fetching departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving departments",
        )


@router.get(
    "/provinces/{department_code}",
    summary="List provinces for a department",
    description="Returns provinces for the given 2-digit department code (e.g. '15' for Lima).",
)
async def list_provinces(department_code: str) -> List[Dict[str, Any]]:
    if len(department_code) != 2 or not department_code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="department_code must be exactly 2 digits",
        )
    try:
        # Query the view that returns DISTINCT provinces per department
        response = (
            supabase_service.client.table("v_ubigeo_provinces")
            .select("province_code, province")
            .eq("department_code", department_code)
            .order("province")
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No provinces found for department '{department_code}'",
            )
        return [{"code": r["province_code"], "name": r["province"]} for r in response.data]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching provinces for {department_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving provinces",
        )


@router.get(
    "/districts/{province_code}",
    summary="List districts for a province",
    description="Returns districts for the given 4-digit province code (e.g. '1501' for Lima).",
)
async def list_districts(province_code: str) -> List[Dict[str, Any]]:
    if len(province_code) != 4 or not province_code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="province_code must be exactly 4 digits",
        )
    try:
        response = (
            supabase_service.client.table("ubigeos")
            .select("ubigeo_code, district, population, area_km2")
            .eq("province_code", province_code)
            .order("district")
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No districts found for province '{province_code}'",
            )
        return [
            {
                "code": row["ubigeo_code"],
                "name": row["district"],
                "population": row.get("population"),
                "area_km2": row.get("area_km2"),
            }
            for row in response.data
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching districts for {province_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving districts",
        )
