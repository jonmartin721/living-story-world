from __future__ import annotations

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..chapter_jobs import run_chapter_job
from ..settings import load_user_settings
from ..storage import WORLDS_DIR, validate_slug
from ..world import load_world, save_world

router = APIRouter(prefix="/api/worlds/{slug}/chapters", tags=["chapters"])

executor = ThreadPoolExecutor(max_workers=4)
active_jobs: Dict[str, asyncio.Queue] = {}

_settings_cache = None
_settings_cache_time = 0
_SETTINGS_CACHE_TTL = 60


def get_cached_settings():
    global _settings_cache, _settings_cache_time
    now = time.time()
    if _settings_cache is None or now - _settings_cache_time > _SETTINGS_CACHE_TTL:
        _settings_cache = load_user_settings()
        _settings_cache_time = now
    return _settings_cache


class ChapterGenerateRequest(BaseModel):
    no_images: bool = False
    chapter_length: str = Field(
        "medium", description="Chapter length: short, medium, or long"
    )


class ChoiceSelectionRequest(BaseModel):
    choice_id: str = Field(
        ..., description="ID of the selected choice, or 'auto' for AI selection"
    )


@router.post("")
async def start_chapter_generation(slug: str, request: ChapterGenerateRequest):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    job_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    active_jobs[job_id] = queue
    asyncio.create_task(run_chapter_job(slug, request, queue, job_id, executor))
    return {"job_id": job_id}


@router.get("/stream/{job_id}")
async def stream_chapter_progress(slug: str, job_id: str):
    try:
        validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    queue = active_jobs.get(job_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_stream():
        try:
            while True:
                update = await queue.get()
                if update["stage"] == "complete":
                    yield f"event: complete\ndata: {json.dumps(update['chapter'])}\n\n"
                    break
                if update["stage"] == "error":
                    yield f"event: error\ndata: {json.dumps({'error': update['error']})}\n\n"
                    break
                yield f"event: progress\ndata: {json.dumps(update)}\n\n"
        finally:
            active_jobs.pop(job_id, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{chapter_num}/content")
async def get_chapter_content(slug: str, chapter_num: int):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    _, state, dirs = load_world(slug)
    chapter_file = next(
        (chapter.filename for chapter in state.chapters if chapter.number == chapter_num),
        None,
    )
    if not chapter_file:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter_path = dirs["base"] / "chapters" / chapter_file
    if not chapter_path.exists():
        raise HTTPException(status_code=404, detail="Chapter file not found")

    return {"content": chapter_path.read_text(encoding="utf-8")}


@router.post("/{chapter_num}/select-choice")
async def select_choice(slug: str, chapter_num: int, request: ChoiceSelectionRequest):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    loop = asyncio.get_event_loop()
    cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

    chapter = next((item for item in state.chapters if item.number == chapter_num), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    if not chapter.choices:
        raise HTTPException(status_code=400, detail="Chapter has no choices")

    choice_id = request.choice_id
    if choice_id == "auto":
        import random

        choice_id = random.choice(chapter.choices).id

    selected_choice = next(
        (choice for choice in chapter.choices if choice.id == choice_id), None
    )
    if selected_choice is None:
        raise HTTPException(status_code=400, detail="Invalid choice ID")

    chapter.selected_choice_id = choice_id
    chapter.choice_reasoning = None
    await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

    return {
        "success": True,
        "choice": {
            "id": selected_choice.id,
            "text": selected_choice.text,
            "description": selected_choice.description,
        },
    }


@router.put("/{chapter_num}/reroll")
async def reroll_chapter(
    slug: str, chapter_num: int, request: Optional[ChapterGenerateRequest] = None
):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    job_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    active_jobs[job_id] = queue
    asyncio.create_task(
        run_chapter_job(
            slug,
            request or ChapterGenerateRequest(),
            queue,
            job_id,
            executor,
            chapter_num=chapter_num,
        )
    )
    return {"job_id": job_id}


@router.delete("/{chapter_num}")
async def delete_chapter(slug: str, chapter_num: int):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    loop = asyncio.get_event_loop()
    cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

    chapter_index = None
    chapter = None
    for index, item in enumerate(state.chapters):
        if item.number == chapter_num:
            chapter_index = index
            chapter = item
            break

    if chapter_index is None or chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter_path = dirs["base"] / "chapters" / chapter.filename
    if chapter_path.exists():
        chapter_path.unlink()

    scenes_dir = dirs["base"] / "media" / "scenes"
    if scenes_dir.exists():
        for scene_file in scenes_dir.glob(f"scene-{chapter_num:04d}-*.png"):
            scene_file.unlink()

    state.chapters.pop(chapter_index)
    await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)
    return {"success": True, "message": f"Chapter {chapter_num} deleted"}
