from __future__ import annotations

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

from ..storage import WORLDS_DIR, validate_slug
from ..world import load_world, save_world
from ..generator import generate_chapter
from ..image import generate_scene_image

router = APIRouter(prefix="/api/worlds/{slug}/chapters", tags=["chapters"])

# Thread pool for running sync operations
executor = ThreadPoolExecutor(max_workers=4)

# Active generation jobs
active_jobs: Dict[str, asyncio.Queue] = {}


class ChapterGenerateRequest(BaseModel):
    focus: Optional[str] = Field(None, max_length=1000, description="Focus/direction for the chapter")
    no_images: bool = False
    chapter_length: str = Field("medium", description="Chapter length: short, medium, or long")

    @validator('focus')
    def strip_whitespace(cls, v):
        return v.strip() if v else v


@router.post("")
async def start_chapter_generation(slug: str, request: ChapterGenerateRequest):
    """Start chapter generation and return job ID for SSE streaming"""
    try:
        slug = validate_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    # Create job
    job_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    active_jobs[job_id] = queue

    # Start background task
    asyncio.create_task(run_chapter_generation(slug, request, queue, job_id))

    return {"job_id": job_id}


@router.get("/stream/{job_id}")
async def stream_chapter_progress(slug: str, job_id: str):
    """SSE stream for chapter generation progress"""
    try:
        slug = validate_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
                elif update["stage"] == "error":
                    yield f"event: error\ndata: {json.dumps({'error': update['error']})}\n\n"
                    break
                else:
                    yield f"event: progress\ndata: {json.dumps(update)}\n\n"
        finally:
            # Clean up job
            if job_id in active_jobs:
                del active_jobs[job_id]

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def run_chapter_generation(slug: str, request: ChapterGenerateRequest, queue: asyncio.Queue, job_id: str):
    """Background task to generate chapter with progress updates"""
    import traceback
    import time
    try:
        loop = asyncio.get_event_loop()

        # Send initial progress
        await queue.put({
            "stage": "init",
            "percent": 5,
            "message": "Loading world..."
        })

        # Load world (sync operation in executor)
        cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

        await queue.put({
            "stage": "init",
            "percent": 8,
            "message": "World loaded, preparing generation..."
        })

        # Generate text with smooth progress updates
        await queue.put({
            "stage": "text",
            "percent": 10,
            "message": "Calling OpenAI API for chapter text..."
        })

        # Start text generation in background
        text_start = time.time()
        text_future = loop.run_in_executor(
            executor,
            generate_chapter,
            dirs["base"],
            cfg,
            state,
            request.focus,
            not request.no_images,  # make_scene_image
            request.chapter_length,
        )

        # Send progress updates while waiting (estimated ~25-35 seconds for text generation)
        estimated_duration = 30.0  # seconds
        start_percent = 10
        end_percent = 85
        update_interval = 0.5  # Update every 0.5 seconds

        while not text_future.done():
            elapsed = time.time() - text_start
            progress_ratio = min(elapsed / estimated_duration, 1.0)
            # Use easing function for smoother progress (slower at end)
            eased_progress = 1 - (1 - progress_ratio) ** 2
            current_percent = int(start_percent + (end_percent - start_percent) * eased_progress)

            await queue.put({
                "stage": "text",
                "percent": current_percent,
                "message": f"Generating chapter text... ({elapsed:.0f}s)"
            })

            try:
                await asyncio.wait_for(asyncio.shield(text_future), timeout=update_interval)
                break
            except asyncio.TimeoutError:
                continue

        chapter = await text_future
        text_duration = time.time() - text_start
        print(f"[TIMING] Text generation: {text_duration:.2f}s", flush=True)

        await queue.put({
            "stage": "text",
            "percent": 89,
            "message": f"Text generation complete ({text_duration:.1f}s)"
        })

        # Generate image if needed
        image_path = None
        if not request.no_images and chapter.scene_prompt:
            await queue.put({
                "stage": "image",
                "percent": 90,
                "message": f"Calling Replicate API ({cfg.image_model})..."
            })

            # Start image generation in background
            image_start = time.time()
            image_future = loop.run_in_executor(
                executor,
                generate_scene_image,
                dirs["base"],
                cfg.image_model,
                cfg.style_pack,
                chapter.scene_prompt,
                chapter.number
            )

            # Send progress updates while waiting (flux-dev ~8-12s, flux-schnell ~2-4s)
            estimated_image_duration = 10.0 if cfg.image_model == "flux-dev" else 3.0
            start_percent = 90
            end_percent = 93
            update_interval = 0.5

            while not image_future.done():
                elapsed = time.time() - image_start
                progress_ratio = min(elapsed / estimated_image_duration, 1.0)
                eased_progress = 1 - (1 - progress_ratio) ** 2
                current_percent = int(start_percent + (end_percent - start_percent) * eased_progress)

                await queue.put({
                    "stage": "image",
                    "percent": current_percent,
                    "message": f"Generating scene image... ({elapsed:.0f}s)"
                })

                try:
                    await asyncio.wait_for(asyncio.shield(image_future), timeout=update_interval)
                    break
                except asyncio.TimeoutError:
                    continue

            image_path = await image_future
            image_duration = time.time() - image_start
            print(f"[TIMING] Image generation: {image_duration:.2f}s", flush=True)

            await queue.put({
                "stage": "image",
                "percent": 94,
                "message": f"Image generation complete ({image_duration:.1f}s)"
            })

        # Update state
        await queue.put({
            "stage": "saving",
            "percent": 95,
            "message": "Saving world state..."
        })

        state.chapters.append(chapter.__dict__)
        state.next_chapter += 1

        await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

        # Build response
        chapter_data = {
            "number": chapter.number,
            "title": chapter.title,
            "filename": chapter.filename,
            "summary": chapter.summary,
            "scene_prompt": chapter.scene_prompt,
            "characters_in_scene": chapter.characters_in_scene,
            "scene": f"/worlds/{slug}/media/scenes/{image_path.name}" if image_path else None
        }

        await queue.put({
            "stage": "complete",
            "percent": 100,
            "message": "Chapter complete!",
            "chapter": chapter_data
        })

    except Exception as e:
        import logging
        logging.exception(f"Chapter generation failed for job {job_id}")

        # SECURITY: Log full details server-side but send generic error to client
        error_msg = f"{type(e).__name__}: {str(e)}"
        traceback_str = traceback.format_exc()
        logging.error(f"Full traceback: {traceback_str}")

        # Send sanitized error to client (no traceback)
        await queue.put({
            "stage": "error",
            "error": "Chapter generation failed. Please check your settings and try again.",
            "error_type": type(e).__name__,
            "job_id": job_id  # For support reference
        })
        print(f"ERROR in chapter generation: {error_msg}")


