from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Character:
    id: str
    name: str
    epithet: Optional[str] = None
    traits: List[str] = field(default_factory=list)
    description: Optional[str] = None
    visual_profile: Dict[str, str] = field(default_factory=dict)  # style tokens, palette hints


@dataclass
class Location:
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Item:
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Chapter:
    number: int
    title: str
    filename: str
    summary: Optional[str] = None
    scene_prompt: Optional[str] = None
    characters_in_scene: List[str] = field(default_factory=list)


@dataclass
class WorldConfig:
    title: str
    slug: str
    theme: str
    style_pack: str = "storybook-ink"
    text_model: str = "gpt-4o-mini"
    image_model: str = "flux-schnell"
    maturity_level: str = "general"  # general, teen, mature, explicit
    preset: str = "cozy-adventure"  # Narrative preset defines the vibe/tone
    chapter_length: str = "medium"  # short, medium (2x short), long (4x short)

    # NAI-style memory system
    memory: Optional[str] = None  # Always included in context (lore, background, key facts)
    authors_note: Optional[str] = None  # Inserted at strategic point in prompt (style guidance, tone)
    world_instructions: Optional[str] = None  # Custom instructions specific to this world


@dataclass
class WorldState:
    tick: int = 0
    next_chapter: int = 1
    characters: Dict[str, Character] = field(default_factory=dict)
    locations: Dict[str, Location] = field(default_factory=dict)
    items: Dict[str, Item] = field(default_factory=dict)
    chapters: List[Chapter] = field(default_factory=list)

