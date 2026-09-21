import pytest


def test_empty_world_can_be_exported(stored_world):
    from argparse import Namespace

    from living_storyworld.cli import cmd_build

    cfg, _, base = stored_world
    cmd_build(Namespace(world=cfg.slug))
    assert "Harbor" in (base / "web" / "index.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "configured,override,expected",
    [
        ("", None, ""),
        ("workflow", None, "workflow"),
        ("workflow", "gpt-image-1-mini", "gpt-image-1-mini"),
    ],
)
def test_cli_init_inherits_image_settings_unless_explicitly_overridden(
    stored_world, monkeypatch, configured, override, expected
):
    from living_storyworld.cli import main
    from living_storyworld.settings import UserSettings
    from living_storyworld.world import load_world

    monkeypatch.setattr(
        "living_storyworld.world.load_user_settings",
        lambda: UserSettings(default_image_model=configured),
    )
    args = ["init", "--title", "CLI world", "--theme", "A clockmaker's workshop"]
    if override is not None:
        args += ["--image-model", override]
    main(args)
    config, _, _ = load_world("cli-world")
    assert config.image_model == expected


@pytest.mark.parametrize("image_provider", ["none", "comfyui"])
def test_world_wizard_respects_illustration_settings(
    stored_world, monkeypatch, image_provider
):
    from unittest.mock import Mock

    from living_storyworld import wizard
    from living_storyworld.models import Chapter
    from living_storyworld.providers.image import ImageGenerationResult
    from living_storyworld.settings import UserSettings
    from living_storyworld.world import load_world

    settings = UserSettings(
        image_provider=image_provider, default_image_model="workflow"
    )
    monkeypatch.setattr(
        "living_storyworld.settings.load_user_settings", lambda: settings
    )
    monkeypatch.setattr("living_storyworld.world.load_user_settings", lambda: settings)
    replies = iter(["Wizard world", "A workshop", "", "", "y", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))

    def generate(base, config, state, *, make_scene_image):
        chapter = Chapter(
            number=1,
            title="The Clock",
            filename="chapter-0001.md",
            scene_prompt="A clock",
        )
        state.chapters.append(chapter)
        (base / "chapters" / chapter.filename).write_text(
            "# The Clock\nA story.", encoding="utf-8"
        )
        return chapter

    def illustrate(base, model, style, prompt, **kwargs):
        path = base / "media" / "scenes" / "scene-0001.png"
        path.write_bytes(b"test image")
        return ImageGenerationResult(path, image_provider, model, None)

    generate_mock = Mock(side_effect=generate)
    image_mock = Mock(side_effect=illustrate)
    monkeypatch.setattr(wizard, "generate_chapter", generate_mock)
    monkeypatch.setattr(wizard, "generate_scene_result", image_mock)
    wizard.run_world_wizard()

    _, state, dirs = load_world("wizard-world")
    assert len(state.chapters) == 1
    assert (dirs["chapters"] / state.chapters[0].filename).read_text(
        encoding="utf-8"
    ) == "# The Clock\nA story."
    assert generate_mock.call_args.kwargs["make_scene_image"] is (
        image_provider != "none"
    )
    if image_provider == "none":
        image_mock.assert_not_called()
        assert not state.chapters[0].scene_filename
    else:
        image_mock.assert_called_once()
        assert image_mock.call_args.args[1] == "workflow"
        assert state.chapters[0].scene_filename == "scene-0001.png"
