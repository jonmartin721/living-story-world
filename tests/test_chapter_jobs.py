import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from living_storyworld.api import chapters
from living_storyworld.api.chapters import ChapterGenerateRequest
from living_storyworld.chapter_jobs import run_chapter_job
from living_storyworld.models import Chapter, Character, Choice, GeneratedChapterDraft, WorldConfig, WorldState
from living_storyworld.world import load_world, save_world


async def _run_reroll(cfg, state, base, *, target=None, failing_save=False):
    save_world(cfg.slug, cfg, state)
    observed = []

    def draft(config, context, **kwargs):
        observed.append(context.to_dict())
        return GeneratedChapterDraft(
            markdown="# New\nNew story",
            title="New",
            summary="New summary",
            new_characters=[{"id": "newcomer", "name": "Newcomer"}],
            choices=[Choice(id="new", text="New option")],
        )

    queue = asyncio.Queue()
    with (
        patch("living_storyworld.chapter_jobs.generate_chapter_draft", side_effect=draft),
        patch(
            "living_storyworld.chapter_jobs.generate_chapter_summary",
            new=AsyncMock(return_value=""),
        ),
        patch(
            "living_storyworld.chapter_jobs.save_world",
            side_effect=OSError("disk error") if failing_save else save_world,
        ),
    ):
        await run_chapter_job(
            cfg.slug,
            chapters.ChapterGenerateRequest(no_images=True),
            queue,
            "test",
            None,
            chapter_num=target,
        )
    updates = []
    while not queue.empty():
        updates.append(queue.get_nowait())
    return observed, updates[-1]


@pytest.mark.asyncio
async def test_reroll_restores_context_and_persists_matching_content(stored_world):
    cfg, state, base = stored_world
    first = Chapter(number=1, title="First", filename="chapter-0001.md", summary="Prior events")
    old = Chapter(
        number=2,
        title="Old",
        filename="chapter-0002.md",
        summary="Must not leak",
        ai_summary="Stale summary",
        selected_choice_id="old",
        choice_reasoning="Stale reasoning",
        entity_context={"characters": {}, "locations": {}, "items": {}, "tick": 1},
    )
    state.chapters = [first, old]
    state.next_chapter = 3
    state.characters["discarded"] = Character(id="discarded", name="Discarded")
    original = base / "chapters" / old.filename
    original.write_text("# Old\nOld story", encoding="utf-8")
    observed, final = await _run_reroll(cfg, state, base, target=2)
    assert observed[0]["next_chapter"] == 2
    assert [chapter["number"] for chapter in observed[0]["chapters"]] == [1]
    assert observed[0]["characters"] == {}
    _, saved, _ = load_world(cfg.slug)
    assert final["stage"] == "complete"
    assert saved.next_chapter == 3
    chapter = saved.chapters[-1]
    assert final["chapter"]["filename"] == chapter.filename
    assert chapter.filename != old.filename
    assert (base / "chapters" / chapter.filename).read_text(encoding="utf-8") == "# New\nNew story"
    assert original.read_text(encoding="utf-8") == "# Old\nOld story"
    assert chapter.selected_choice_id is None
    assert chapter.ai_summary == "New summary"
    assert set(saved.characters) == {"newcomer"}


@pytest.mark.asyncio
async def test_failed_reroll_save_keeps_previous_readable_revision(stored_world):
    cfg, state, base = stored_world
    old = Chapter(number=1, title="Old", filename="chapter-0001.md")
    state.chapters = [old]
    state.next_chapter = 2
    path = base / "chapters" / old.filename
    path.write_text("# Original", encoding="utf-8")
    _, final = await _run_reroll(cfg, state, base, target=1, failing_save=True)
    assert final["stage"] == "error"
    _, saved, _ = load_world(cfg.slug)
    assert saved.chapters[-1].filename == old.filename
    assert path.read_text(encoding="utf-8") == "# Original"


