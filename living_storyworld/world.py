from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .models import WorldConfig, WorldState, Character, Location
from .storage import ensure_world_dirs, set_current_world, slugify, write_json, read_json


def init_world(
    title: str,
    theme: str,
    style_pack: str = "storybook-ink",
    slug: Optional[str] = None,
    image_model: str = "flux-dev",
    memory: Optional[str] = None,
    authors_note: Optional[str] = None,
    world_instructions: Optional[str] = None
) -> str:
    slug = slug or slugify(title)
    dirs = ensure_world_dirs(slug)
    cfg = WorldConfig(
        title=title,
        slug=slug,
        theme=theme,
        style_pack=style_pack,
        image_model=image_model,
        memory=memory,
        authors_note=authors_note,
        world_instructions=world_instructions
    )
    state = WorldState(
        tick=0,
        next_chapter=1,
        characters={},
        locations={},
        items={},
        chapters=[],
    )
    write_json(dirs["base"] / "config.json", asdict(cfg))
    write_json(dirs["base"] / "world.json", asdict(state))
    set_current_world(slug)
    # Minimal web index placeholder
    (dirs["web"] / "index.html").write_text("""
<!doctype html>
<html><head><meta charset='utf-8'><title>Living Storyworld</title>
<style>body{font-family:system-ui, sans-serif;max-width:860px;margin:3rem auto;padding:0 1rem} img{max-width:100%;height:auto;border-radius:6px} .chapter{margin:2rem 0;padding:1rem;border:1px solid #eee;border-radius:8px}</style>
</head>
<body>
<h1>Living Storyworld</h1>
<p>Chapters will appear here after generation.</p>
</body></html>
""")
    return slug


def load_world(slug: str) -> tuple[WorldConfig, WorldState, dict]:
    """Load world configuration and state with validation.

    Raises:
        RuntimeError: If world data is missing or corrupted
    """
    dirs = ensure_world_dirs(slug)

    # Load and validate config
    cfg_data = read_json(dirs["base"] / "config.json")
    if cfg_data is None:
        raise RuntimeError(f"World '{slug}' config.json not found or corrupted")

    try:
        cfg = WorldConfig(**cfg_data)
    except (TypeError, ValueError) as e:
        logging.error(f"Failed to validate world config for '{slug}': {e}")
        raise RuntimeError(f"World '{slug}' has corrupted configuration: {e}")

    # Load and validate state
    state_data = read_json(dirs["base"] / "world.json")
    if state_data is None:
        raise RuntimeError(f"World '{slug}' world.json not found or corrupted")

    try:
        state = WorldState(**state_data)
    except (TypeError, ValueError) as e:
        logging.error(f"Failed to validate world state for '{slug}': {e}")
        raise RuntimeError(f"World '{slug}' has corrupted state: {e}")

    return cfg, state, dirs


def save_world(slug: str, cfg: WorldConfig, state: WorldState, dirs: Optional[dict] = None) -> None:
    if dirs is None:
        dirs = ensure_world_dirs(slug)
    write_json(dirs["base"] / "config.json", asdict(cfg))
    write_json(dirs["base"] / "world.json", asdict(state))


def tick_world(slug: str) -> int:
    cfg, state, dirs = load_world(slug)
    state.tick += 1
    save_world(slug, cfg, state, dirs)
    return state.tick

