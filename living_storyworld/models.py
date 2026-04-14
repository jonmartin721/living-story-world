from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass
class Character:
    id: str
    name: str
    epithet: Optional[str] = None
    traits: List[str] = field(default_factory=list)
    description: Optional[str] = None
    visual_profile: Dict[str, str] = field(
        default_factory=dict
    )  # style tokens, palette hints

    @classmethod
    def from_dict(cls, data: "Character | dict") -> "Character":
        if isinstance(data, cls):
            return data
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Location:
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: "Location | dict") -> "Location":
        if isinstance(data, cls):
            return data
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Item:
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: "Item | dict") -> "Item":
        if isinstance(data, cls):
            return data
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Choice:
    id: str
    text: str
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: "Choice | dict") -> "Choice":
        if isinstance(data, cls):
            return data
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Chapter:
    number: int
    title: str
    filename: str
    summary: Optional[str] = None
    ai_summary: Optional[str] = None  # AI-generated concise summary for continuity
    scene_prompt: Optional[str] = None
    image_prompt: Optional[str] = None  # Concise prompt optimized for image generation
    characters_in_scene: List[str] = field(default_factory=list)
    choices: List[Choice] = field(default_factory=list)
    selected_choice_id: Optional[str] = None
    choice_reasoning: Optional[str] = None
    generated_at: Optional[str] = None  # ISO format timestamp
    text_model_used: Optional[str] = None  # Model used for text generation
    image_model_used: Optional[str] = None  # Model used for image generation

    def __post_init__(self) -> None:
        self.choices = [Choice.from_dict(choice) for choice in self.choices]

    @classmethod
    def from_dict(cls, data: "Chapter | dict") -> "Chapter":
        if isinstance(data, cls):
            return data
        payload = dict(data)
        payload["choices"] = [
            Choice.from_dict(choice) for choice in payload.get("choices", [])
        ]
        return cls(**payload)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorldConfig:
    title: str
    slug: str
    theme: str
    style_pack: str = "storybook-ink"
    text_model: str = (
        "gemini-2.5-flash"  # Will be overridden by user's chosen provider during world creation
    )
    image_model: str = "flux-dev"
    maturity_level: str = "general"  # general, teen, mature, explicit
    preset: str = "cozy-adventure"  # Narrative preset defines the vibe/tone
    enable_choices: bool = False  # Interactive chapter choices

    # NAI-style memory system
    memory: Optional[str] = (
        None  # Always included in context (lore, background, key facts)
    )
    # Inserted at strategic point in prompt (style guidance, tone)
    authors_note: Optional[str] = None
    world_instructions: Optional[str] = (
        None  # Custom instructions specific to this world
    )

    @classmethod
    def from_dict(cls, data: "WorldConfig | dict") -> "WorldConfig":
        if isinstance(data, cls):
            return data
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorldState:
    tick: int = 0
    next_chapter: int = 1
    characters: Dict[str, Character] = field(default_factory=dict)
    locations: Dict[str, Location] = field(default_factory=dict)
    items: Dict[str, Item] = field(default_factory=dict)
    chapters: List[Chapter] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.characters = {
            key: Character.from_dict(value) for key, value in self.characters.items()
        }
        self.locations = {
            key: Location.from_dict(value) for key, value in self.locations.items()
        }
        self.items = {key: Item.from_dict(value) for key, value in self.items.items()}
        self.chapters = [Chapter.from_dict(chapter) for chapter in self.chapters]

    @classmethod
    def from_dict(cls, data: "WorldState | dict") -> "WorldState":
        if isinstance(data, cls):
            return data
        payload = dict(data)
        return cls(
            tick=payload.get("tick", 0),
            next_chapter=payload.get("next_chapter", 1),
            characters={
                key: Character.from_dict(value)
                for key, value in payload.get("characters", {}).items()
            },
            locations={
                key: Location.from_dict(value)
                for key, value in payload.get("locations", {}).items()
            },
            items={
                key: Item.from_dict(value)
                for key, value in payload.get("items", {}).items()
            },
            chapters=[
                Chapter.from_dict(chapter) for chapter in payload.get("chapters", [])
            ],
        )

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "next_chapter": self.next_chapter,
            "characters": {
                key: character.to_dict() for key, character in self.characters.items()
            },
            "locations": {
                key: location.to_dict() for key, location in self.locations.items()
            },
            "items": {key: item.to_dict() for key, item in self.items.items()},
            "chapters": [chapter.to_dict() for chapter in self.chapters],
        }


@dataclass(frozen=True)
class ResolvedGenerationSettings:
    text_provider: str
    image_provider: str
    text_provider_order: List[str]
    preferred_text_model: Optional[str]
    preferred_image_model: Optional[str]


@dataclass
class GeneratedChapterDraft:
    markdown: str
    title: str
    summary: Optional[str] = None
    scene_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    characters_in_scene: List[str] = field(default_factory=list)
    choices: List[Choice] = field(default_factory=list)
    text_model_used: Optional[str] = None
    text_provider_used: Optional[str] = None
    new_characters: List[dict] = field(default_factory=list)
    new_locations: List[dict] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class ChapterJobResult:
    chapter: Chapter
    scene: Optional[str] = None
