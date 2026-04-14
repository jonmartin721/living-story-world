import asyncio
import importlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from living_storyworld.api.chapters import ChapterGenerateRequest
from living_storyworld.chapter_jobs import run_chapter_job
from living_storyworld.generator import (
    GeneratedChapterDraft,
    _generate_text_with_fallback,
    resolve_generation_settings,
)
from living_storyworld.models import Chapter, Choice, WorldConfig, WorldState
from living_storyworld.settings import UserSettings
from living_storyworld.world import load_world, save_world


def _drain_queue(queue: asyncio.Queue) -> list[dict]:
    updates = []
    while not queue.empty():
        updates.append(queue.get_nowait())
    return updates


def test_resolve_generation_settings_prefers_world_models(sample_world_config):
    settings = UserSettings(
        text_provider="gemini",
        image_provider="pollinations",
        default_text_model="gemini-2.5-flash-lite",
        default_image_model="flux",
    )

    with patch(
        "living_storyworld.settings.get_available_text_providers",
        return_value=["gemini", "openai"],
    ):
        resolved = resolve_generation_settings(sample_world_config, settings)

    assert resolved.text_provider_order == ["gemini", "openai"]
    assert resolved.preferred_text_model == sample_world_config.text_model
    assert resolved.preferred_image_model == sample_world_config.image_model


def test_text_fallback_uses_provider_default_model_for_secondary_provider(
    sample_world_config,
):
    settings = UserSettings(
        text_provider="openai",
        default_text_model="gpt-4o-mini",
    )
    messages = [{"role": "user", "content": "Hello"}]

    primary_provider = MagicMock()
    secondary_provider = MagicMock()
    primary_provider.generate.side_effect = RuntimeError("primary failed")
    primary_provider.get_default_model.return_value = "gpt-5-mini"
    secondary_provider.generate.return_value = type(
        "Result",
        (),
        {
            "content": "fallback worked",
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "estimated_cost": 0.0,
        },
    )()
    secondary_provider.get_default_model.return_value = "gemini-2.5-flash"

    with patch(
        "living_storyworld.generator.get_text_provider",
        side_effect=[primary_provider, secondary_provider],
    ), patch(
        "living_storyworld.generator.get_api_key_for_provider",
        return_value="test-key",
    ), patch(
        "living_storyworld.settings.get_available_text_providers",
        return_value=["openai", "gemini"],
    ):
        content, provider_name, model_name = _generate_text_with_fallback(
            messages,
            sample_world_config,
            0.7,
            settings=settings,
        )

    assert content == "fallback worked"
    assert provider_name == "gemini"
    assert model_name == "gemini-2.5-flash"
    secondary_provider.generate.assert_called_once_with(
        messages,
        temperature=0.7,
        model="gemini-2.5-flash",
    )


def test_load_and_save_world_preserves_image_model(tmp_path):
    worlds_dir = tmp_path / "worlds"
    world_dir = worlds_dir / "kept-model"
    world_dir.mkdir(parents=True)
    (world_dir / "config.json").write_text(
        """
{
  "title": "Kept Model",
  "slug": "kept-model",
  "theme": "Testing persistence",
  "style_pack": "storybook-ink",
  "text_model": "gpt-4o-mini",
  "image_model": "flux-schnell"
}
""".strip(),
        encoding="utf-8",
    )
    (world_dir / "world.json").write_text(
        '{"tick": 0, "next_chapter": 1, "characters": {}, "locations": {}, "items": {}, "chapters": []}',
        encoding="utf-8",
    )

    with patch("living_storyworld.storage.WORLDS_DIR", worlds_dir):
        cfg, state, dirs = load_world("kept-model")
        assert cfg.image_model == "flux-schnell"

        save_world("kept-model", cfg, state, dirs)
        reloaded_cfg, _, _ = load_world("kept-model")

    assert reloaded_cfg.image_model == "flux-schnell"


def test_webapp_mounts_worlds_on_clean_start(tmp_path, monkeypatch):
    worlds_dir = tmp_path / "worlds"
    monkeypatch.setattr("living_storyworld.storage.WORLDS_DIR", worlds_dir)

    import living_storyworld.webapp as webapp_module

    webapp = importlib.reload(webapp_module)

    served_file = worlds_dir / "test-world" / "hello.txt"
    served_file.parent.mkdir(parents=True, exist_ok=True)
    served_file.write_text("hello", encoding="utf-8")

    client = TestClient(webapp.app)
    response = client.get("/worlds/test-world/hello.txt")

    assert response.status_code == 200
    assert response.text == "hello"


async def _run_job(queue: asyncio.Queue, base_dir: Path, state: WorldState, chapter_num=None):
    cfg = WorldConfig(
        title="Refactor Test",
        slug="refactor-test",
        theme="Test theme",
        text_model="gpt-4o-mini",
        image_model="flux-schnell",
    )
    dirs = {"base": base_dir}

    draft = GeneratedChapterDraft(
        markdown="<!-- {\"scene_prompt\": \"A harbor\", \"image_prompt\": \"A harbor at dusk\", \"summary\": \"A summary\", \"new_characters\": [], \"new_locations\": []} -->\n# Harbor\n\nStory content",
        title="Harbor",
        summary="A summary",
        scene_prompt="A harbor",
        image_prompt="A harbor at dusk",
        text_model_used="gpt-4o-mini",
        choices=[Choice(id="c1", text="Stay", description="Stay put")],
    )

    with patch("living_storyworld.chapter_jobs.load_world", return_value=(cfg, state, dirs)), patch(
        "living_storyworld.chapter_jobs.save_world"
    ) as mock_save, patch(
        "living_storyworld.chapter_jobs.generate_chapter_draft", return_value=draft
    ), patch(
        "living_storyworld.chapter_jobs.generate_chapter_summary",
        new=AsyncMock(return_value="Short continuity summary"),
    ):
        await run_chapter_job(
            "refactor-test",
            ChapterGenerateRequest(no_images=True),
            queue,
            "job-1",
            None,
            chapter_num=chapter_num,
        )

    return _drain_queue(queue), mock_save


def test_reroll_overwrites_existing_file_without_orphan(tmp_path):
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
    assert original.read_text(encoding="utf-8").startswith("<!--")
    assert not (chapters_dir / "chapter-0002.md").exists()
    assert complete["chapter"]["scene"] == "/worlds/refactor-test/media/scenes/scene-0001-old.png"
    assert complete["chapter"]["selected_choice_id"] == "c1"


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

    create_updates, create_save = asyncio.run(
        _run_job(asyncio.Queue(), base_dir, create_state)
    )
    reroll_updates, reroll_save = asyncio.run(
        _run_job(asyncio.Queue(), base_dir, reroll_state, chapter_num=1)
    )

    create_payload = create_updates[-1]["chapter"]
    reroll_payload = reroll_updates[-1]["chapter"]

    assert set(create_payload.keys()) == set(reroll_payload.keys())
    assert create_save.called
    assert reroll_save.called
