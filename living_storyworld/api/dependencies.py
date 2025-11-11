"""FastAPI dependencies for common operations."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, Path as PathParam

from ..storage import WORLDS_DIR, validate_slug
from ..world import load_world
from ..models import WorldConfig, WorldState

# Thread executor for blocking operations
executor = ThreadPoolExecutor(max_workers=4)


def get_validated_world_slug(slug: str = PathParam(..., description="World slug")) -> Tuple[str, Path]:
    """Validate slug and check world exists.

    Args:
        slug: World slug from path parameter

    Returns:
        Tuple of (validated_slug, world_path)

    Raises:
        HTTPException: 400 if slug is invalid, 404 if world not found
    """
    try:
        validated_slug = validate_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    world_path = WORLDS_DIR / validated_slug
    if not world_path.exists():
        raise HTTPException(status_code=404, detail="World not found")

    return validated_slug, world_path


async def load_world_async(slug: str) -> Tuple[WorldConfig, WorldState, dict]:
    """Async wrapper for load_world.

    Args:
        slug: World slug to load

    Returns:
        Tuple of (config, state, directories)
    """
    return await asyncio.get_event_loop().run_in_executor(
        executor, load_world, slug
    )


async def get_world_data(slug: str = PathParam(..., description="World slug")) -> Tuple[str, WorldConfig, WorldState, dict]:
    """Validate slug and load world data.

    Combined dependency that validates the slug and loads world data asynchronously.

    Args:
        slug: World slug from path parameter

    Returns:
        Tuple of (slug, config, state, directories)

    Raises:
        HTTPException: 400 if slug is invalid, 404 if world not found
    """
    validated_slug, world_path = get_validated_world_slug(slug)
    cfg, state, dirs = await load_world_async(validated_slug)
    return validated_slug, cfg, state, dirs
