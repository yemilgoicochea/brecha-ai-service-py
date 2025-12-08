"""Pydantic schemas for API requests and responses."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ClassificationLabel(BaseModel):
    """Single classification label with confidence and justification."""

    label: str = Field(..., description="Category label name")
    confianza: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )
    justificacion: str = Field(..., description="Justification for the classification")


class ClassificationRequest(BaseModel):
    """Request model for project classification."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Project title to classify",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate and clean the title."""
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty or only whitespace")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"title": "Mejoramiento del servicio de agua potable en el distrito de San Juan"}
            ]
        }
    }


class ClassificationResponse(BaseModel):
    """Response model for project classification."""

    labels: List[ClassificationLabel] = Field(
        default_factory=list,
        description="List of classification labels",
    )
    error: Optional[str] = Field(
        None,
        description="Error message if classification failed",
    )
    detalle_error: Optional[str] = Field(
        None,
        description="Detailed error information",
    )
    raw_response: Optional[str] = Field(
        None,
        description="Raw response from the model (only included if parsing failed)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "labels": [
                        {
                            "label": "servicio de agua potable mediante red publica o pileta publica",
                            "confianza": 0.95,
                            "justificacion": "El título menciona explícitamente 'servicio de agua potable', que corresponde directamente a esta categoría.",
                        }
                    ]
                }
            ]
        }
    }
