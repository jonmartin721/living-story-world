from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage import WORLDS_DIR
from ..world import load_world
from ..image import generate_scene_image

router = APIRouter(prefix="/api/worlds/{slug}/images", tags=["images"])

# Thread pool for running sync operations
executor = ThreadPoolExecutor(max_workers=4)


class ImageGenerateRequest(BaseModel):
    chapter: Optional[int] = None
    prompt: Optional[str] = None


@router.post("")
async def generate_image(slug: str, request: ImageGenerateRequest):
    """Generate or regenerate a scene image"""
    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    cfg, state, dirs = await asyncio.get_event_loop().run_in_executor(
        executor, load_world, slug
    )

    # Determine prompt and chapter number
    prompt = request.prompt
    chapter_num = request.chapter

    if chapter_num is not None and not prompt:
        # Pull prompt from chapter record
        for ch in state.chapters:
            if ch.get("number") == chapter_num:
                prompt = ch.get("scene_prompt")
                break

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="No prompt provided or found for chapter"
        )

    # Generate image
    loop = asyncio.get_event_loop()
    image_path = await loop.run_in_executor(
        executor,
        generate_scene_image,
        dirs["base"],
        cfg.image_model,
        cfg.style_pack,
        prompt,
        chapter_num
    )

    return {
        "scene": f"/worlds/{slug}/media/scenes/{image_path.name}",
        "chapter": chapter_num
    }
