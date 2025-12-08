"""Test API endpoints."""

import pytest
from fastapi import status


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"


def test_list_categories(client):
    """Test list categories endpoint."""
    response = client.get("/api/v1/categories")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "categories" in data
    assert "total" in data
    assert data["total"] > 0
    assert isinstance(data["categories"], dict)


def test_classify_endpoint_validation(client):
    """Test classification endpoint validation."""
    # Test with empty title
    response = client.post(
        "/api/v1/classify",
        json={"title": ""}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test with whitespace only
    response = client.post(
        "/api/v1/classify",
        json={"title": "   "}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test with missing title field
    response = client.post(
        "/api/v1/classify",
        json={}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_classify_endpoint_structure(client, sample_project_title):
    """Test classification endpoint response structure."""
    response = client.post(
        "/api/v1/classify",
        json={"title": sample_project_title}
    )
    
    # Should return 200 even if classification fails
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "labels" in data
    assert isinstance(data["labels"], list)
