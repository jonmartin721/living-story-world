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
class Choice:
    id: str
    text: str
    description: Optional[str] = None


@dataclass
class Chapter:
    number: int
    title: str
    filename: str
    summary: Optional[str] = None
    ai_summary: Optional[str] = None  # AI-generated concise summary for continuity
    scene_prompt: Optional[str] = None
    characters_in_scene: List[str] = field(default_factory=list)
    choices: List[Choice] = field(default_factory=list)
    selected_choice_id: Optional[str] = None
    choice_reasoning: Optional[str] = None
    generated_at: Optional[str] = None  # ISO format timestamp
    text_model_used: Optional[str] = None  # Model used for text generation
    image_model_used: Optional[str] = None  # Model used for image generation


@dataclass
class WorldConfig:
    title: str
    slug: str
    theme: str
    style_pack: str = "storybook-ink"
    text_model: str = "gpt-4o-mini"
    maturity_level: str = "general"  # general, teen, mature, explicit
    preset: str = "cozy-adventure"  # Narrative preset defines the vibe/tone
    enable_choices: bool = False  # Interactive chapter choices

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