@router.get("/{chapter_num}/content")
async def get_chapter_content(slug: str, chapter_num: int):
    """Get the markdown content of a specific chapter"""
    try:
        slug = validate_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    cfg, state, dirs = load_world(slug)

    # Find chapter
    chapter_file = None
    for ch in state.chapters:
        if ch.get("number") == chapter_num:
            chapter_file = ch.get("filename")
            break

    if not chapter_file:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter_path = dirs["base"] / "chapters" / chapter_file
    if not chapter_path.exists():
        raise HTTPException(status_code=404, detail="Chapter file not found")

    content = chapter_path.read_text(encoding="utf-8")
    return {"content": content}


@router.put("/{chapter_num}/reroll")
async def reroll_chapter(slug: str, chapter_num: int, request: Optional[ChapterGenerateRequest] = None):
    """Regenerate text for a specific chapter"""
    try:
        slug = validate_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    # Start regeneration job
    job_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    active_jobs[job_id] = queue

    # Use default options if not provided
    if request is None:
        request = ChapterGenerateRequest()

    # Start background task
    asyncio.create_task(run_chapter_reroll(slug, chapter_num, request, queue, job_id))

    return {"job_id": job_id}


async def run_chapter_reroll(slug: str, chapter_num: int, request: ChapterGenerateRequest, queue: asyncio.Queue, job_id: str):
    """Background task to regenerate a chapter"""
    import traceback
    import time
    try:
        loop = asyncio.get_event_loop()

        await queue.put({
            "stage": "init",
            "percent": 5,
            "message": "Loading world..."
        })

        cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

        # Find the chapter in state
        chapter_index = None
        old_chapter_data = None
        for i, ch in enumerate(state.chapters):
            if ch.get("number") == chapter_num:
                chapter_index = i
                old_chapter_data = ch
                break

        if chapter_index is None:
            await queue.put({
                "stage": "error",
                "error": f"Chapter {chapter_num} not found"
            })
            return

        await queue.put({
            "stage": "text",
            "percent": 10,
            "message": "Calling OpenAI API for chapter text..."
        })

        # Generate new chapter text with smooth progress
        text_start = time.time()
        text_future = loop.run_in_executor(
            executor,
            generate_chapter,
            dirs["base"],
            cfg,
            state,
            request.focus,
            request.no_images,  # Respect the no_images flag from request
        )

        # Send progress updates while waiting
        estimated_duration = 30.0
        start_percent = 10
        end_percent = 85
        update_interval = 0.5

        while not text_future.done():
            elapsed = time.time() - text_start
            progress_ratio = min(elapsed / estimated_duration, 1.0)
            eased_progress = 1 - (1 - progress_ratio) ** 2
            current_percent = int(start_percent + (end_percent - start_percent) * eased_progress)

            await queue.put({
                "stage": "text",
                "percent": current_percent,
                "message": f"Generating chapter text... ({elapsed:.0f}s)"
            })

            try:
                await asyncio.wait_for(asyncio.shield(text_future), timeout=update_interval)
                break
            except asyncio.TimeoutError:
                continue

        chapter = await text_future
        text_duration = time.time() - text_start
        print(f"[TIMING] Text generation (reroll): {text_duration:.2f}s", flush=True)

        # Override chapter number to match the one we're replacing
        chapter.number = chapter_num
        chapter.filename = old_chapter_data.get("filename")

        await queue.put({
            "stage": "text",
            "percent": 89,
            "message": f"Text generation complete ({text_duration:.1f}s)"
        })

        # Generate image if needed
        image_path = None
        if not request.no_images and chapter.scene_prompt:
            await queue.put({
                "stage": "image",
                "percent": 90,
                "message": f"Calling Replicate API ({cfg.image_model})..."
            })

            # Start image generation with smooth progress
            image_start = time.time()
            image_future = loop.run_in_executor(
                executor,
                generate_scene_image,
                dirs["base"],
                cfg.image_model,
                cfg.style_pack,
                chapter.scene_prompt,
                chapter.number
            )

            # Send progress updates while waiting
            estimated_image_duration = 10.0 if cfg.image_model == "flux-dev" else 3.0
            start_percent = 90
            end_percent = 93
            update_interval = 0.5

            while not image_future.done():
                elapsed = time.time() - image_start
                progress_ratio = min(elapsed / estimated_image_duration, 1.0)
                eased_progress = 1 - (1 - progress_ratio) ** 2
                current_percent = int(start_percent + (end_percent - start_percent) * eased_progress)

                await queue.put({
                    "stage": "image",
                    "percent": current_percent,
                    "message": f"Generating scene image... ({elapsed:.0f}s)"
                })

                try:
                    await asyncio.wait_for(asyncio.shield(image_future), timeout=update_interval)
                    break
                except asyncio.TimeoutError:
                    continue

            image_path = await image_future
            image_duration = time.time() - image_start
            print(f"[TIMING] Image generation (reroll): {image_duration:.2f}s", flush=True)

            await queue.put({
                "stage": "image",
                "percent": 94,
                "message": f"Image generation complete ({image_duration:.1f}s)"
            })

        await queue.put({
            "stage": "saving",
            "percent": 95,
            "message": "Saving world state..."
        })

        # Update the chapter in state
        state.chapters[chapter_index] = chapter.__dict__

        # Save world state
        await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

        chapter_data = {
            "number": chapter.number,
            "title": chapter.title,
            "filename": chapter.filename,
            "summary": chapter.summary,
            "scene_prompt": chapter.scene_prompt,
            "characters_in_scene": chapter.characters_in_scene,
            "scene": f"/worlds/{slug}/media/scenes/{image_path.name}" if image_path else old_chapter_data.get("scene")
        }

        await queue.put({
            "stage": "complete",
            "percent": 100,
            "message": "Chapter regenerated!",
            "chapter": chapter_data
        })

    except Exception as e:
        import logging
        logging.exception(f"Chapter reroll failed for job {job_id}")

        # SECURITY: Log full details server-side but send generic error to client
        error_msg = f"{type(e).__name__}: {str(e)}"
        traceback_str = traceback.format_exc()
        logging.error(f"Full traceback: {traceback_str}")

        # Send sanitized error to client (no traceback)
        await queue.put({
            "stage": "error",
            "error": "Chapter regeneration failed. Please check your settings and try again.",
            "error_type": type(e).__name__,
            "job_id": job_id  # For support reference
        })
        print(f"ERROR in chapter reroll: {error_msg}")


