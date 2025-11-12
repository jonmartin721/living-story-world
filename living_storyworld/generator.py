from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import STYLE_PACKS
from .models import Chapter, Choice, WorldConfig, WorldState
from .presets import DEFAULT_PRESET, PRESETS
from .providers import get_text_provider
from .settings import get_api_key_for_provider, load_user_settings

logger = logging.getLogger(__name__)


def _get_client():
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "OpenAI SDK not installed. Run: pip install openai>=1.0"
        ) from e
    return OpenAI()


def _build_chapter_prompt(
    cfg: WorldConfig, state: WorldState, chapter_length: str = "medium"
) -> Tuple[str, list[dict], float]:
    # textual art bible for images
    style = STYLE_PACKS.get(cfg.style_pack, STYLE_PACKS["storybook-ink"])
    preset = PRESETS.get(cfg.preset, DEFAULT_PRESET)

    # Load global instructions from user settings
    settings = load_user_settings()
    global_instructions = settings.global_instructions or ""

    # Maturity level guidance
    maturity_guidance = {
        "general": "Write family-friendly content suitable for all ages. Keep themes light and appropriate.",
        "teen": "Write young adult fiction. Include tension, conflict, and emotional depth appropriate for teen readers.",
        "mature": "Write adult fiction with mature themes and realistic situations. Use authentic language and explore complex emotional landscapes.",
        "explicit": "Write unrestricted adult fiction with full creative freedom. Portray mature themes authentically and unflinchingly as serves the story.",
    }
    maturity_instruction = maturity_guidance.get(
        cfg.maturity_level, maturity_guidance["general"]
    )

    # Build system message with global + world-specific instructions
    metadata_keys = (
        "scene_prompt (string describing a wide scene illustration), characters_in_scene (string array), "
        "summary (string), new_characters (array of {id, name, description}), new_locations (array of {id, name, description})"
    )

    # Add choices instruction if enabled
    if cfg.enable_choices:
        metadata_keys += (
            ", choices (array of 3 objects with {id, text, description}), story_health (object with {is_repetitive: bool, natural_ending_reached: bool, needs_fresh_direction: bool, notes: string}). "
            "Choices should be immediate actions or reactions, not story endings. "
            "Examples: ask questions, make decisions about current situation, take action in the moment. "
            "Each choice should lead to new complications, not resolve everything."
        )

    sys_parts = [
        f"This is a fictional story for entertainment purposes only. Write a compelling chapter that advances the story. "
        f"Include metadata as JSON comment with: {metadata_keys} "
        + preset.system_directives,
        f"Maturity: {maturity_instruction}",
        "Keep the story moving with action and exploration. Change locations regularly, avoid long conversations in one place. Characters should be doing things, not just talking.",
        "Make the world feel big. Characters can travel to new places and discover unexpected territories. Each chapter should reveal something new about the world.",
        "Write realistic characters with flaws and contradictions. People can be selfish, make bad choices, or have hidden motives. Not everyone gets redeemed.",
        "CRITICAL: Use fresh, memorable character names. NEVER use these overused AI names: Elara, Lyra, Aria, Kira, Zara, Seraphina, Theron, Kael, Alaric, Aiden, Eira, Orion. Choose distinctive, unexpected names that fit the world's culture.",
        "Vary each chapter - if you've been in forests recently, go somewhere different. If there was a lot of talking, add more action. Keep the story progressing.",
        "In metadata, note if the story feels repetitive or has reached a natural ending.",
    ]

    # Add global instructions if present
    if global_instructions:
        sys_parts.append(f"\n\nGlobal Instructions: {global_instructions}")

    # Add world-specific instructions if present
    if cfg.world_instructions:
        sys_parts.append(f"\n\nWorld Instructions: {cfg.world_instructions}")

    sys = "".join(sys_parts)

    # Build efficient story context using stored summaries
    story_context = []
    if state.chapters:
        # Get summaries from recent chapters (last 3-4 for focused context without over-anchoring)
        recent_chapters = (
            state.chapters[-4:] if len(state.chapters) >= 4 else state.chapters
        )

        for ch in recent_chapters:
            chapter_info = [f"Chapter {ch.number}: {ch.title}"]

            # Use lighter summaries to avoid over-anchoring on recent events
            if hasattr(ch, "ai_summary") and ch.ai_summary:
                chapter_info.append(f"{ch.ai_summary}")
            elif ch.summary:
                chapter_info.append(f"{ch.summary}")

            # Include the selected choice for continuity, but skip reasoning to reduce anchor weight
            if ch.selected_choice_id and ch.choices:
                selected_choice = next(
                    (c for c in ch.choices if c.id == ch.selected_choice_id), None
                )
                if selected_choice:
                    chapter_info.append(f"Choice: {selected_choice.text}")

            story_context.append("\n".join(chapter_info))

        # Create a chained story progression with broader strokes
        if len(state.chapters) > 4:
            # For longer stories, include brief arc summary
            older_summary = []
            for ch in state.chapters[-8:-4]:  # Earlier chapters
                if hasattr(ch, "ai_summary") and ch.ai_summary:
                    # Just title and key beat, no details
                    older_summary.append(f"Ch {ch.number} ({ch.title})")
                elif ch.summary:
                    older_summary.append(f"Ch {ch.number} ({ch.title})")
            if older_summary:
                story_context.insert(
                    0, "Earlier progression: " + " → ".join(older_summary)
                )

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

    # Add comprehensive story context for continuity
    if story_context:
        user_parts.append("Story progression:\n" + "\n\n".join(story_context) + "\n\n")

    # Add author's note (strategic placement for style guidance)
    if cfg.authors_note:
        user_parts.append(f"Author's Note: {cfg.authors_note}\n\n")

    # Add previous choice context LAST (strongest signal - most recent in context)
    if cfg.enable_choices and state.chapters:
        prev_chapter = state.chapters[-1]
        if prev_chapter.selected_choice_id and prev_chapter.choices:
            selected_choice = next(
                (
                    c
                    for c in prev_chapter.choices
                    if c.id == prev_chapter.selected_choice_id
                ),
                None,
            )
            if selected_choice:
                choice_context = (
                    f"READER'S CHOICE (PRIMARY DIRECTIVE): {selected_choice.text}\n\n"
                )
                choice_context += "This choice MUST be the central driver of this chapter. Build the narrative directly from the consequences and implications of this decision. Any optional focus/nudges above are secondary to honoring this choice.\n\n"
                user_parts.append(choice_context)

    # Variable chapter length with random variation
    import random

    length_config = {
        "short": (400, 600),  # Base length
        "medium": (800, 1200),  # 2x short
        "long": (1600, 2400),  # 4x short
    }
    min_words, max_words = length_config.get(chapter_length, length_config["medium"])
    # Add ±10% random variation for natural feel
    variation = random.uniform(0.9, 1.1)
    min_words = int(min_words * variation)
    max_words = int(max_words * variation)

    # Build metadata format string
    metadata_format = '<!-- {"scene_prompt": string, "characters_in_scene": [string], "summary": string, '
    metadata_format += '"new_characters": [{id, name, description}], "new_locations": [{id, name, description}]'
    if cfg.enable_choices:
        metadata_format += (
            ', "choices": [{"id": string, "text": string, "description": string}], '
        )
        metadata_format += '"story_health": {"is_repetitive": bool, "natural_ending_reached": bool, "needs_fresh_direction": bool, "notes": string}'
    metadata_format += "} -->\n"

    # Special instructions for first chapter
    if state.next_chapter == 1:
        user_parts.append(
            "\n\nFIRST CHAPTER GUIDANCE:\n"
            "Establish a compelling narrative seed that will grow into an engaging story arc. "
            "Start with a focal character in a specific situation - NOT a generic introduction, but an active moment that reveals character through action. "
            "This could be a protagonist, antagonist, or key figure depending on what best serves the theme and tone. "
            "Introduce ONE clear dramatic question or tension point that will drive the next few chapters (a mystery, a goal, a problem, a choice, a threat). "
            "Keep it focused: establish the character, their immediate situation, and one clear narrative hook. "
            "Don't overwhelm with worldbuilding - let details emerge naturally through the scene. "
            "End on a note of momentum: a decision made, a journey begun, a question raised, or a complication discovered. "
            "The reader should feel intrigued about what happens next, not lost in exposition. "
            "Think: 'opening scene of a good novel' not 'encyclopedia entry'.\n\n"
        )

    user_parts.extend(
        [
            f"Write Chapter {state.next_chapter}:\n",
            f"Start with a unique chapter title as H1 (do NOT include 'Chapter {
            state.next_chapter}' in the title - just the evocative name). ",
            f"Then write {min_words}-{max_words} words of rich prose emphasizing physical action, movement through spaces, and scene changes. ",
            "PUSH THE STORY FORWARD - introduce new complications, visit different locations, advance the timeline, reveal new information. ",
            "Avoid repeating locations or beats from recent chapters. Each chapter should feel like PROGRESS. ",
            "Minimize static dialogue - have characters talk while doing things, traveling, or exploring. ",
            "Include vivid sensory detail and a memorable closing beat.\n",
            f"At top, put: {metadata_format}",
            "Include new_characters/new_locations arrays (can be empty if focusing on existing cast). Use kebab-case for IDs.\n",
            "When creating new_characters, their descriptions should hint at complexity/flaws/contradictions, NOT just surface traits. "
            "AVOID generic AI names (Elara, Lyra, Aria, Kira, Theron, Kael, etc). Use distinctive names that match the world's culture. "
            "Examples: 'A merchant who smiles too much while calculating debts' not 'A friendly merchant'. "
            "'A priest haunted by what she did to get here' not 'A devoted priest'. Give them EDGES.\n",
            f"Art direction (for scene_prompt only): {style}.\n",
            f"Preset instructions: {preset.text_instructions}",
        ]
    )

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
    make_scene_image: bool = True,
    chapter_length: str = "medium",
) -> Chapter:
    # Load settings and get available providers for fallback
    from .settings import get_available_text_providers

    settings = load_user_settings()
    available_providers = get_available_text_providers(settings)

    if not available_providers:
        raise ValueError(
            "No text providers configured. Please add API keys in Settings."
        )

    # Try each available provider until one succeeds
    last_error = None
    for provider_name in available_providers:
        try:
            api_key = get_api_key_for_provider(provider_name, settings)
            provider = get_text_provider(provider_name, api_key=api_key)

            # Build prompt and generate
            style, messages, temp = _build_chapter_prompt(cfg, state, chapter_length)

            # Use provider's default model for consistency
            model = provider.get_default_model()

            result = provider.generate(messages, temperature=temp, model=model)
            md = result.content
            logger.info(
                "Generated chapter using %s (%s), cost: $%.4f",
                result.provider,
                result.model,
                result.estimated_cost,
            )
            break  # Success, exit loop

        except Exception as e:
            last_error = e
            error_msg = str(e)

            # Check if this was a safety filter issue
            is_safety_block = (
                "safety filter" in error_msg.lower() or "blocked" in error_msg.lower()
            )

            if len(available_providers) > 1:
                # We have fallback options
                remaining = [p for p in available_providers if p != provider_name]
                if is_safety_block:
                    logger.warning(
                        "%s blocked content (safety filters). Trying fallback provider: %s",
                        provider_name,
                        remaining[0] if remaining else "none",
                    )
                else:
                    logger.warning(
                        "%s failed: %s. Trying fallback provider: %s",
                        provider_name,
                        error_msg,
                        remaining[0] if remaining else "none",
                    )
            else:
                # No fallbacks available
                if is_safety_block:
                    raise ValueError(
                        f"Content blocked by {provider_name}'s safety filters. Try regenerating or configure additional text providers in Settings for automatic fallback."
                    )
                raise

    else:
        # All providers failed
        providers_tried = ", ".join(available_providers)
        raise ValueError(
            f"All text providers failed ({providers_tried}). Last error: {last_error}. Configure additional providers in Settings for better reliability."
        )

    meta = _parse_meta(md)
    scene_prompt = str(meta.get("scene_prompt", "")) if isinstance(meta, dict) else ""
    summary = str(meta.get("summary", "")) if isinstance(meta, dict) else None
    characters_in_scene = (
        meta.get("characters_in_scene", []) if isinstance(meta, dict) else []
    )
    if not isinstance(characters_in_scene, list):
        characters_in_scene = []

    # Extract and log story health if present
    if isinstance(meta, dict) and "story_health" in meta:
        story_health = meta.get("story_health", {})
        if isinstance(story_health, dict):
            is_repetitive = story_health.get("is_repetitive", False)
            natural_ending = story_health.get("natural_ending_reached", False)
            needs_fresh = story_health.get("needs_fresh_direction", False)
            health_notes = story_health.get("notes", "")

            # Log warning if story health issues detected
            if is_repetitive or natural_ending or needs_fresh:
                logger.info(
                    "Story health - Repetitive: %s, Natural End: %s, Needs Fresh: %s",
                    is_repetitive,
                    natural_ending,
                    needs_fresh,
                )
                if health_notes:
                    logger.info("Story health notes: %s", health_notes)

    # Extract choices if present
    choices = []
    if isinstance(meta, dict) and "choices" in meta:
        choices_data = meta.get("choices", [])
        if isinstance(choices_data, list):
            for choice_dict in choices_data:
                if (
                    isinstance(choice_dict, dict)
                    and "id" in choice_dict
                    and "text" in choice_dict
                ):
                    choices.append(
                        Choice(
                            id=str(choice_dict["id"]),
                            text=str(choice_dict["text"]),
                            description=str(choice_dict.get("description", "")),
                        )
                    )

    # Extract and register new entities
    new_characters = meta.get("new_characters", []) if isinstance(meta, dict) else []
    new_locations = meta.get("new_locations", []) if isinstance(meta, dict) else []

    _register_new_entities(state, new_characters, new_locations)

    num = state.next_chapter
    filename = f"chapter-{num:04d}.md"
    chapter_path = base_dir / "chapters" / filename
    chapter_path.write_text(md, encoding="utf-8")

    # Capture actual model used for text generation
    actual_text_model = model
    if hasattr(result, "model"):
        actual_text_model = result.model

    # Create chapter object
    ch = Chapter(
        number=num,
        title=_extract_title(md) or f"Chapter {num}",
        filename=filename,
        summary=summary,
        ai_summary=None,  # Will be set after AI summary generation
        scene_prompt=scene_prompt,
        characters_in_scene=[str(c) for c in characters_in_scene],
        choices=choices,
        text_model_used=actual_text_model,
    )

    # AI summary will be generated separately in parallel with image generation
    ch.ai_summary = None

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
            title = re.sub(r"^Chapter\s+\d+\s*[:\-]\s*", "", title, flags=re.IGNORECASE)
            return title
    return None


