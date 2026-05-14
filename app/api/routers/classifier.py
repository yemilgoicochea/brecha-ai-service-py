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
                metadata={"submitted_at": "now()"},
            )
            query_id = query_record["id"]
        except Exception as e:
            logger.error(f"Failed to save query: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save query",
            )

        # Publish to Pub/Sub for worker processing
        try:
            message = {
                "query_id": query_id,
                "user_id": current_user.get("sub"),
                "title": request.title,
                "description": request.description or "",
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
            "processing_time_ms": query_record.get("processing_time_ms"),
            "created_at": query_record["created_at"],
        }

        # If completed, include classifications
        if query_record["status"] == "completed":
            try:
                classifications_response = (
                    supabase_service.client.table("project_classifications")
                    .select("*")
                    .eq("project_query_id", query_id)
                    .execute()
                )
                result["classifications"] = classifications_response.data
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
                .select("id, title, description, status, created_at, completed_at")
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
                "created_at": q["created_at"],
                "completed_at": q.get("completed_at"),
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
