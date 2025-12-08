"""Test configuration and fixtures."""

import os
import pytest
from fastapi.testclient import TestClient

# Set test environment variables
os.environ["GEMINI_API_KEY"] = "test-api-key"
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def client():
    """Create a test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_project_title():
    """Sample project title for testing."""
    return "Mejoramiento del servicio de agua potable en el distrito de San Juan"


@pytest.fixture
def mock_classification_response():
    """Mock classification response."""
    return {
        "labels": [
            {
                "label": "servicio de agua potable mediante red publica o pileta publica",
                "confianza": 0.95,
                "justificacion": "El título menciona explícitamente 'servicio de agua potable'.",
            }
        ]
    }
