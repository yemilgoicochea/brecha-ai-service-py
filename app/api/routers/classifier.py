"""Classification router - Now publishes to Pub/Sub instead of calling Gemini directly."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import ClassificationRequest, ClassificationResponse
from app.services.pubsub_service import PubSubPublisher
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
pubsub_publisher = PubSubPublisher()
supabase_service = SupabaseService()


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit project for classification",
    description="Submits a project for classification. Returns immediately with query ID. Classification is done asynchronously by the worker.",
)
async def classify_project(
    request: ClassificationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Submit a project for classification.

    This endpoint now works asynchronously:
    1. Saves the query to Supabase with status='pending'
    2. Publishes to Pub/Sub for the worker to process
    3. Returns immediately with query ID for polling

    Args:
        request: Classification request with project title
        current_user: Current authenticated user

    Returns:
        Query ID and status for polling

    Raises:
        HTTPException: If submission fails
    """
    try:
        logger.info(f"Received classification request from user: {current_user.get('sub')}")

        # Create query record in Supabase
        try:
            query_record = supabase_service.create_project_query(
                user_id=current_user.get("sub"),
                title=request.title,
                description=request.description,
                ubigeo_code=request.ubigeo_code,
                department=request.department,
                province=request.province,
                district=request.district,
                metadata={"submitted_at": "now()"},
            )
            query_id = query_record["id"]
        except Exception as e:
            logger.error(f"Failed to save query: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save query",
            )

        # Determinar zona (urbana/rural) según población del distrito
        zone_type: str | None = None
        if request.ubigeo_code:
            try:
                ubigeo_row = (
                    supabase_service.client.table("ubigeos")
                    .select("population")
                    .eq("ubigeo_code", request.ubigeo_code)
                    .single()
                    .execute()
                )
                population = (ubigeo_row.data or {}).get("population")
                if population is not None:
                    zone_type = "urbano" if population >= 2000 else "rural"
                    logger.info(
                        f"Distrito {request.ubigeo_code}: población={population} → zona={zone_type}"
                    )
            except Exception as e:
                logger.warning(f"No se pudo obtener población para {request.ubigeo_code}: {e}")

        # Publish to Pub/Sub for worker processing
        try:
            message = {
                "query_id": query_id,
                "user_id": current_user.get("sub"),
                "title": request.title,
                "description": request.description or "",
                "ubigeo_code": request.ubigeo_code,
                "department": request.department,
                "province": request.province,
                "district": request.district,
                "zone_type": zone_type,
                "metadata": {"source": "api"},
            }
            pubsub_publisher.publish_classification_request(message)
        except Exception as e:
            logger.error(f"Failed to publish to Pub/Sub: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to queue classification request",
            )

        logger.info(f"Classification queued: {query_id}")
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "query_id": query_id,
                "status": "pending",
                "message": "Classification queued. Use query_id to check status.",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Classification error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during classification submission.",
        )


