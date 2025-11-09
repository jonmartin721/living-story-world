from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional, Tuple

from .models import WorldConfig, WorldState, Chapter
from .presets import PRESETS, DEFAULT_PRESET
from .config import STYLE_PACKS


def _get_client():
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("OpenAI SDK not installed. Run: pip install openai>=1.0") from e
    return OpenAI()


def _build_chapter_prompt(cfg: WorldConfig, state: WorldState, focus: Optional[str], preset_key: Optional[str] = None) -> Tuple[str, list[dict], float]:
    style = STYLE_PACKS.get(cfg.style_pack, STYLE_PACKS["storybook-ink"])  # textual art bible for images
    preset = PRESETS.get(preset_key or "", DEFAULT_PRESET)
    sys = (
        "You are a narrative engine for a persistent storyworld. "
        "Write evocative, tightly paced chapters that advance arcs within a coherent world. "
        "Always include a single HTML comment at the very top containing JSON metadata with keys: "
        "scene_prompt (string describing a wide scene illustration), characters_in_scene (string array), "
        "summary (string), new_characters (array of {id, name, description}), new_locations (array of {id, name, description}). "
        "Introduce new characters or locations when they serve the story naturally. "
        + preset.system_directives
    )
    world_brief = {
        "title": cfg.title,
        "theme": cfg.theme,
        "tick": state.tick,
        "chapter_number": state.next_chapter,
        "known_characters": list(state.characters.keys()),
        "known_locations": list(state.locations.keys()),
    }
    user = (
        "World brief: "
        + json.dumps(world_brief)
        + "\n\n"
        + (f"Focus: {focus}\n\n" if focus else "")
        + "Write Chapter "
        + str(state.next_chapter)
        + ":\n"
        + "Title (H1), rich prose (700-900 words), light dialogue, tangible sensory detail, and a memorable closing beat.\n"
        + 'At top, put: <!-- {"scene_prompt": string, "characters_in_scene": [string], "summary": string, '
        + '"new_characters": [{id, name, description}], "new_locations": [{id, name, description}]} -->\n'
        + "Include new_characters/new_locations arrays (can be empty if focusing on existing cast). Use kebab-case for IDs.\n"
        + f"Art direction (for scene_prompt only): {style}.\n"
        + f"Preset instructions: {preset.text_instructions}"
    )
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ]
    return style, messages, preset.temperature


def _parse_meta(md_text: str) -> Dict[str, object]:
    # Expect: <!-- {...} --> at the top
    m = re.search(r"<!--\s*(\{.*?\})\s*-->", md_text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def generate_chapter(
    base_dir: Path,
    cfg: WorldConfig,
    state: WorldState,
    focus: Optional[str] = None,
    make_scene_image: bool = True,
    preset_key: Optional[str] = None,
) -> Chapter:
    client = _get_client()

    style, messages, temp = _build_chapter_prompt(cfg, state, focus, preset_key=preset_key)
    resp = client.chat.completions.create(
        model=cfg.text_model,
        messages=messages,
        temperature=temp,
    )
    md = resp.choices[0].message.content or ""

    meta = _parse_meta(md)
    scene_prompt = str(meta.get("scene_prompt", "")) if isinstance(meta, dict) else ""
    summary = str(meta.get("summary", "")) if isinstance(meta, dict) else None
    characters_in_scene = meta.get("characters_in_scene", []) if isinstance(meta, dict) else []
    if not isinstance(characters_in_scene, list):
        characters_in_scene = []

    # Extract and register new entities
    new_characters = meta.get("new_characters", []) if isinstance(meta, dict) else []
    new_locations = meta.get("new_locations", []) if isinstance(meta, dict) else []

    _register_new_entities(state, new_characters, new_locations)

    num = state.next_chapter
    filename = f"chapter-{num:04d}.md"
    chapter_path = base_dir / "chapters" / filename
    chapter_path.write_text(md, encoding="utf-8")

    ch = Chapter(
        number=num,
        title=_extract_title(md) or f"Chapter {num}",
        filename=filename,
        summary=summary,
        scene_prompt=scene_prompt,
        characters_in_scene=[str(c) for c in characters_in_scene],
    )

    # Optionally queue scene image generation marker (actual pixel gen in image module)
    if make_scene_image and scene_prompt:
        _write_scene_request(base_dir, num, cfg.style_pack, scene_prompt)

    return ch


def _extract_title(md: str) -> Optional[str]:
    for line in md.splitlines():
        if line.strip().startswith("# "):
            return line.strip("# ").strip()
    return None


def _write_scene_request(base_dir: Path, chapter_num: int, style_pack: str, scene_prompt: str) -> None:
    reqs = base_dir / "media" / "scene_requests.json"
    data = []
    if reqs.exists():
        try:
            data = json.loads(reqs.read_text(encoding="utf-8"))
        except Exception:
            data = []
    data.append({
        "chapter": chapter_num,
        "style_pack": style_pack,
        "prompt": scene_prompt,
    })
    reqs.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _register_new_entities(state: WorldState, new_characters: list, new_locations: list) -> None:
    """Register new characters and locations from chapter metadata into world state."""
    from .models import Character, Location

    # Add new characters
    if isinstance(new_characters, list):
        for char_data in new_characters:
            if isinstance(char_data, dict) and "id" in char_data and "name" in char_data:
                char_id = str(char_data["id"])
                if char_id not in state.characters:
                    char = Character(
                        id=char_id,
                        name=str(char_data.get("name", char_id)),
                        description=str(char_data.get("description", "")),
                        epithet=str(char_data.get("epithet", "")),
                        traits=char_data.get("traits", [])
                    )
                    state.characters[char_id] = char.__dict__
                    print(f"[WORLD] Added new character: {char.name} ({char_id})", flush=True)

    # Add new locations
    if isinstance(new_locations, list):
        for loc_data in new_locations:
            if isinstance(loc_data, dict) and "id" in loc_data and "name" in loc_data:
                loc_id = str(loc_data["id"])
                if loc_id not in state.locations:
                    loc = Location(
                        id=loc_id,
                        name=str(loc_data.get("name", loc_id)),
                        description=str(loc_data.get("description", "")),
                        tags=loc_data.get("tags", [])
                    )
                    state.locations[loc_id] = loc.__dict__
                    print(f"[WORLD] Added new location: {loc.name} ({loc_id})", flush=True)
