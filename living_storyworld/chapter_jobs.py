from __future__ import annotations

import asyncio
import logging
import random
import time
import traceback
from datetime import datetime, timezone
from functools import partial
from typing import Optional

from .generator import (
    find_latest_scene_path,
    generate_chapter_draft,
    generate_chapter_summary,
    persist_generated_chapter,
    resolve_image_model,
    serialize_chapter_response,
)
from .image import generate_scene_image
from .settings import load_user_settings
from .world import load_world, save_world

logger = logging.getLogger(__name__)


async def run_chapter_job(
    slug: str,
    request,
    queue: asyncio.Queue,
    job_id: str,
    executor,
    *,
    chapter_num: Optional[int] = None,
) -> None:
    try:
        loop = asyncio.get_event_loop()

        await queue.put({"stage": "init", "percent": 5, "message": "Loading world..."})
        cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

        existing_chapter = None
        chapter_index = None
        reroll = chapter_num is not None
        if reroll:
            for index, chapter in enumerate(state.chapters):
                if chapter.number == chapter_num:
                    existing_chapter = chapter
                    chapter_index = index
                    break
            if existing_chapter is None:
                await queue.put(
                    {"stage": "error", "error": f"Chapter {chapter_num} not found"}
                )
                return
        elif cfg.enable_choices and state.chapters:
            previous = state.chapters[-1]
            if previous.choices and not previous.selected_choice_id:
                selected_choice = random.choice(previous.choices)
                previous.selected_choice_id = selected_choice.id
                previous.choice_reasoning = None
                await queue.put(
                    {
                        "stage": "init",
                        "percent": 9,
                        "message": f"Auto-selecting choice: '{selected_choice.text[:50]}...'",
                    }
                )
                await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

        await queue.put(
            {"stage": "text", "percent": 10, "message": "Generating chapter text..."}
        )

        text_start = time.time()
        text_future = loop.run_in_executor(
            executor,
            partial(
                generate_chapter_draft,
                cfg,
                state,
                chapter_length=request.chapter_length,
            ),
        )
        await _watch_progress(
            queue,
            text_future,
            stage="text",
            start_percent=10,
            end_percent=85,
            estimated_duration=40.0,
            label="Chapter text",
        )
        draft = await text_future
        text_duration = time.time() - text_start
        logger.info("Text generation completed: %.2fs", text_duration)

        await queue.put(
            {
                "stage": "post-processing",
                "percent": 88,
                "message": "Generating summary...",
            }
        )
        summary_task = asyncio.create_task(generate_chapter_summary(draft.markdown, cfg))

        target_chapter_number = chapter_num or state.next_chapter
        image_path = None
        image_model_used = None

        if not request.no_images and (draft.image_prompt or draft.scene_prompt):
            settings = load_user_settings()
            image_model_used = resolve_image_model(cfg, settings)
            await queue.put(
                {
                    "stage": "image",
                    "percent": 90,
                    "message": f"Generating image ({image_model_used})...",
                }
            )
            prompt_for_image = draft.image_prompt or draft.scene_prompt or ""
            image_future = loop.run_in_executor(
                executor,
                partial(
                    generate_scene_image,
                    dirs["base"],
                    image_model_used,
                    cfg.style_pack,
                    prompt_for_image,
                    target_chapter_number,
                    "16:9",
                    reroll,
                ),
            )
            await _watch_progress(
                queue,
                image_future,
                stage="image",
                start_percent=90,
                end_percent=93,
                estimated_duration=8.0,
                label="Scene image",
            )
            image_path = await image_future

        await queue.put(
            {
                "stage": "post-processing",
                "percent": 94,
                "message": "Finalizing chapter...",
            }
        )
        ai_summary = await summary_task

        await queue.put(
            {"stage": "saving", "percent": 95, "message": "Saving world state..."}
        )
        chapter = await loop.run_in_executor(
            executor,
            partial(
                persist_generated_chapter,
                dirs["base"],
                cfg,
                state,
                draft,
                target_chapter_number,
                filename=existing_chapter.filename if existing_chapter else None,
                chapter_index=chapter_index,
                write_scene_request=not request.no_images,
            ),
        )

        chapter.generated_at = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        chapter.ai_summary = ai_summary or (existing_chapter.ai_summary if existing_chapter else None)
        if existing_chapter:
            chapter.selected_choice_id = existing_chapter.selected_choice_id
            chapter.choice_reasoning = existing_chapter.choice_reasoning
        if image_model_used:
            chapter.image_model_used = image_model_used
        elif existing_chapter:
            chapter.image_model_used = existing_chapter.image_model_used

        await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

        scene = None
        if image_path is not None:
            scene = f"/worlds/{slug}/media/scenes/{image_path.name}"
        else:
            scene = find_latest_scene_path(dirs["base"], slug, target_chapter_number)

        chapter_data = serialize_chapter_response(slug, chapter, scene=scene)
        await queue.put(
            {
                "stage": "complete",
                "percent": 100,
                "message": "Chapter complete!" if not reroll else "Chapter regenerated!",
                "chapter": chapter_data,
            }
        )
    except Exception:
        logging.exception("Chapter job failed for %s", job_id)
        logger.error("Full traceback: %s", traceback.format_exc())
        await queue.put(
            {
                "stage": "error",
                "error": "Chapter generation failed. Please check your settings and try again.",
                "job_id": job_id,
            }
        )


async def _watch_progress(
    queue: asyncio.Queue,
    future,
    *,
    stage: str,
    start_percent: int,
    end_percent: int,
    estimated_duration: float,
    label: str,
) -> None:
    start_time = time.time()
    update_interval = 0.5
    while not future.done():
        elapsed = time.time() - start_time
        progress_ratio = min(elapsed / estimated_duration, 1.0)
        eased_progress = 1 - (1 - progress_ratio) ** 2
        current_percent = int(
            start_percent + (end_percent - start_percent) * eased_progress
        )
        await queue.put(
            {
                "stage": stage,
                "percent": current_percent,
                "message": f"{label}... ({elapsed:.0f}s)",
            }
        )
        try:
            await asyncio.wait_for(asyncio.shield(future), timeout=update_interval)
            break
        except asyncio.TimeoutError:
            continue
