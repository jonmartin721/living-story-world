from __future__ import annotations

import asyncio
import logging
import random
import time
import traceback
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Optional, Protocol

from .generator import (
    find_chapter_scene_path,
    generate_chapter_draft,
    generate_chapter_summary,
    persist_generated_chapter,
    resolve_image_model,
    serialize_chapter_response,
)
from .image import generate_scene_result
from .models import WorldState
from .settings import load_user_settings
from .world import load_world, save_world

logger = logging.getLogger(__name__)


class ProgressSink(Protocol):
    async def put(self, update: dict) -> None:
        ...


async def run_chapter_job(
    slug: str,
    request,
    queue: ProgressSink,
    job_id: str,
    executor,
    *,
    chapter_num: Optional[int] = None,
) -> None:
    summary_task = None
    try:
        loop = asyncio.get_event_loop()

        await queue.put({"stage": "init", "percent": 5, "message": "Loading world..."})
        cfg, state, dirs = await loop.run_in_executor(executor, load_world, slug)

        settings = await loop.run_in_executor(executor, load_user_settings)
        include_images = not request.no_images and settings.image_provider != "none"

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
            if chapter_index != len(state.chapters) - 1:
                await queue.put(
                    {
                        "stage": "error",
                        "error": "Only the latest chapter can be rerolled. Later chapters depend on it.",
                    }
                )
                return
            # Never prompt a reroll with the chapter being replaced or with a future number.
            context = existing_chapter.entity_context or state.to_dict()
            state = WorldState.from_dict(
                {
                    **context,
                    "next_chapter": chapter_num,
                    "chapters": [
                        chapter.to_dict() for chapter in state.chapters[:chapter_index]
                    ],
                }
            )
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
        summary_task = asyncio.create_task(
            generate_chapter_summary(draft.markdown, cfg)
        )

        target_chapter_number = chapter_num or state.next_chapter
        image_path = None
        image_model_used = None

        if include_images and (draft.image_prompt or draft.scene_prompt):
            settings = await loop.run_in_executor(executor, load_user_settings)
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
                    generate_scene_result,
                    dirs["base"],
                    image_model_used,
                    cfg.style_pack,
                    prompt_for_image,
                    target_chapter_number,
                    "16:9",
                    reroll,
                    revision=True,
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
            image_result = await image_future
            image_path = image_result.image_path
            image_model_used = image_result.model

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
                # Publish a new file, then atomically switch world.json to it. The previous
                # revision remains readable if saving fails, and is retained after success.
                filename=(
                    f"chapter-{target_chapter_number:04d}-{uuid.uuid4().hex}.md"
                    if reroll
                    else None
                ),
                write_scene_request=include_images,
            ),
        )

        chapter.generated_at = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        chapter.ai_summary = ai_summary or draft.summary
        if image_model_used:
            chapter.image_model_used = image_model_used
        elif existing_chapter:
            chapter.image_model_used = existing_chapter.image_model_used

        if image_path is not None:
            chapter.scene_filename = image_path.relative_to(dirs["base"] / "media" / "scenes").as_posix()
        elif existing_chapter:
            prior_scene = find_chapter_scene_path(dirs["base"], slug, existing_chapter)
            chapter.scene_filename = prior_scene.removeprefix(f"/worlds/{slug}/media/scenes/") if prior_scene else ""

        await loop.run_in_executor(executor, save_world, slug, cfg, state, dirs)

        scene = find_chapter_scene_path(dirs["base"], slug, chapter)

        chapter_data = serialize_chapter_response(slug, chapter, scene=scene)
        await queue.put(
            {
                "stage": "complete",
                "percent": 100,
                "message": (
                    "Chapter complete!" if not reroll else "Chapter regenerated!"
                ),
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
    finally:
        if summary_task is not None and not summary_task.done():
            summary_task.cancel()
            await asyncio.gather(summary_task, return_exceptions=True)


async def _watch_progress(
    queue: ProgressSink,
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