@router.delete("/{chapter_num}")
async def delete_chapter(slug: str, chapter_num: int):
    """Delete a specific chapter"""
    try:
        slug = validate_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    loop = asyncio.get_event_loop()
    cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

    # Find the chapter in state
    chapter_index = None
    chapter_data = None
    for i, ch in enumerate(state.chapters):
        if ch.get("number") == chapter_num:
            chapter_index = i
            chapter_data = ch
            break

    if chapter_index is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Delete chapter file
    chapter_filename = chapter_data.get("filename")
    if chapter_filename:
        chapter_path = dirs["base"] / "chapters" / chapter_filename
        if chapter_path.exists():
            chapter_path.unlink()

    # Delete scene image if it exists
    scene_path = chapter_data.get("scene")
    if scene_path:
        # Extract filename from path like "/worlds/slug/media/scenes/filename.webp"
        import re
        match = re.search(r'/scenes/(.+)$', scene_path)
        if match:
            scene_filename = match.group(1)
            scene_file = dirs["base"] / "media" / "scenes" / scene_filename
            if scene_file.exists():
                scene_file.unlink()

    # Remove chapter from state
    state.chapters.pop(chapter_index)

    # Save world state
    await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

    return {"success": True, "message": f"Chapter {chapter_num} deleted"}
