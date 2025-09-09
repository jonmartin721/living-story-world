from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict

from .models import WorldConfig
from .storage import read_json, write_json


STYLE_PACKS: Dict[str, str] = {
    "storybook-ink": (
        "Storybook ink and wash, muted palette, soft vignette, gentle rim light, "
        "film grain, 3:2 composition, evocative and cozy, illustrative linework"
    ),
    "pixel-rpg": (
        "16-bit SNES pixel art, 256-color limited palette, crisp sprites, tile-based, "
        "subtle dither, top-down scenes, nostalgic RPG manual illustration"
    ),
    "lowpoly-iso": (
        "Low-poly isometric diorama, soft ambient occlusion, stylized color blocks, "
        "minimal texture, cinematic lighting, clean edges"
    ),
}


def save_config(path: Path, cfg: WorldConfig) -> None:
    write_json(path, asdict(cfg))


def load_config(path: Path) -> WorldConfig:
    data = read_json(path, {})
    return WorldConfig(**data)

