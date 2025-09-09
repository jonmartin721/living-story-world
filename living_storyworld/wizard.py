from __future__ import annotations

from getpass import getpass
from typing import Optional

from .config import STYLE_PACKS
from .generator import generate_chapter
from .image import generate_scene_image
from .models import WorldConfig, WorldState
from .presets import PRESETS, DEFAULT_PRESET
from .settings import UserSettings, load_user_settings, save_user_settings
from .storage import WORLDS_DIR, get_current_world, set_current_world, slugify
from .world import init_world, load_world, save_world


def _pick(prompt: str, options: list[str], default: Optional[str] = None) -> str:
    idx_map = {str(i + 1): opt for i, opt in enumerate(options)}
    while True:
        print(prompt)
        for i, opt in enumerate(options):
            star = "*" if default and opt == default else ""
            print(f"  {i+1}. {opt} {star}")
        sel = input("Choose (number): ").strip() or None
        if not sel and default:
            return default
        if sel in idx_map:
            return idx_map[sel]
        print("Please enter a valid number.\n")


def run_setup_wizard() -> None:
    print("\n=== Living Storyworld Setup ===\n")
    s = load_user_settings()
    if s.openai_api_key:
        print("A saved API key was found. Press Enter to keep it.")
    key = getpass("OpenAI API Key: ")
    if key.strip():
        s.openai_api_key = key.strip()
    # Defaults
    style = _pick("Pick a default art style:", list(STYLE_PACKS.keys()), default=s.default_style_pack)
    preset = _pick("Pick a default story preset:", list(PRESETS.keys()), default=s.default_preset)
    s.default_style_pack = style
    s.default_preset = preset
    save_user_settings(s)
    print(f"Saved. Default style={style}, preset={preset}.\n")


def run_world_wizard() -> None:
    print("\n=== Create Your Storyworld ===\n")
    title = input("World title (e.g., The Flooded Stacks): ").strip() or "My Storyworld"
    theme = input("One-line theme (e.g., A city of drowned archives): ").strip() or "A world of wonder."
    from .settings import load_user_settings
    s = load_user_settings()
    style = _pick("Art style:", list(STYLE_PACKS.keys()), default=s.default_style_pack)
    preset = _pick("Story preset:", list(PRESETS.keys()), default=s.default_preset)
    slug = slugify(title)
    init_world(title, theme, style, slug)
    set_current_world(slug)
    print(f"Created world at worlds/{slug}.\n")
    # Offer first chapter
    go = (input("Generate your first chapter now? [Y/n]: ").strip().lower() or "y").startswith("y")
    if not go:
        return
    cfg, state, dirs = load_world(slug)
    ch = generate_chapter(dirs["base"], cfg, state, focus=None, make_scene_image=True, preset_key=preset)
    state.chapters.append(ch.__dict__)
    state.next_chapter += 1
    save_world(slug, cfg, state, dirs)
    if ch.scene_prompt:
        out = generate_scene_image(dirs["base"], cfg.image_model, cfg.style_pack, ch.scene_prompt, chapter_num=ch.number)
        print(f"Generated scene image -> {out.relative_to(dirs['base'])}")
    print(f"Wrote chapter {ch.number}: {ch.title}")
    # Offer viewer build
    build = (input("Build the simple HTML viewer now? [Y/n]: ").strip().lower() or "y").startswith("y")
    if build:
        from .cli import cmd_build
        import argparse
        cmd_build(argparse.Namespace(world=slug))
        print(f"Open: worlds/{slug}/web/index.html\n")

