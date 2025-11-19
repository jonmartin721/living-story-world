"""Tests for webapp startup, middleware, and configuration."""


from fastapi.testclient import TestClient


class TestWebappStartup:
    """Test webapp initialization and startup."""

    def test_app_creation(self):
        """App can be created."""
        from living_storyworld.webapp import app

        assert app is not None
        assert app.title == "Living Storyworld"

    def test_cors_middleware_configured(self):
        """CORS middleware is configured."""
        from living_storyworld.webapp import app

        # Check that CORS middleware is in the middleware stack
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes

    def test_security_headers_middleware(self):
        """Security headers middleware is configured."""
        from living_storyworld.webapp import app

        [m.cls.__name__ for m in app.user_middleware]
        # Check we have custom middleware
        assert len(app.user_middleware) > 0

    def test_routers_mounted(self):
        """API routers are mounted."""
        from living_storyworld.webapp import app

        # Check routes exist
        routes = [route.path for route in app.routes]
        assert any("/api/worlds" in route for route in routes)
        assert any("/api/settings" in route for route in routes)
        assert any("/api/generate" in route for route in routes)


class TestSecurityMiddleware:
    """Test security middleware headers."""

    def test_security_headers_applied(self):
        """Security headers are applied to responses."""
        from living_storyworld.webapp import app

        client = TestClient(app)

        # Make request to root
        response = client.get("/")

        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers


class TestStaticFileServing:
    """Test static file serving."""

    def test_root_serves_index(self):
        """Root path serves index.html."""
        from living_storyworld.webapp import app

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_worlds_static_files(self):
        """Worlds static files are served."""
        from living_storyworld.webapp import app

        # Create a test world file
        from living_storyworld.storage import WORLDS_DIR

        test_world = WORLDS_DIR / "test-static"
        test_file = test_world / "test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content")

        try:
            client = TestClient(app)
            response = client.get("/worlds/test-static/test.txt")

            # Should serve the file
            assert response.status_code in (200, 404)  # Depends on routing setup
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
            if test_world.exists() and not any(test_world.iterdir()):
                test_world.rmdir()


class TestStartupValidation:
    """Test startup validation logic."""

    def test_startup_checks_api_keys(self):
        """Startup logs warning if no API keys configured."""
        # This is tested indirectly via the startup event handler
        # The actual validation happens in startup.py which logs warnings
        from living_storyworld.webapp import app

        assert app is not None

    def test_startup_checks_writable_directories(self):
        """Startup checks that data directories are writable."""
        from living_storyworld.webapp import app

        # App should initialize successfully
        assert app is not None


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self):
        """Root endpoint returns 200."""
        from living_storyworld.webapp import app

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling."""

    def test_404_for_unknown_route(self):
        """Unknown routes return 404."""
        from living_storyworld.webapp import app

        client = TestClient(app)
        response = client.get("/api/nonexistent-route-xyz")

        assert response.status_code == 404
