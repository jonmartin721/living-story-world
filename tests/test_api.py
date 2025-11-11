"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from living_storyworld.webapp import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test basic server health."""
    # The root endpoint should at least return something
    response = client.get("/")
    assert response.status_code in [200, 404]  # Either serves index.html or 404


def test_api_settings_get(client):
    """Test GET /api/settings endpoint."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()

    # Should return settings object
    assert isinstance(data, dict)
    assert "text_provider" in data
    assert "image_provider" in data


def test_api_worlds_list(client):
    """Test GET /api/worlds endpoint."""
    response = client.get("/api/worlds")
    assert response.status_code == 200
    data = response.json()

    # Should return list of worlds
    assert isinstance(data, list)


def test_api_invalid_world(client):
    """Test accessing non-existent world."""
    response = client.get("/api/worlds/nonexistent-world-12345")
    assert response.status_code == 404


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get("/api/settings", headers={"Origin": "http://localhost:8001"})
    assert response.status_code == 200
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


def test_security_headers(client):
    """Test security headers are present."""
    response = client.get("/api/settings")
    assert response.status_code == 200

    # Check for security headers
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert "x-xss-protection" in headers
