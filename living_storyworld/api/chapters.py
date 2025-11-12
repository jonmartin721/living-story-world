from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..storage import WORLDS_DIR, validate_slug
from ..world import load_world, save_world
from ..generator import generate_chapter, generate_chapter_summary
from ..image import generate_scene_image
from ..settings import load_user_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/worlds/{slug}/chapters", tags=["chapters"])

# Thread pool for running sync operations
executor = ThreadPoolExecutor(max_workers=4)

# Active generation jobs
active_jobs: Dict[str, asyncio.Queue] = {}

# Settings cache with TTL
_settings_cache = None
_settings_cache_time = 0
_SETTINGS_CACHE_TTL = 60


def get_cached_settings():
    """Get cached settings or load fresh if cache expired."""
    global _settings_cache, _settings_cache_time
    current_time = time.time()
    if _settings_cache is None or current_time - _settings_cache_time > _SETTINGS_CACHE_TTL:
        _settings_cache = load_user_settings()
        _settings_cache_time = current_time
    return _settings_cache


class ChapterGenerateRequest(BaseModel):
    no_images: bool = False
    chapter_length: str = Field("medium", description="Chapter length: short, medium, or long")


class ChoiceSelectionRequest(BaseModel):
    choice_id: str = Field(..., description="ID of the selected choice, or 'auto' for AI selection")


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

        # Auto-select a choice if the previous chapter has unselected choices
        if cfg.enable_choices and state.chapters:
            prev_chapter = state.chapters[-1]
            if prev_chapter.choices and not prev_chapter.selected_choice_id:
                import random
                selected_choice = random.choice(prev_chapter.choices)

                await queue.put({
                    "stage": "init",
                    "percent": 9,
                    "message": f"Auto-selecting choice: '{selected_choice.text[:50]}...'"
                })

                # Update previous chapter with the auto-selection
                prev_chapter.selected_choice_id = selected_choice.id
                prev_chapter.choice_reasoning = None

                # Save the updated state
                await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

        # Generate text with smooth progress updates
        await queue.put({
            "stage": "text",
            "percent": 10,
            "message": "Generating chapter text..."
        })

        # Start text generation in background
        text_start = time.time()
        text_future = loop.run_in_executor(
            executor,
            generate_chapter,
            dirs["base"],
            cfg,
            state,
            not request.no_images,  # make_scene_image
            request.chapter_length,
        )

        # Send progress updates while waiting (estimated ~40 seconds for text generation)
        estimated_duration = 40.0  # seconds
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
                "message": f"Chapter text... ({elapsed:.0f}s)"
            })

            try:
                await asyncio.wait_for(asyncio.shield(text_future), timeout=update_interval)
                break
            except asyncio.TimeoutError:
                continue

        chapter = await text_future
        text_duration = time.time() - text_start
        logger.info("Text generation completed: %.2fs", text_duration)

        # Read chapter markdown for summary generation
        chapter_md = (dirs["base"] / "chapters" / chapter.filename).read_text(encoding="utf-8")

        await queue.put({
            "stage": "post-processing",
            "percent": 70,
            "message": "Generating summary and image..."
        })

        # Start summary generation (runs in parallel with image)
        summary_task = asyncio.create_task(generate_chapter_summary(chapter_md, cfg))

        # Generate image if needed
        image_path = None
        actual_image_model = None
        if not request.no_images and chapter.scene_prompt:
            settings = get_cached_settings()
            actual_image_model = settings.default_image_model

            await queue.put({
                "stage": "image",
                "percent": 90,
                "message": f"Generating image ({actual_image_model})..."
            })

            # Start image generation in background
            image_start = time.time()
            image_future = loop.run_in_executor(
                executor,
                generate_scene_image,
                dirs["base"],
                actual_image_model,
                cfg.style_pack,
                chapter.scene_prompt,
                chapter.number
            )

            # Send progress updates while waiting (estimated ~8 seconds)
            estimated_image_duration = 8.0
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
                    "message": f"Scene image... ({elapsed:.0f}s)"
                })

                try:
                    await asyncio.wait_for(asyncio.shield(image_future), timeout=update_interval)
                    break
                except asyncio.TimeoutError:
                    continue

            image_path = await image_future
            image_duration = time.time() - image_start
            logger.info("Image generation completed: %.2fs", image_duration)

            await queue.put({
                "stage": "image",
                "percent": 94,
                "message": f"Image generation complete ({image_duration:.1f}s)"
            })

        # Wait for summary generation to complete
        await queue.put({
            "stage": "post-processing",
            "percent": 95,
            "message": "Finalizing summary..."
        })

        ai_summary = await summary_task
        chapter.ai_summary = ai_summary
        if ai_summary:
            logger.debug("Generated AI summary: %s...", ai_summary[:50])

        # Add metadata to chapter
        from datetime import datetime
        chapter.generated_at = datetime.utcnow().isoformat() + 'Z'
        # text_model_used is already set in generator.py, don't override it
        # Set image model only if it was actually generated
        if actual_image_model:
            chapter.image_model_used = actual_image_model

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
        from dataclasses import asdict
        chapter_data = {
            "number": chapter.number,
            "title": chapter.title,
            "filename": chapter.filename,
            "summary": chapter.summary,
            "scene_prompt": chapter.scene_prompt,
            "characters_in_scene": chapter.characters_in_scene,
            "choices": [asdict(c) for c in chapter.choices] if chapter.choices else [],
            "selected_choice_id": chapter.selected_choice_id,
            "choice_reasoning": chapter.choice_reasoning,
            "scene": f"/worlds/{slug}/media/scenes/{image_path.name}" if image_path else None,
            "generated_at": chapter.generated_at,
            "text_model_used": chapter.text_model_used,
            "image_model_used": chapter.image_model_used
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

        error_msg = f"{type(e).__name__}: {str(e)}"
        traceback_str = traceback.format_exc()
        logging.error(f"Full traceback: {traceback_str}")

        # Send sanitized error to client (no traceback or error details)
        await queue.put({
            "stage": "error",
            "error": "Chapter generation failed. Please check your settings and try again.",
            "job_id": job_id  # For support reference
        })
        logger.error("Chapter generation failed: %s", error_msg)


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
        if ch.number == chapter_num:
            chapter_file = ch.filename
            break

    if not chapter_file:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter_path = dirs["base"] / "chapters" / chapter_file
    if not chapter_path.exists():
        raise HTTPException(status_code=404, detail="Chapter file not found")

    content = chapter_path.read_text(encoding="utf-8")
    return {"content": content}


@router.post("/{chapter_num}/select-choice")
async def select_choice(slug: str, chapter_num: int, request: ChoiceSelectionRequest):
    """Record user's choice selection"""
    try:
        slug = validate_slug(slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    loop = asyncio.get_event_loop()
    cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

    # Find the chapter
    chapter_index = None
    chapter_data = None
    for i, ch in enumerate(state.chapters):
        if ch.number == chapter_num:
            chapter_index = i
            chapter_data = ch
            break

    if chapter_index is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Verify chapter has choices
    choices = chapter_data.choices
    if not choices:
        raise HTTPException(status_code=400, detail="Chapter has no choices")

    # Handle auto-selection
    choice_id = request.choice_id
    if choice_id == "auto":
        import random
        choice_id = random.choice(choices).id

    # Find the selected choice
    selected_choice = None
    for choice in choices:
        if choice.id == choice_id:
            selected_choice = choice
            break

    if selected_choice is None:
        raise HTTPException(status_code=400, detail="Invalid choice ID")

    # Update chapter with selection
    chapter_data.selected_choice_id = choice_id
    chapter_data.choice_reasoning = None
    state.chapters[chapter_index] = chapter_data

    # Save world state
    await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

    return {
        "success": True,
        "choice": {
            "id": selected_choice.id,
            "text": selected_choice.text,
            "description": selected_choice.description
        }
    }


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
            if ch.number == chapter_num:
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
        estimated_duration = 40.0
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
                "message": f"Chapter text... ({elapsed:.0f}s)"
            })

            try:
                await asyncio.wait_for(asyncio.shield(text_future), timeout=update_interval)
                break
            except asyncio.TimeoutError:
                continue

        chapter = await text_future
        text_duration = time.time() - text_start
        logger.info("Text generation (reroll) completed: %.2fs", text_duration)

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
        regen_image_model = None
        if not request.no_images and chapter.scene_prompt:
            settings = get_cached_settings()
            regen_image_model = settings.default_image_model

            await queue.put({
                "stage": "image",
                "percent": 90,
                "message": f"Generating image ({regen_image_model})..."
            })

            # Start image generation with smooth progress
            image_start = time.time()
            image_future = loop.run_in_executor(
                executor,
                generate_scene_image,
                dirs["base"],
                regen_image_model,
                cfg.style_pack,
                chapter.scene_prompt,
                chapter.number
            )

            # Send progress updates while waiting
            estimated_image_duration = 8.0
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
                    "message": f"Scene image... ({elapsed:.0f}s)"
                })

                try:
                    await asyncio.wait_for(asyncio.shield(image_future), timeout=update_interval)
                    break
                except asyncio.TimeoutError:
                    continue

            image_path = await image_future
            image_duration = time.time() - image_start
            logger.info("Image generation (reroll) completed: %.2fs", image_duration)

            await queue.put({
                "stage": "image",
                "percent": 94,
                "message": f"Image generation complete ({image_duration:.1f}s)"
            })

        # Update image model metadata if regenerated
        if regen_image_model:
            chapter.image_model_used = regen_image_model

        await queue.put({
            "stage": "saving",
            "percent": 95,
            "message": "Saving world state..."
        })

        # Update the chapter in state
        state.chapters[chapter_index] = chapter.__dict__

        # Save world state
        await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

        from dataclasses import asdict
        chapter_data = {
            "number": chapter.number,
            "title": chapter.title,
            "filename": chapter.filename,
            "summary": chapter.summary,
            "scene_prompt": chapter.scene_prompt,
            "characters_in_scene": chapter.characters_in_scene,
            "choices": [asdict(c) for c in chapter.choices] if chapter.choices else [],
            "selected_choice_id": chapter.selected_choice_id,
            "choice_reasoning": chapter.choice_reasoning,
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
        logger.error("Chapter reroll failed: %s", error_msg)


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
        if ch.number == chapter_num:
            chapter_index = i
            chapter_data = ch
            break

    if chapter_index is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Delete chapter file
    chapter_filename = chapter_data.filename
    if chapter_filename:
        chapter_path = dirs["base"] / "chapters" / chapter_filename
        if chapter_path.exists():
            chapter_path.unlink()

    # Delete scene image(s) if they exist
    # Scene images are named like: scene-0001-{hash}.png
    scenes_dir = dirs["base"] / "media" / "scenes"
    if scenes_dir.exists():
        pattern = f"scene-{chapter_num:04d}-*.png"
        for scene_file in scenes_dir.glob(pattern):
            scene_file.unlink()
            logger.debug("Deleted scene image: %s", scene_file.name)

    # Remove chapter from state
    state.chapters.pop(chapter_index)

    # Save world state
    await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

    return {"success": True, "message": f"Chapter {chapter_num} deleted"}