def _write_scene_request(
    base_dir: Path, chapter_num: int, style_pack: str, scene_prompt: str
) -> None:
    reqs = base_dir / "media" / "scene_requests.json"
    data = []
    if reqs.exists():
        try:
            data = json.loads(reqs.read_text(encoding="utf-8"))
        except Exception:
            data = []
    data.append(
        {
            "chapter": chapter_num,
            "style_pack": style_pack,
            "prompt": scene_prompt,
        }
    )
    reqs.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _register_new_entities(
    state: WorldState, new_characters: list, new_locations: list
) -> None:
    """Register new characters and locations from chapter metadata into world state."""
    from .models import Character, Location

    # Add new characters
    if isinstance(new_characters, list):
        for char_data in new_characters:
            if (
                isinstance(char_data, dict)
                and "id" in char_data
                and "name" in char_data
            ):
                char_id = str(char_data["id"])
                if char_id not in state.characters:
                    char = Character(
                        id=char_id,
                        name=str(char_data.get("name", char_id)),
                        description=str(char_data.get("description", "")),
                        epithet=str(char_data.get("epithet", "")),
                        traits=char_data.get("traits", []),
                    )
                    state.characters[char_id] = char.__dict__
                    logger.debug("Added new character: %s (%s)", char.name, char_id)

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
                        tags=loc_data.get("tags", []),
                    )
                    state.locations[loc_id] = loc.__dict__
                    logger.debug("Added new location: %s (%s)", loc.name, loc_id)


