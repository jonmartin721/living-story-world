from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    description: str
    temperature: float
    system_directives: str
    text_instructions: str


PRESETS: Dict[str, Preset] = {
    "cozy-adventure": Preset(
        key="cozy-adventure",
        name="Cozy Adventure",
        description="Wholesome explorations, wonder, gentle stakes, warm tone.",
        temperature=0.9,
        system_directives=(
            "Write with warmth and curiosity. Keep stakes human-scale; avoid graphic violence. "
            "Balance narration with dialogue; favor sensory detail (smell, texture, sound)."
        ),
        text_instructions=(
            "Lean into small acts of courage, cozy spaces, and companionship. "
            "Include at least one tactile object or motif that carries through the chapter."
        ),
    ),
    "noir-mystery": Preset(
        key="noir-mystery",
        name="Noir Mystery",
        description="Moody, wry, metaphor-rich, moral gray zones.",
        temperature=0.85,
        system_directives=(
            "Adopt a noir sensibility: sparse but evocative prose, sharp dialogue, and layered clues. "
            "Cynicism tempered by wit; keep answers just out of reach."
        ),
        text_instructions=(
            "Feature a reversible clue and a reveal that raises more questions. "
            "Use precise, image-rich metaphors; keep momentum taut."
        ),
    ),
    "epic-fantasy": Preset(
        key="epic-fantasy",
        name="Epic Fantasy",
        description="Grand vistas, mythic stakes, lyrical cadence.",
        temperature=1.0,
        system_directives=(
            "Use lyrical, myth-tinged prose with sweeping scale and resonant imagery. "
            "Build momentum toward a resonant closing beat; keep character voices distinct."
        ),
        text_instructions=(
            "Include a moment of awe, a whispered history, and a choice with cost."
        ),
    ),
    "solarpunk-explorer": Preset(
        key="solarpunk-explorer",
        name="Solarpunk Explorer",
        description="Inventive systems, hopepunk tone, practical wonder.",
        temperature=0.88,
        system_directives=(
            "Optimistic, systems-aware storytelling with practical ingenuity and cooperative problem-solving. "
            "Emphasize ecology, craft, and accessible tech."
        ),
        text_instructions=(
            "Show a small technology or practice that helps the community; describe how it works."
        ),
    ),
}

DEFAULT_PRESET = PRESETS["cozy-adventure"]

