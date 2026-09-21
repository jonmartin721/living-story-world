from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..generator import resolve_image_model
from ..image import generate_scene_result
from .dependencies import get_validated_world_slug, load_world_async
from .world_operations import world_operation

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
    with world_operation(world_info[0]):
        return await _generate_image(request, world_info)


async def _generate_image(request: ImageGenerateRequest, world_info: tuple[str, Path]):
    slug, world_path = world_info
    cfg, state, dirs = await load_world_async(slug)

    # Determine prompt and chapter number
    prompt = request.prompt
    chapter_num = request.chapter

    if chapter_num is not None and not prompt:
        # Pull prompt from chapter record
        for ch in state.chapters:
            if ch.number == chapter_num:
                # Prefer concise image_prompt, fallback to scene_prompt for backward compatibility
                prompt = (
                    ch.image_prompt
                    if hasattr(ch, "image_prompt") and ch.image_prompt
                    else ch.scene_prompt
                )
                break

    if not prompt:
        raise HTTPException(
            status_code=400, detail="No prompt provided or found for chapter"
        )

    # Generate image
    from ..settings import load_user_settings

    settings = load_user_settings()
    image_model = resolve_image_model(cfg, settings)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        partial(
            generate_scene_result,
            dirs["base"],
            image_model,
            cfg.style_pack,
            prompt,
            chapter_num,
            "16:9",
            True,
            revision=True,
        ),
    )
    image_path = result.image_path
    scene_filename = image_path.relative_to(dirs["base"] / "media" / "scenes").as_posix()

    if chapter_num is not None:
        for ch in state.chapters:
            if ch.number == chapter_num:
                import time

                ch.generated_at = time.strftime("%Y-%m-%d %I:%M:%S %p")
                ch.image_model_used = result.model
                ch.scene_filename = scene_filename

                from ..world import save_world

                save_world(slug, cfg, state, dirs)
                break

    return {
        "scene": f"/worlds/{slug}/media/scenes/{scene_filename}",
        "chapter": chapter_num,
    }