@router.get(
    "/query/{query_id}",
    summary="Get classification status and results",
    description="Get the status of a classification request and results if completed.",
)
async def get_query_status(
    query_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the status of a classification query.

    Args:
        query_id: UUID of the query
        current_user: Current authenticated user

    Returns:
        Query status and results if available
    """
    try:
        # Get query from Supabase
        try:
            response = (
                supabase_service.client.table("project_queries")
                .select("*")
                .eq("id", query_id)
                .single()
                .execute()
            )
            query_record = response.data
        except Exception as e:
            logger.warning(f"Query not found: {query_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found",
            )

        # Verify ownership
        if query_record["user_id"] != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Build response
        result = {
            "id": query_record["id"],
            "status": query_record["status"],
            "classification_status": query_record.get("classification_status"),
            "processing_time_ms": query_record.get("processing_time_ms"),
            "created_at": query_record["created_at"],
            "ubigeo_code": query_record.get("ubigeo_code"),
            "department": query_record.get("department"),
            "province": query_record.get("province"),
            "district": query_record.get("district"),
        }

        # If completed, include classifications with gap and sector names
        if query_record["status"] == "completed":
            try:
                classifications_response = (
                    supabase_service.client.table("project_classifications")
                    .select("id, confidence_score, justification, ranking_position, llm_model, gap_indicator_id, gap_indicators(name, indicator_type, sectors(name))")
                    .eq("project_query_id", query_id)
                    .order("ranking_position")
                    .execute()
                )
                classifications = []
                for c in classifications_response.data:
                    gap = c.pop("gap_indicators", None) or {}
                    sector = gap.pop("sectors", None) or {}
                    classifications.append({
                        **c,
                        "gap_name": gap.get("name"),
                        "indicator_type": gap.get("indicator_type"),
                        "sector_name": sector.get("name"),
                    })
                result["classifications"] = classifications
            except Exception as e:
                logger.warning(f"Failed to get classifications: {str(e)}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting query status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving query status",
        )


@router.get(
    "/categories",
    summary="List available categories",
    description="Returns all available classification categories with their definitions.",
)
async def list_categories() -> Dict[str, Any]:
    """
    List all available classification categories.

    Returns:
        Dictionary of category names and definitions
    """
    try:
        # Get from gap_indicators table
        try:
            response = (
                supabase_service.client.table("gap_indicators")
                .select("id, name, definition")
                .eq("is_active", True)
                .execute()
            )
            categories = {
                item["name"]: {
                    "id": item["id"],
                    "definition": item["definition"],
                }
                for item in response.data
            }
        except Exception as e:
            logger.warning(f"Failed to get categories from Supabase: {str(e)}")
            # Fallback to hardcoded categories
            categories = {
                "servicio de alcantarillado u otras formas de disposicion sanitaria de excretas": {
                    "id": 1,
                    "definition": "..."
                },
                "servicio de agua potable mediante red publica o pileta publica": {
                    "id": 2,
                    "definition": "..."
                },
            }

        return {
            "categories": categories,
            "total": len(categories),
        }
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving categories.",
        )


@router.post(
    "/query/{query_id}/retry",
    summary="Retry a failed classification",
    description="Re-queues an existing query. Only works on completed queries with no results or error queries.",
)
async def retry_query(
    query_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        try:
            response = (
                supabase_service.client.table("project_queries")
                .select("*")
                .eq("id", query_id)
                .single()
                .execute()
            )
            query_record = response.data
        except Exception:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found")

        if query_record["user_id"] != current_user.get("sub"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if query_record["status"] not in ("completed", "error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only completed or error queries can be retried",
            )

        # Block retry if classifications already exist
        existing = (
            supabase_service.client.table("project_classifications")
            .select("id", count="exact")
            .eq("project_query_id", query_id)
            .execute()
        )
        if existing.count and existing.count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query already has classifications",
            )

        supabase_service.client.table("project_queries").update(
            {"status": "pending", "processing_time_ms": None}
        ).eq("id", query_id).execute()

        message = {
            "query_id": query_id,
            "user_id": current_user.get("sub"),
            "title": query_record.get("title", ""),
            "description": query_record.get("description") or "",
            "metadata": {"source": "retry"},
        }
        pubsub_publisher.publish_classification_request(message)

        logger.info(f"Retry queued for query: {query_id}")
        return {"query_id": query_id, "status": "pending", "message": "Classification retried."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retry error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry classification",
        )


@router.get(
    "/history",
    summary="Get user's classification history",
    description="Returns all classification queries for the authenticated user.",
)
async def get_user_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> list:
    """
    Get the classification history for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        List of user's queries with status
    """
    try:
        # Get all queries for the user
        try:
            response = (
                supabase_service.client.table("project_queries")
                .select("id, title, description, status, classification_status, ubigeo_code, department, province, district, created_at, updated_at")
                .eq("user_id", current_user.get("sub"))
                .order("created_at", desc=True)
                .execute()
            )
            queries = response.data
        except Exception as e:
            logger.error(f"Failed to get user history: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve history",
            )

        # Format response
        history = [
            {
                "query_id": q["id"],
                "title": q.get("title", "Sin título"),
                "description": q.get("description", ""),
                "status": q["status"],
                "classification_status": q.get("classification_status"),
                "ubigeo_code": q.get("ubigeo_code"),
                "department": q.get("department"),
                "province": q.get("province"),
                "district": q.get("district"),
                "created_at": q["created_at"],
                "completed_at": q.get("updated_at") if q["status"] == "completed" else None,
            }
            for q in queries
        ]

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving history.",
        )
