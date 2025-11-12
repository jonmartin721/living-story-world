from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..image import generate_scene_image
from .dependencies import get_validated_world_slug, load_world_async

router = APIRouter(prefix="/api/worlds/{slug}/images", tags=["images"])

# Thread pool for running sync operations
executor = ThreadPoolExecutor(max_workers=4)


class ImageGenerateRequest(BaseModel):
    chapter: Optional[int] = Field(None, ge=1, description="Chapter number")
    prompt: Optional[str] = Field(
        None, max_length=2000, description="Image generation prompt"
    )

    @field_validator("prompt")
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if v else v


@router.post("")
async def generate_image(
    request: ImageGenerateRequest,
    world_info: tuple[str, Path] = Depends(get_validated_world_slug),
):
    """Generate or regenerate a scene image"""
    slug, world_path = world_info
    cfg, state, dirs = await load_world_async(slug)

    # Determine prompt and chapter number
    prompt = request.prompt
    chapter_num = request.chapter

    if chapter_num is not None and not prompt:
        # Pull prompt from chapter record
        for ch in state.chapters:
            if ch.number == chapter_num:
                prompt = ch.scene_prompt
                break

    if not prompt:
        raise HTTPException(
            status_code=400, detail="No prompt provided or found for chapter"
        )

    # Generate image
    from ..settings import load_user_settings

    settings = load_user_settings()
    image_model = settings.default_image_model

    loop = asyncio.get_event_loop()
    image_path = await loop.run_in_executor(
        executor,
        generate_scene_image,
        dirs["base"],
        image_model,
        cfg.style_pack,
        prompt,
        chapter_num,
        "16:9",  # aspect_ratio
        True,  # bypass_cache - always bypass when regenerating via API
    )

    # Update chapter's scene path and metadata in world state if this is for a specific chapter
    if chapter_num is not None:
        for ch in state.chapters:
            if ch.number == chapter_num:
                import time

                from ..settings import load_user_settings

                # Update scene path
                ch.scene = f"/worlds/{slug}/media/scenes/{image_path.name}"

                # Update generation metadata
                ch.generated_at = time.strftime("%Y-%m-%d %I:%M:%S %p")

                # Update model used information
                settings = load_user_settings()
                ch.image_model_used = settings.default_image_model

                # Save the updated world state
                from ..world import save_world

                save_world(slug, cfg, state, dirs)
                break

    return {
        "scene": f"/worlds/{slug}/media/scenes/{image_path.name}",
        "chapter": chapter_num,
    }
