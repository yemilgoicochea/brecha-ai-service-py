"""Classification router."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import ClassificationRequest, ClassificationResponse
from app.services.classifier_service import ClassifierService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize classifier service
classifier_service = ClassifierService()


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify project title",
    description="Classifies a public infrastructure project title into one or more service categories.",
)
async def classify_project(request: ClassificationRequest) -> Dict[str, Any]:
    """
    Classify a project title using Gemini AI.

    Args:
        request: Classification request with project title

    Returns:
        Classification result with labels, confidence scores, and justifications

    Raises:
        HTTPException: If classification fails
    """
    try:
        logger.info(f"Received classification request for title: {request.title[:50]}...")
        
        result = await classifier_service.classify(request.title)
        
        logger.info(f"Classification completed with {len(result.get('labels', []))} labels")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except Exception as e:
        logger.error(f"Classification error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during classification. Please try again later.",
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
        categories = classifier_service.get_categories()
        return {
            "categories": categories,
            "total": len(categories),
        }
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving categories.",
        )
