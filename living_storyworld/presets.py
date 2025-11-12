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
    "gothic-horror": Preset(
        key="gothic-horror",
        name="Gothic Horror",
        description="Atmospheric dread, psychological tension, haunting beauty.",
        temperature=0.92,
        system_directives=(
            "Build oppressive atmosphere through architecture, weather, and shadow. "
            "Favor psychological unease over shock; let dread accumulate. Keep prose ornate but precise."
        ),
        text_instructions=(
            "Include a threshold crossed, an inherited curse or secret, and something beautiful made sinister. "
            "End on lingering unease rather than resolution."
        ),
    ),
    "space-opera": Preset(
        key="space-opera",
        name="Space Opera",
        description="Galactic scale, diverse cultures, political intrigue among the stars.",
        temperature=0.95,
        system_directives=(
            "Balance vast scale with personal stakes. Feature diverse alien perspectives and cultures. "
            "Mix action with diplomacy; keep tech consistent within the scene."
        ),
        text_instructions=(
            "Show at least two different cultures or species interacting. "
            "Include one small detail that reveals larger political tensions."
        ),
    ),
    "slice-of-life": Preset(
        key="slice-of-life",
        name="Slice of Life",
        description="Quiet moments, everyday magic, character-focused intimacy.",
        temperature=0.87,
        system_directives=(
            "Find meaning in the mundane. Focus on internal states, small gestures, and subtle shifts. "
            "Let silence and pauses breathe. Avoid melodrama; keep stakes personal and grounded."
        ),
        text_instructions=(
            "Center a routine activity that reveals character. Include sensory details of home or comfort. "
            "Let emotion emerge through observation rather than declaration."
        ),
    ),
    "cosmic-horror": Preset(
        key="cosmic-horror",
        name="Cosmic Horror",
        description="Existential dread, incomprehensible forces, sanity fraying.",
        temperature=0.93,
        system_directives=(
            "Emphasize the unknowable and the insignificance of human concerns. "
            "Use geometric or abstract imagery; avoid explaining the horror. Build disorientation."
        ),
        text_instructions=(
            "Feature something that defies natural law or comprehension. "
            "Show a character's worldview cracking. Use precise, clinical language for the impossible."
        ),
    ),
    "cyberpunk-noir": Preset(
        key="cyberpunk-noir",
        name="Cyberpunk Noir",
        description="High-tech low-life, neon-soaked streets, corporate shadows.",
        temperature=0.86,
        system_directives=(
            "Blend noir sensibility with tech-saturated future. Sharp contrasts: neon and shadow, wealth and poverty. "
            "Feature tech as both tool and threat. Keep dialogue punchy and world-weary."
        ),
        text_instructions=(
            "Show technology integrated into daily life. Include corporate influence or surveillance. "
            "Feature at least one 'jacked-in' or augmented moment."
        ),
    ),
    "whimsical-fairy-tale": Preset(
        key="whimsical-fairy-tale",
        name="Whimsical Fairy Tale",
        description="Playful enchantment, talking creatures, moral lessons with heart.",
        temperature=0.96,
        system_directives=(
            "Write with childlike wonder and clever wordplay. Feature anthropomorphized elements. "
            "Balance whimsy with gentle wisdom. Use classic fairy tale rhythms and repetition."
        ),
        text_instructions=(
            "Include a magical rule or transformation. Feature a riddle, song, or rhyme. "
            "Let a small creature or object offer unexpected help."
        ),
    ),
    "post-apocalyptic": Preset(
        key="post-apocalyptic",
        name="Post-Apocalyptic",
        description="Survival amid ruins, harsh beauty, rebuilding hope.",
        temperature=0.89,
        system_directives=(
            "Balance bleakness with resilience. Show scarcity and adaptation. "
            "Find beauty in decay and determination. Keep resource concerns tactile and present."
        ),
        text_instructions=(
            "Feature salvaged or repurposed technology. Show evidence of the old world. "
            "Include a moment of found beauty or preserved culture."
        ),
    ),
    "historical-intrigue": Preset(
        key="historical-intrigue",
        name="Historical Intrigue",
        description="Period authenticity, courtly machinations, personal stakes in grand events.",
        temperature=0.84,
        system_directives=(
            "Ground narrative in historical texture: manners, technology, power structures. "
            "Feature layered social dynamics and coded communication. Balance period voice with accessibility."
        ),
        text_instructions=(
            "Include period-accurate details of dress, food, or custom. "
            "Show power dynamics through gesture or protocol. Feature written correspondence or formal address."
        ),
    ),
}

DEFAULT_PRESET = PRESETS["cozy-adventure"]
