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
from .settings import load_user_settings, get_api_key_for_provider
from .providers import get_text_provider


def _get_client():
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("OpenAI SDK not installed. Run: pip install openai>=1.0") from e
    return OpenAI()


def _build_chapter_prompt(cfg: WorldConfig, state: WorldState, focus: Optional[str], chapter_length: str = "medium") -> Tuple[str, list[dict], float]:
    style = STYLE_PACKS.get(cfg.style_pack, STYLE_PACKS["storybook-ink"])  # textual art bible for images
    preset = PRESETS.get(cfg.preset, DEFAULT_PRESET)

    # Load global instructions from user settings
    settings = load_user_settings()
    global_instructions = settings.global_instructions or ""

    # Maturity level guidance
    maturity_guidance = {
        "general": "Keep content appropriate for all ages. Avoid violence, profanity, and mature themes.",
        "teen": "Keep content appropriate for teen audiences. Mild violence and tension is acceptable, but avoid explicit content.",
        "mature": "Content may include moderate violence, adult themes, and occasional strong language. Keep sexual content subtle/implied.",
        "explicit": "Content may include graphic violence, explicit language, and mature sexual themes. Write authentically without censorship."
    }
    maturity_instruction = maturity_guidance.get(cfg.maturity_level, maturity_guidance["general"])

    # Build system message with global + world-specific instructions
    sys_parts = [
        "You are a narrative engine for a persistent storyworld. "
        "Write evocative, tightly paced chapters that advance arcs within a coherent world. "
        "Always include a single HTML comment at the very top containing JSON metadata with keys: "
        "scene_prompt (string describing a wide scene illustration), characters_in_scene (string array), "
        "summary (string), new_characters (array of {id, name, description}), new_locations (array of {id, name, description}). "
        "Introduce new characters or locations when they serve the story naturally. "
        + preset.system_directives,
        f"\n\nMaturity Level: {maturity_instruction}"
    ]

    # Add global instructions if present
    if global_instructions:
        sys_parts.append(f"\n\nGlobal Instructions: {global_instructions}")

    # Add world-specific instructions if present
    if cfg.world_instructions:
        sys_parts.append(f"\n\nWorld Instructions: {cfg.world_instructions}")

    sys = "".join(sys_parts)

    # Build story summary from previous chapters for continuity
    story_so_far = []
    if state.chapters:
        # Include summaries from recent chapters (last 3) for better continuity
        recent_chapters = state.chapters[-3:]
        for ch in recent_chapters:
            if ch.summary:
                story_so_far.append(f"Chapter {ch.number}: {ch.summary}")

    world_brief = {
        "title": cfg.title,
        "theme": cfg.theme,
        "tick": state.tick,
        "chapter_number": state.next_chapter,
        "known_characters": list(state.characters.keys()),
        "known_locations": list(state.locations.keys()),
    }

    # Build user message with memory and author's note
    user_parts = []

    # Add memory/lore first (always in context)
    if cfg.memory:
        user_parts.append(f"Memory/Lore:\n{cfg.memory}\n\n")

    user_parts.append("World brief: " + json.dumps(world_brief) + "\n\n")

    # Add story summary for continuity
    if story_so_far:
        user_parts.append("Story so far:\n" + "\n".join(story_so_far) + "\n\n")

    # Add author's note (strategic placement for style guidance)
    if cfg.authors_note:
        user_parts.append(f"Author's Note: {cfg.authors_note}\n\n")

    if focus:
        user_parts.append(f"Focus: {focus}\n\n")

    # Variable chapter length with random variation
    import random
    length_config = {
        "short": (400, 600),    # Base length
        "medium": (800, 1200),  # 2x short
        "long": (1600, 2400)    # 4x short
    }
    min_words, max_words = length_config.get(chapter_length, length_config["medium"])
    # Add ±10% random variation for natural feel
    variation = random.uniform(0.9, 1.1)
    min_words = int(min_words * variation)
    max_words = int(max_words * variation)

    user_parts.extend([
        f"Write Chapter {state.next_chapter}:\n",
        f"Start with a unique chapter title as H1 (do NOT include 'Chapter {state.next_chapter}' in the title - just the evocative name). ",
        f"Then write {min_words}-{max_words} words of rich prose with light dialogue, tangible sensory detail, and a memorable closing beat.\n",
        'At top, put: <!-- {"scene_prompt": string, "characters_in_scene": [string], "summary": string, ',
        '"new_characters": [{id, name, description}], "new_locations": [{id, name, description}]} -->\n',
        "Include new_characters/new_locations arrays (can be empty if focusing on existing cast). Use kebab-case for IDs.\n",
        f"Art direction (for scene_prompt only): {style}.\n",
        f"Preset instructions: {preset.text_instructions}"
    ])

    user = "".join(user_parts)

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
    chapter_length: str = "medium",
) -> Chapter:
    # Load settings to determine which provider to use
    settings = load_user_settings()
    text_provider_name = settings.text_provider
    api_key = get_api_key_for_provider(text_provider_name, settings)

    # Get the text provider
    try:
        provider = get_text_provider(text_provider_name, api_key=api_key)
    except Exception as e:
        # Fallback to legacy OpenAI client if provider setup fails
        print(f"[WARN] Provider {text_provider_name} failed, falling back to OpenAI: {e}", flush=True)
        client = _get_client()
        style, messages, temp = _build_chapter_prompt(cfg, state, focus, chapter_length)
        resp = client.chat.completions.create(
            model=cfg.text_model,
            messages=messages,
            temperature=temp,
        )
        md = resp.choices[0].message.content or ""
    else:
        # Use the provider abstraction
        style, messages, temp = _build_chapter_prompt(cfg, state, focus, chapter_length)
        result = provider.generate(messages, temperature=temp, model=cfg.text_model)
        md = result.content
        print(f"[INFO] Generated chapter using {result.provider} ({result.model}), cost: ${result.estimated_cost:.4f}", flush=True)

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
    import re
    for line in md.splitlines():
        if line.strip().startswith("# "):
            title = line.strip("# ").strip()
            # Strip "Chapter X:" or "Chapter X -" prefix if present
            title = re.sub(r'^Chapter\s+\d+\s*[:\-]\s*', '', title, flags=re.IGNORECASE)
            return title
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
