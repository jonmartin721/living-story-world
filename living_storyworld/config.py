from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict

from .models import WorldConfig
from .storage import read_json, write_json


STYLE_PACKS: Dict[str, str] = {
    "storybook-ink": (
        "STYLE REQUIREMENT: Traditional storybook illustration with ink and wash technique. "
        "MUST HAVE: Muted earthy palette, soft vignette edges, gentle rim lighting, visible film grain texture, "
        "3:2 composition framing, illustrative pen linework over watercolor washes. Evocative, cozy, hand-drawn feel. "
        "Think classic children's book illustrations like Beatrix Potter or Arthur Rackham."
    ),
    "pixel-rpg": (
        "CRITICAL STYLE REQUIREMENT: Pure 16-bit pixel art ONLY. "
        "MUST HAVE: Hard pixel edges with NO anti-aliasing, limited 256-color palette, visible dithering patterns, "
        "sharp blocky sprites. MUST look exactly like Final Fantasy VI, Chrono Trigger, or Dragon Quest SNES games. "
        "Top-down or 3/4 isometric RPG view. Every single element MUST show clearly visible individual square pixels. "
        "NO smooth gradients, NO photorealistic elements. Purely retro video game pixel art."
    ),
    "lowpoly-iso": (
        "STYLE REQUIREMENT: 3D low-poly isometric diorama style. "
        "MUST HAVE: Geometric shapes with minimal polygons, flat color blocks, soft ambient occlusion shadows, "
        "NO detailed textures, clean hard edges, isometric 45-degree viewing angle. "
        "Think Monument Valley or modern minimalist 3D illustration. Stylized and toylike."
    ),
    "watercolor-dream": (
        "STYLE REQUIREMENT: Traditional watercolor painting on textured paper. "
        "MUST HAVE: Flowing pigments with visible water blooms, soft wet-on-wet color bleeding, "
        "loose expressive brush strokes, luminous transparent washes, paper grain texture visible. "
        "Ethereal, dreamlike, with intentional color bleeds and organic edges. Hand-painted feel."
    ),
    "noir-sketch": (
        "STYLE REQUIREMENT: High-contrast charcoal or ink sketch in film noir style. "
        "MUST HAVE: Dramatic shadows with deep blacks, heavy cross-hatching technique, "
        "bold ink lines, stark black and white ONLY (no color), expressive gestural marks. "
        "Moody atmospheric lighting with harsh contrasts. Think Sin City or classic noir comics."
    ),
    "art-nouveau": (
        "STYLE REQUIREMENT: Art Nouveau poster illustration circa 1890-1910. "
        "MUST HAVE: Flowing organic curved lines, decorative floral borders, elegant stylized typography integrated, "
        "muted earth tones (ochre, sage, terracotta) with jewel tone accents, ornamental Celtic-inspired patterns. "
        "Think Alphonse Mucha. Romantic, elegant, highly decorative."
    ),
    "comic-book": (
        "STYLE REQUIREMENT: Classic American comic book illustration style 1960s-80s. "
        "MUST HAVE: Bold black ink outlines, Ben-Day dot patterns for shading, dynamic angular composition, "
        "saturated primary colors (red, blue, yellow), vintage four-color printing halftone dots visible. "
        "Think Jack Kirby or classic Marvel/DC. Action-oriented, dramatic angles."
    ),
    "oil-painting": (
        "STYLE REQUIREMENT: Classical oil painting in the style of Old Masters. "
        "MUST HAVE: Visible thick brush strokes with impasto texture, rich layered glazes, "
        "dramatic chiaroscuro lighting (strong light/shadow contrast), warm amber undertones. "
        "Renaissance or Baroque composition. Think Rembrandt or Caravaggio. Museum-quality fine art."
    ),
}


def save_config(path: Path, cfg: WorldConfig) -> None:
    write_json(path, asdict(cfg))


def load_config(path: Path) -> WorldConfig:
    data = read_json(path, {})
    return WorldConfig(**data)

