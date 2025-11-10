from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .api import worlds, chapters, images, settings, generate

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # SECURITY: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # SECURITY: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # SECURITY: Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # SECURITY: Enforce HTTPS in production (max-age=1 year)
        if os.environ.get("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# Create FastAPI app
app = FastAPI(
    title="Living Storyworld",
    description="Web interface for Living Storyworld narrative generator",
    version="1.0.0"
)

# SECURITY: Configure CORS with environment-based origins
# Format: comma-separated list of allowed origins
# Default: localhost for development
allowed_origins_str = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:9999,http://127.0.0.1:9999"
)
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit methods only
    allow_headers=["Content-Type", "Authorization"],  # Explicit headers only
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Include API routers
app.include_router(worlds.router)
app.include_router(chapters.router)
app.include_router(images.router)
app.include_router(settings.router)
app.include_router(generate.router)

# Serve world media files
# SECURITY WARNING: This serves ALL world files without authentication.
# In a production deployment with multiple users, implement access control
# to prevent unauthorized access to private worlds. Consider:
# - User authentication/authorization
# - Per-world access tokens
# - Serving files through controlled endpoints instead of StaticFiles
from .storage import WORLDS_DIR
app.mount("/worlds", StaticFiles(directory=str(WORLDS_DIR)), name="worlds")

# Serve frontend static files
web_dir = Path(__file__).parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

# Root endpoint serves the main HTML
@app.get("/")
async def index():
    """Serve the main web interface"""
    html_path = Path(__file__).parent / "web" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "Living Storyworld API", "docs": "/docs"}


@app.on_event("startup")
async def validate_configuration():
    """Validate configuration on startup."""
    import logging
    from .settings import load_user_settings

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    settings = load_user_settings()

    # Warn about missing API keys
    warnings = []
    if not settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
        warnings.append("OpenAI API key not configured")
    if not settings.replicate_api_token and not os.environ.get("REPLICATE_API_TOKEN"):
        warnings.append("Replicate API token not configured")

    if warnings:
        for warning in warnings:
            logging.warning(f"CONFIG: {warning}")
        logging.info("Some API keys are missing. Configure them via /api/settings or environment variables.")

    # Check writable directories
    try:
        WORLDS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = WORLDS_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        logging.info(f"WORLDS_DIR is writable: {WORLDS_DIR}")
    except Exception as e:
        logging.error(f"WORLDS_DIR not writable: {e}")
        raise RuntimeError(f"Cannot write to worlds directory: {e}")

    logging.info("Configuration validation complete")
    logging.info(f"Allowed CORS origins: {', '.join(allowed_origins)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Living Storyworld"}
