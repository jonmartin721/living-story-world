def test_empty_world_can_be_exported(stored_world):
    from argparse import Namespace

    from living_storyworld.cli import cmd_build

    cfg, _, base = stored_world
    cmd_build(Namespace(world=cfg.slug))
    assert "Harbor" in (base / "web" / "index.html").read_text(encoding="utf-8")