@pytest.mark.asyncio
async def test_historical_reroll_does_not_generate_or_change_state(stored_world):
    cfg, state, base = stored_world
    state.chapters = [Chapter(number=n, title=f"Chapter {n}", filename=f"{n}.md") for n in (1, 2)]
    state.next_chapter = 3
    observed, final = await _run_reroll(cfg, state, base, target=1)
    assert not observed
    assert final["stage"] == "error"
    assert len(load_world(cfg.slug)[1].chapters) == 2


def _drain_queue(queue: asyncio.Queue) -> list[dict]:
    updates = []
    while not queue.empty():
        updates.append(queue.get_nowait())
    return updates


async def _run_job(queue: asyncio.Queue, base_dir: Path, state: WorldState, chapter_num=None):
    cfg = WorldConfig(
        title="Harbor",
        slug="harbor",
        theme="Test theme",
        text_model="gpt-4o-mini",
        image_model="flux-schnell",
    )
    dirs = {"base": base_dir}

    draft = GeneratedChapterDraft(
        markdown='<!-- {"scene_prompt": "A harbor", "image_prompt": "A harbor at dusk", "summary": "A summary", "new_characters": [], "new_locations": []} -->\n# Harbor\n\nStory content',
        title="Harbor",
        summary="A summary",
        scene_prompt="A harbor",
        image_prompt="A harbor at dusk",
        text_model_used="gpt-4o-mini",
        choices=[Choice(id="c1", text="Stay", description="Stay put")],
    )

    with (
        patch("living_storyworld.chapter_jobs.load_world", return_value=(cfg, state, dirs)),
        patch("living_storyworld.chapter_jobs.save_world") as mock_save,
        patch("living_storyworld.chapter_jobs.generate_chapter_draft", return_value=draft),
        patch(
            "living_storyworld.chapter_jobs.generate_chapter_summary",
            new=AsyncMock(return_value="Short continuity summary"),
        ),
    ):
        await run_chapter_job(
            "harbor",
            ChapterGenerateRequest(no_images=True),
            queue,
            "job-1",
            None,
            chapter_num=chapter_num,
        )

    return _drain_queue(queue), mock_save


def test_reroll_publishes_new_revision_and_preserves_previous_text(tmp_path):
    base_dir = tmp_path / "world"
    chapters_dir = base_dir / "chapters"
    scenes_dir = base_dir / "media" / "scenes"
    chapters_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)
    original = chapters_dir / "chapter-0001.md"
    original.write_text("# Old\n\nOld content", encoding="utf-8")
    preserved_scene = scenes_dir / "scene-0001-old.png"
    preserved_scene.write_text("png", encoding="utf-8")

    state = WorldState(
        tick=1,
        next_chapter=2,
        chapters=[
            Chapter(
                number=1,
                title="Old",
                filename="chapter-0001.md",
                summary="Old summary",
                scene_prompt="Old scene",
                selected_choice_id="c1",
                choice_reasoning="Because",
                image_model_used="flux-dev",
            )
        ],
    )

    queue: asyncio.Queue = asyncio.Queue()
    updates, _ = asyncio.run(_run_job(queue, base_dir, state, chapter_num=1))
    complete = updates[-1]

    assert complete["stage"] == "complete"
    assert original.read_text(encoding="utf-8") == "# Old\n\nOld content"
    assert (chapters_dir / complete["chapter"]["filename"]).read_text(encoding="utf-8").startswith("<!--")
    assert not (chapters_dir / "chapter-0002.md").exists()
    assert complete["chapter"]["scene"] == "/worlds/harbor/media/scenes/scene-0001-old.png"
    assert complete["chapter"]["selected_choice_id"] is None
    assert complete["chapter"]["choice_reasoning"] is None


