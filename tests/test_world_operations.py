import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from living_storyworld.api import chapters, images, worlds
from living_storyworld.api.world_operations import active_world_operations, world_operation
from living_storyworld.world import load_world


@pytest.mark.asyncio
async def test_world_reservation_blocks_all_competing_writers(stored_world):
    cfg, _, base = stored_world
    with world_operation(cfg.slug):
        requests = [
            chapters.start_chapter_generation(cfg.slug, chapters.ChapterGenerateRequest()),
            chapters.reroll_chapter(cfg.slug, 1),
            chapters.select_choice(cfg.slug, 1, chapters.ChoiceSelectionRequest(choice_id="x")),
            chapters.delete_chapter(cfg.slug, 1),
            worlds.update_world(worlds.WorldUpdateRequest(title="Changed"), (cfg.slug, base)),
            worlds.delete_world((cfg.slug, base)),
            images.generate_image(images.ImageGenerateRequest(chapter=1), (cfg.slug, base)),
        ]
        results = await asyncio.gather(*requests, return_exceptions=True)
    assert all(isinstance(result, HTTPException) and result.status_code == 409 for result in results)
    assert cfg.slug not in active_world_operations
    assert load_world(cfg.slug)[0].title == "Harbor"


@pytest.mark.asyncio
async def test_generation_reservation_survives_disconnect_and_releases_after_failure(
    stored_world,
):
    cfg, _, _ = stored_world
    entered, release = asyncio.Event(), asyncio.Event()

    async def job(*args, **kwargs):
        entered.set()
        await release.wait()

    with patch.object(chapters, "run_chapter_job", side_effect=job):
        response = await chapters.start_chapter_generation(cfg.slug, chapters.ChapterGenerateRequest())
        await entered.wait()
        # Simulate the SSE consumer leaving; generation must still own its slot.
        stream = await chapters.stream_chapter_progress(cfg.slug, response["job_id"])
        await anext(stream.body_iterator)
        await stream.body_iterator.aclose()
        assert chapters.active_jobs[response["job_id"]].snapshot()["status"] == "running"
        with pytest.raises(HTTPException):
            await chapters.start_chapter_generation(cfg.slug, chapters.ChapterGenerateRequest())
        release.set()
        await asyncio.sleep(0)
    assert cfg.slug not in active_world_operations
    with patch.object(chapters, "run_chapter_job", new=AsyncMock(side_effect=RuntimeError("failed"))):
        active_world_operations[cfg.slug] = "failed-job"
        with pytest.raises(RuntimeError):
            await chapters._run_job_with_cleanup(
                cfg.slug,
                chapters.ChapterGenerateRequest(),
                asyncio.Queue(),
                "failed-job",
            )
    assert cfg.slug not in active_world_operations


@pytest.mark.asyncio
async def test_job_can_be_reconnected_and_read_by_multiple_clients(stored_world):
    from living_storyworld.api.chapter_progress import ChapterProgress

    cfg, _, _ = stored_world
    job = ChapterProgress(cfg.slug, "recover")
    chapters.active_jobs[job.job_id] = job
    active_world_operations[cfg.slug] = job.job_id
    first = await chapters.stream_chapter_progress(cfg.slug, job.job_id)
    assert "progress" in await anext(first.body_iterator)
    await first.body_iterator.aclose()
    assert (await chapters.current_chapter_job(cfg.slug))["job_id"] == job.job_id
    assert (await chapters.chapter_job_status(cfg.slug, job.job_id))["status"] == "running"
    with pytest.raises(HTTPException) as wrong_world:
        await chapters.chapter_job_status("other-world", job.job_id)
    assert wrong_world.value.status_code == 404
    await job.put({"stage": "complete", "chapter": {"title": "Saved"}})
    for _ in range(2):
        stream = await chapters.stream_chapter_progress(cfg.slug, job.job_id)
        events = [event async for event in stream.body_iterator]
        assert len(events) == 1 and '"title": "Saved"' in events[0]
    assert (await chapters.chapter_job_status(cfg.slug, job.job_id))["status"] == "complete"
    assert await chapters.current_chapter_job(cfg.slug) is None


@pytest.mark.asyncio
async def test_finished_job_retention_is_bounded_without_expiring_running_jobs(stored_world, monkeypatch):
    from living_storyworld.api.chapter_progress import ChapterProgress

    cfg, _, _ = stored_world
    running = ChapterProgress(cfg.slug, "running")
    chapters.active_jobs["running"] = running
    for number in range(chapters._MAX_FINISHED_JOBS + 1):
        job = ChapterProgress(cfg.slug, str(number))
        await job.put({"stage": "error", "error": "Failed"})
        chapters.active_jobs[job.job_id] = job
    chapters._prune_jobs()
    assert len(chapters.active_jobs) == chapters._MAX_FINISHED_JOBS + 1
    latest = max(job.finished_at or 0 for job in chapters.active_jobs.values())
    monkeypatch.setattr(chapters.time, "monotonic", lambda: latest + chapters._JOB_TTL + 1)
    chapters._prune_jobs()
    assert chapters.active_jobs == {"running": running}
