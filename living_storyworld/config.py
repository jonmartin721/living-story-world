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
    "watercolor-dream": (
        "Delicate watercolor on textured paper, flowing pigments, soft wet-on-wet blending, "
        "loose brush strokes, luminous washes, ethereal and dreamlike atmosphere"
    ),
    "noir-sketch": (
        "High-contrast charcoal sketch, dramatic shadows, cross-hatching, film noir aesthetic, "
        "bold blacks and whites, expressive lines, moody atmospheric lighting"
    ),
    "art-nouveau": (
        "Art nouveau poster style, flowing organic lines, decorative borders, elegant typography, "
        "muted earth tones with jewel accents, ornamental patterns, romantic elegance"
    ),
    "comic-book": (
        "Classic comic book illustration, bold ink lines, Ben-Day dots, dynamic angles, "
        "saturated primary colors, action-oriented composition, vintage four-color printing"
    ),
    "oil-painting": (
        "Classical oil painting, visible brush strokes, rich impasto texture, Renaissance lighting, "
        "deep chiaroscuro, warm glazes, museum-quality fine art composition"
    ),
}


def save_config(path: Path, cfg: WorldConfig) -> None:
    write_json(path, asdict(cfg))


def load_config(path: Path) -> WorldConfig:
    data = read_json(path, {})
    return WorldConfig(**data)

