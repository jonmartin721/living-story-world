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

from ..chapter_jobs import ProgressSink, run_chapter_job
from ..settings import load_user_settings
from ..storage import WORLDS_DIR, validate_slug
from ..world import load_world, save_world
from .chapter_progress import ChapterProgress
from .world_operations import active_world_operations, check_world_idle, world_operation

router = APIRouter(prefix="/api/worlds/{slug}/chapters", tags=["chapters"])

executor = ThreadPoolExecutor(max_workers=4)
active_jobs: Dict[str, ChapterProgress] = {}
_JOB_TTL = 600
_MAX_FINISHED_JOBS = 100
active_slug_jobs = active_world_operations

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


def _claim_job_slot(slug: str) -> None:
    check_world_idle(slug)


async def _run_job_with_cleanup(
    slug: str,
    request: ChapterGenerateRequest,
    queue: ProgressSink,
    job_id: str,
    *,
    chapter_num: Optional[int] = None,
) -> None:
    try:
        await run_chapter_job(
            slug,
            request,
            queue,
            job_id,
            executor,
            chapter_num=chapter_num,
        )
    finally:
        if isinstance(queue, ChapterProgress):
            if queue.finished_at is None:
                await queue.put({"stage": "error", "error": "Generation stopped before completing."})
            _prune_jobs()
            asyncio.get_running_loop().call_later(_JOB_TTL + 1, _prune_jobs)
        if active_slug_jobs.get(slug) == job_id:
            active_slug_jobs.pop(slug, None)


@router.post("")
async def start_chapter_generation(slug: str, request: ChapterGenerateRequest):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    _claim_job_slot(slug)
    job_id = str(uuid.uuid4())
    _prune_jobs()
    queue = ChapterProgress(slug, job_id)
    active_jobs[job_id] = queue
    active_slug_jobs[slug] = job_id
    asyncio.create_task(_run_job_with_cleanup(slug, request, queue, job_id))
    return {"job_id": job_id}


def _prune_jobs() -> None:
    finished = sorted(
        ((job.finished_at, job_id) for job_id, job in active_jobs.items() if job.finished_at is not None),
    )
    for index, (finished_at, job_id) in enumerate(finished):
        if time.monotonic() - finished_at >= _JOB_TTL or index < len(finished) - _MAX_FINISHED_JOBS:
            active_jobs.pop(job_id, None)


def _get_job(slug: str, job_id: str) -> ChapterProgress:
    try:
        validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _prune_jobs()
    job = active_jobs.get(job_id)
    if job is None or job.slug != slug:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    return job


@router.get("/jobs/current")
async def current_chapter_job(slug: str):
    try:
        validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    job_id = active_slug_jobs.get(slug)
    job = active_jobs.get(job_id) if job_id else None
    return job.snapshot() if job and job.finished_at is None else None


@router.get("/jobs/{job_id}")
async def chapter_job_status(slug: str, job_id: str):
    return _get_job(slug, job_id).snapshot()


@router.get("/stream/{job_id}")
async def stream_chapter_progress(slug: str, job_id: str):
    job = _get_job(slug, job_id)

    async def event_stream():
        async for update in job.updates():
            if update is None:
                yield ": keepalive\n\n"
            elif update["stage"] == "complete":
                yield f"event: complete\ndata: {json.dumps(update['chapter'])}\n\n"
            elif update["stage"] == "error":
                yield f"event: error\ndata: {json.dumps({'error': update['error']})}\n\n"
            else:
                yield f"event: progress\ndata: {json.dumps(update)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{chapter_num}/content")
async def get_chapter_content(slug: str, chapter_num: int):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    loop = asyncio.get_event_loop()
    _, state, dirs = await loop.run_in_executor(executor, load_world, slug)
    chapter_file = next(
        (
            chapter.filename
            for chapter in state.chapters
            if chapter.number == chapter_num
        ),
        None,
    )
    if not chapter_file:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter_path = dirs["base"] / "chapters" / chapter_file
    if not chapter_path.exists():
        raise HTTPException(status_code=404, detail="Chapter file not found")

    content = await loop.run_in_executor(executor, chapter_path.read_text, "utf-8")
    return {"content": content}


@router.post("/{chapter_num}/select-choice")
async def select_choice(slug: str, chapter_num: int, request: ChoiceSelectionRequest):
    with world_operation(slug):
        return await _select_choice(slug, chapter_num, request)


async def _select_choice(slug: str, chapter_num: int, request: ChoiceSelectionRequest):
    try:
        slug = validate_slug(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    loop = asyncio.get_event_loop()
    cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

    chapter = next(
        (item for item in state.chapters if item.number == chapter_num), None
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    if chapter is not state.chapters[-1]:
        raise HTTPException(
            status_code=409, detail="Only the latest chapter's choice can be changed."
        )
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

    _claim_job_slot(slug)
    job_id = str(uuid.uuid4())
    _prune_jobs()
    queue = ChapterProgress(slug, job_id)
    active_jobs[job_id] = queue
    active_slug_jobs[slug] = job_id
    asyncio.create_task(
        _run_job_with_cleanup(
            slug,
            request or ChapterGenerateRequest(),
            queue,
            job_id,
            chapter_num=chapter_num,
        )
    )
    return {"job_id": job_id}


@router.delete("/{chapter_num}")
async def delete_chapter(slug: str, chapter_num: int):
    with world_operation(slug):
        return await _delete_chapter(slug, chapter_num)


async def _delete_chapter(slug: str, chapter_num: int):
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
    if chapter_index != len(state.chapters) - 1:
        raise HTTPException(
            status_code=409,
            detail="Only the latest chapter can be deleted. Later chapters depend on it.",
        )

    state.chapters.pop(chapter_index)
    state.next_chapter = chapter_num
    if chapter.entity_context is not None:
        from ..models import WorldState

        restored = WorldState.from_dict(chapter.entity_context)
        state.characters = restored.characters
        state.locations = restored.locations
        state.items = restored.items
    await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)
    await loop.run_in_executor(
        executor, _delete_chapter_assets, dirs["base"], chapter.filename, chapter_num
    )
    return {"success": True, "message": f"Chapter {chapter_num} deleted"}


def _delete_chapter_assets(base_dir, chapter_filename: str, chapter_num: int) -> None:
    chapter_path = base_dir / "chapters" / chapter_filename
    if chapter_path.exists():
        chapter_path.unlink()

    scenes_dir = base_dir / "media" / "scenes"
    if scenes_dir.exists():
        for scene_file in scenes_dir.glob(f"scene-{chapter_num:04d}-*.png"):
            scene_file.unlink()