async def infer_choice_reasoning(
    choice_text: str, chapter_summary: str, world_theme: str, cfg: WorldConfig
) -> str:
    """Use LLM to infer why the reader chose this option.

    Args:
        choice_text: The text of the selected choice
        chapter_summary: Summary of the chapter where the choice was made
        world_theme: The overall theme of the world
        cfg: World configuration for model settings

    Returns:
        A 1-2 sentence explanation of the narrative intent behind the choice
    """
    settings = load_user_settings()
    text_provider_name = settings.text_provider
    api_key = get_api_key_for_provider(text_provider_name, settings)
    text_model = settings.default_text_model

    try:
        provider = get_text_provider(text_provider_name, api_key=api_key)
    except Exception:
        # If provider fails, return a generic reasoning
        return f"The reader chose to {choice_text.lower()}"

    prompt = f"""Given this story context and reader's choice, infer in 1-2 sentences why the reader might have chosen this option. Focus on narrative intent and character motivation.

Story Theme: {world_theme}
Chapter Context: {chapter_summary}
Reader's Choice: {choice_text}

Reasoning:"""

    messages = [
        {
            "role": "system",
            "content": "You are a narrative analyst. Provide concise, insightful reasoning about story choices.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        result = provider.generate(messages, temperature=0.7, model=text_model)
        reasoning = result.content.strip()
        # Limit to reasonable length
        if len(reasoning) > 200:
            reasoning = reasoning[:197] + "..."
        return reasoning
    except Exception as e:
        logger.warning("Failed to infer choice reasoning: %s", e)
        return f"The reader chose to {choice_text.lower()}"


async def generate_chapter_summary(chapter_content: str, cfg: WorldConfig) -> str:
    """Use LLM to generate a concise summary of chapter events for story continuity.

    Args:
        chapter_content: The full text content of the chapter
        cfg: World configuration for model settings

    Returns:
        A 2-3 sentence summary of key events and developments
    """
    settings = load_user_settings()
    text_provider_name = settings.text_provider
    api_key = get_api_key_for_provider(text_provider_name, settings)
    text_model = settings.default_text_model

    try:
        provider = get_text_provider(text_provider_name, api_key=api_key)
    except Exception:
        # If provider fails, return empty summary
        return ""

    # Extract just the story content (remove HTML/metadata)
    import re

    # Remove HTML metadata comments
    content_clean = re.sub(r"<!--.*?-->", "", chapter_content, flags=re.DOTALL)
    # Remove HTML tags
    content_clean = re.sub(r"<[^>]+>", "", content_clean)
    # Get first ~1000 characters for context
    content_sample = content_clean[:1000]

    prompt = f"""Generate a concise 2-3 sentence summary of this chapter's key events and plot developments for story continuity. Focus on what actually happens and any important changes.

Chapter content:
{content_sample}

Summary:"""

    messages = [
        {
            "role": "system",
            "content": "You are a story editor. Create concise, accurate summaries that capture the essence of what happens in each chapter.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        result = provider.generate(messages, temperature=0.3, model=text_model)
        summary = result.content.strip()
        # Limit to reasonable length
        if len(summary) > 300:
            summary = summary[:297] + "..."
        return summary
    except Exception as e:
        logger.warning("Failed to generate chapter summary: %s", e)
        return ""
