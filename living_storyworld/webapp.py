from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .api import worlds, chapters, images, settings, generate

# Create FastAPI app
app = FastAPI(
    title="Living Storyworld",
    description="Web interface for Living Storyworld narrative generator",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(worlds.router)
app.include_router(chapters.router)
app.include_router(images.router)
app.include_router(settings.router)
app.include_router(generate.router)

# Serve world media files
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


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "Living Storyworld"}