def test_create_and_reroll_emit_same_chapter_shape(tmp_path):
    base_dir = tmp_path / "world"
    (base_dir / "chapters").mkdir(parents=True)

    create_state = WorldState()
    reroll_state = WorldState(
        tick=1,
        next_chapter=2,
        chapters=[Chapter(number=1, title="Old", filename="chapter-0001.md")],
    )
    (base_dir / "chapters" / "chapter-0001.md").write_text("old", encoding="utf-8")

    create_updates, create_save = asyncio.run(_run_job(asyncio.Queue(), base_dir, create_state))
    reroll_updates, reroll_save = asyncio.run(_run_job(asyncio.Queue(), base_dir, reroll_state, chapter_num=1))

    create_payload = create_updates[-1]["chapter"]
    reroll_payload = reroll_updates[-1]["chapter"]

    assert set(create_payload.keys()) == set(reroll_payload.keys())
    assert create_save.called
    assert reroll_save.called


@pytest.mark.asyncio
@pytest.mark.parametrize("failing_save", [False, True])
async def test_image_revision_is_published_only_with_saved_chapter(stored_world, failing_save):
    from unittest.mock import MagicMock

    from living_storyworld.generator import find_chapter_scene_path
    from living_storyworld.image import generate_scene_result
    from living_storyworld.providers.image import ImageGenerationResult
    from living_storyworld.settings import UserSettings

    cfg, state, base = stored_world
    old = Chapter(number=1, title="Old", filename="chapter-0001.md")
    state.chapters = [old]
    state.next_chapter = 2
    (base / "chapters" / old.filename).write_text("Old story")
    legacy = base / "media/scenes/scene-0001-old.png"
    legacy.write_bytes(b"old")
    save_world(cfg.slug, cfg, state)
    provider = MagicMock()

    def image(**kwargs):
        path = kwargs["output_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"new")
        return ImageGenerationResult(path, "pollinations", "flux", 0.0)

    provider.generate.side_effect = image
    draft = GeneratedChapterDraft(markdown="# New\nNew story", title="New", image_prompt="Harbor")
    queue = asyncio.Queue()
    with (
        patch("living_storyworld.chapter_jobs.generate_chapter_draft", return_value=draft),
        patch("living_storyworld.chapter_jobs.generate_chapter_summary", new=AsyncMock(return_value="Summary")),
        patch(
            "living_storyworld.chapter_jobs.save_world",
            side_effect=OSError("disk error") if failing_save else save_world,
        ),
        patch("living_storyworld.image.load_user_settings", return_value=UserSettings(image_provider="pollinations")),
        patch("living_storyworld.chapter_jobs.load_user_settings", return_value=UserSettings(image_provider="pollinations")),
        patch("living_storyworld.image.get_image_provider", return_value=provider),
        patch("living_storyworld.chapter_jobs.generate_scene_result", wraps=generate_scene_result),
    ):
        await run_chapter_job(cfg.slug, ChapterGenerateRequest(), queue, "image-job", None, chapter_num=1)
    final = _drain_queue(queue)[-1]
    saved = load_world(cfg.slug)[1].chapters[0]
    scene = find_chapter_scene_path(base, cfg.slug, saved)
    assert list((base / "media/scenes/revisions").glob("*/*.png"))
    if failing_save:
        assert final["stage"] == "error"
        assert saved.filename == old.filename
        assert scene.endswith("scene-0001-old.png")
    else:
        assert final["stage"] == "complete"
        assert saved.image_model_used == "flux"
        assert saved.scene_filename.startswith("revisions/")
        assert scene == final["chapter"]["scene"]
        assert scene.endswith(saved.scene_filename)

    from argparse import Namespace

    from living_storyworld.cli import cmd_build

    cmd_build(Namespace(world=cfg.slug))
    exported = (base / "web/index.html").read_text(encoding="utf-8")
    assert "../" + scene.removeprefix(f"/worlds/{cfg.slug}/") in exported
    assert f"../chapters/{saved.filename}" in exported
