from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .models import WorldConfig, WorldState, Character, Location, Chapter, Item, Choice
from .storage import ensure_world_dirs, set_current_world, slugify, write_json, read_json


def init_world(
    title: str,
    theme: str,
    style_pack: str = "storybook-ink",
    slug: Optional[str] = None,
    image_model: str = "flux-dev",
    maturity_level: str = "general",
    preset: str = "cozy-adventure",
    enable_choices: bool = False,
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
        maturity_level=maturity_level,
        preset=preset,
        enable_choices=enable_choices,
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


def _deserialize_world_state(data: dict) -> WorldState:
    """Deserialize WorldState from dict, properly reconstructing nested dataclasses."""
    # Deserialize chapters
    chapters = []
    if "chapters" in data:
        for ch_data in data["chapters"]:
            # Deserialize choices if present
            if "choices" in ch_data and ch_data["choices"]:
                ch_data["choices"] = [Choice(**choice) for choice in ch_data["choices"]]
            chapters.append(Chapter(**ch_data))

    # Deserialize characters
    characters = {}
    if "characters" in data:
        for name, char_data in data["characters"].items():
            characters[name] = Character(**char_data)

    # Deserialize locations
    locations = {}
    if "locations" in data:
        for name, loc_data in data["locations"].items():
            locations[name] = Location(**loc_data)

    # Deserialize items
    items = {}
    if "items" in data:
        for name, item_data in data["items"].items():
            items[name] = Item(**item_data)

    return WorldState(
        tick=data.get("tick", 0),
        next_chapter=data.get("next_chapter", 1),
        characters=characters,
        locations=locations,
        items=items,
        chapters=chapters
    )


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
        # Handle backward compatibility for removed image_model field
        cfg_data_copy = cfg_data.copy()
        if 'image_model' in cfg_data_copy:
            del cfg_data_copy['image_model']
        cfg = WorldConfig(**cfg_data_copy)
    except (TypeError, ValueError) as e:
        logging.error(f"Failed to validate world config for '{slug}': {e}")
        raise RuntimeError(f"World '{slug}' has corrupted configuration: {e}")

    # Load and validate state
    state_data = read_json(dirs["base"] / "world.json")
    if state_data is None:
        raise RuntimeError(f"World '{slug}' world.json not found or corrupted")

    try:
        state = _deserialize_world_state(state_data)
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

