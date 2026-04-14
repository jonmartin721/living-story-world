from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import STYLE_PACKS
from .models import (
    Chapter,
    Choice,
    GeneratedChapterDraft,
    ResolvedGenerationSettings,
    WorldConfig,
    WorldState,
)
from .presets import DEFAULT_PRESET, PRESETS
from .providers import get_text_provider
from .settings import get_api_key_for_provider, load_user_settings

logger = logging.getLogger(__name__)


def _build_chapter_prompt(
    cfg: WorldConfig, state: WorldState, chapter_length: str = "medium"
) -> Tuple[str, list[dict], float]:
    style = STYLE_PACKS.get(cfg.style_pack, STYLE_PACKS["storybook-ink"])
    preset = PRESETS.get(cfg.preset, DEFAULT_PRESET)

    settings = load_user_settings()
    global_instructions = settings.global_instructions or ""

    maturity_guidance = {
        "general": "Write family-friendly content suitable for all ages. Keep themes light and appropriate.",
        "teen": "Write young adult fiction. Include tension, conflict, and emotional depth appropriate for teen readers.",
        "mature": "Write adult fiction with mature themes and realistic situations. Use authentic language and explore complex emotional landscapes.",
        "explicit": "Write unrestricted adult fiction with full creative freedom. Portray mature themes authentically and unflinchingly as serves the story.",
    }
    maturity_instruction = maturity_guidance.get(
        cfg.maturity_level, maturity_guidance["general"]
    )

    metadata_keys = (
        "scene_prompt (string describing a wide scene illustration), "
        "image_prompt (concise 1-2 sentence visual description for image generation, max 150 chars, focus on key visual elements only), "
        "characters_in_scene (string array), "
        "summary (string), new_characters (array of {id, name, description}), new_locations (array of {id, name, description})"
    )

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

    if global_instructions:
        sys_parts.append(f"\n\nGlobal Instructions: {global_instructions}")

    if cfg.world_instructions:
        sys_parts.append(f"\n\nWorld Instructions: {cfg.world_instructions}")

    sys = "".join(sys_parts)

    story_context = []
    if state.chapters:
        recent_chapters = (
            state.chapters[-4:] if len(state.chapters) >= 4 else state.chapters
        )

        for ch in recent_chapters:
            chapter_info = [f"Chapter {ch.number}: {ch.title}"]

            if ch.ai_summary:
                chapter_info.append(ch.ai_summary)
            elif ch.summary:
                chapter_info.append(ch.summary)

            if ch.selected_choice_id and ch.choices:
                selected_choice = next(
                    (c for c in ch.choices if c.id == ch.selected_choice_id), None
                )
                if selected_choice:
                    chapter_info.append(f"Choice: {selected_choice.text}")

            story_context.append("\n".join(chapter_info))

        if len(state.chapters) > 4:
            older_summary = []
            for ch in state.chapters[-8:-4]:
                if ch.ai_summary or ch.summary:
                    older_summary.append(f"Ch {ch.number} ({ch.title})")
            if older_summary:
                story_context.insert(
                    0, "Earlier progression: " + " -> ".join(older_summary)
                )

    world_brief = {
        "title": cfg.title,
        "theme": cfg.theme,
        "tick": state.tick,
        "chapter_number": state.next_chapter,
        "known_characters": list(state.characters.keys()),
        "known_locations": list(state.locations.keys()),
    }

    user_parts = []

    if cfg.memory:
        user_parts.append(f"Memory/Lore:\n{cfg.memory}\n\n")

    user_parts.append("World brief: " + json.dumps(world_brief) + "\n\n")

    if story_context:
        user_parts.append("Story progression:\n" + "\n\n".join(story_context) + "\n\n")

    if cfg.authors_note:
        user_parts.append(f"Author's Note: {cfg.authors_note}\n\n")

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

    import random

    length_config = {
        "short": (400, 600),
        "medium": (800, 1200),
        "long": (1600, 2400),
    }
    min_words, max_words = length_config.get(chapter_length, length_config["medium"])
    variation = random.uniform(0.9, 1.1)
    min_words = int(min_words * variation)
    max_words = int(max_words * variation)

    metadata_format = '<!-- {"scene_prompt": string, "image_prompt": string, "characters_in_scene": [string], "summary": string, '
    metadata_format += '"new_characters": [{id, name, description}], "new_locations": [{id, name, description}]'
    if cfg.enable_choices:
        metadata_format += (
            ', "choices": [{"id": string, "text": string, "description": string}], '
        )
        metadata_format += '"story_health": {"is_repetitive": bool, "natural_ending_reached": bool, "needs_fresh_direction": bool, "notes": string}'
    metadata_format += "} -->\n"

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
            f"Start with a unique chapter title as H1 (do NOT include 'Chapter {state.next_chapter}' in the title - just the evocative name). ",
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
    match = re.search(r"<!--\s*(\{.*?\})\s*-->", md_text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except Exception:
        return {}


def resolve_generation_settings(
    cfg: WorldConfig, settings=None
) -> ResolvedGenerationSettings:
    from .settings import get_available_text_providers

    user_settings = settings or load_user_settings()
    text_provider_order = get_available_text_providers(user_settings)
    preferred_text_model = (
        cfg.text_model
        or getattr(user_settings, "default_text_model", None)
    )
    preferred_image_model = (
        cfg.image_model
        or getattr(user_settings, "default_image_model", None)
    )

    return ResolvedGenerationSettings(
        text_provider=user_settings.text_provider,
        image_provider=user_settings.image_provider,
        text_provider_order=text_provider_order,
        preferred_text_model=preferred_text_model,
        preferred_image_model=preferred_image_model,
    )


def _resolve_text_model(
    provider,
    cfg: WorldConfig,
    settings,
    resolved_settings: ResolvedGenerationSettings,
) -> str:
    return (
        resolved_settings.preferred_text_model
        or cfg.text_model
        or getattr(settings, "default_text_model", None)
        or provider.get_default_model()
    )


def resolve_image_model(
    cfg: WorldConfig, settings=None, provider_name: Optional[str] = None
) -> str:
    user_settings = settings or load_user_settings()
    image_provider_name = provider_name or user_settings.image_provider
    provider = None
    try:
        from .providers import get_image_provider

        provider = get_image_provider(
            image_provider_name,
            api_key=get_api_key_for_provider(image_provider_name, user_settings),
        )
    except Exception:
        provider = None
    return (
        cfg.image_model
        or getattr(user_settings, "default_image_model", None)
        or (provider.get_default_model() if provider else None)
        or "flux"
    )


def _generate_text_with_fallback(
    messages: list[dict[str, str]],
    cfg: WorldConfig,
    temperature: float,
    *,
    settings=None,
    resolved_settings: Optional[ResolvedGenerationSettings] = None,
) -> tuple[str, str, str]:
    user_settings = settings or load_user_settings()
    resolved = resolved_settings or resolve_generation_settings(cfg, user_settings)

    if not resolved.text_provider_order:
        raise ValueError(
            "No text providers configured. Please add API keys in Settings."
        )

    last_error: Optional[Exception] = None
    for provider_name in resolved.text_provider_order:
        try:
            api_key = get_api_key_for_provider(provider_name, user_settings)
            provider = get_text_provider(provider_name, api_key=api_key)
            model = _resolve_text_model(provider, cfg, user_settings, resolved)
            result = provider.generate(messages, temperature=temperature, model=model)
            logger.info(
                "Generated text using %s (%s), cost: $%.4f",
                result.provider,
                result.model,
                result.estimated_cost,
            )
            return result.content, result.provider, result.model
        except Exception as exc:
            last_error = exc
            error_msg = str(exc)
            is_safety_block = (
                "safety filter" in error_msg.lower() or "blocked" in error_msg.lower()
            )
            if len(resolved.text_provider_order) == 1:
                if is_safety_block:
                    raise ValueError(
                        f"Content blocked by {provider_name}'s safety filters. Try regenerating or configure additional text providers in Settings for automatic fallback."
                    ) from exc
                raise
            logger.warning("%s failed: %s", provider_name, error_msg)

    providers_tried = ", ".join(resolved.text_provider_order)
    raise ValueError(
        f"All text providers failed ({providers_tried}). Last error: {last_error}. Configure additional providers in Settings for better reliability."
    )


def generate_chapter_draft(
    cfg: WorldConfig,
    state: WorldState,
    chapter_length: str = "medium",
    *,
    settings=None,
    resolved_settings: Optional[ResolvedGenerationSettings] = None,
) -> GeneratedChapterDraft:
    user_settings = settings or load_user_settings()
    resolved = resolved_settings or resolve_generation_settings(cfg, user_settings)
    _, messages, temperature = _build_chapter_prompt(cfg, state, chapter_length)
    markdown, provider_name, model_name = _generate_text_with_fallback(
        messages,
        cfg,
        temperature,
        settings=user_settings,
        resolved_settings=resolved,
    )

    meta = _parse_meta(markdown)
    characters_in_scene = meta.get("characters_in_scene", []) if meta else []
    if not isinstance(characters_in_scene, list):
        characters_in_scene = []

    choices = []
    for choice_data in meta.get("choices", []) if isinstance(meta, dict) else []:
        if (
            isinstance(choice_data, dict)
            and "id" in choice_data
            and "text" in choice_data
        ):
            choices.append(Choice.from_dict(choice_data))

    return GeneratedChapterDraft(
        markdown=markdown,
        title=_extract_title(markdown) or f"Chapter {state.next_chapter}",
        summary=str(meta.get("summary", "")) or None if isinstance(meta, dict) else None,
        scene_prompt=str(meta.get("scene_prompt", "")) or None
        if isinstance(meta, dict)
        else None,
        image_prompt=str(meta.get("image_prompt", "")) or None
        if isinstance(meta, dict)
        else None,
        characters_in_scene=[str(character) for character in characters_in_scene],
        choices=choices,
        text_model_used=model_name,
        text_provider_used=provider_name,
        new_characters=meta.get("new_characters", []) if isinstance(meta, dict) else [],
        new_locations=meta.get("new_locations", []) if isinstance(meta, dict) else [],
        metadata=meta if isinstance(meta, dict) else {},
    )


def _extract_title(md: str) -> Optional[str]:
    for line in md.splitlines():
        if line.strip().startswith("# "):
            title = line.strip("# ").strip()
            return re.sub(
                r"^Chapter\s+\d+\s*[:\-]\s*", "", title, flags=re.IGNORECASE
            )
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
    from .models import Character, Location

    if isinstance(new_characters, list):
        for char_data in new_characters:
            if (
                isinstance(char_data, dict)
                and "id" in char_data
                and "name" in char_data
            ):
                char_id = str(char_data["id"])
                if char_id not in state.characters:
                    state.characters[char_id] = Character(
                        id=char_id,
                        name=str(char_data.get("name", char_id)),
                        description=str(char_data.get("description", "")) or None,
                        epithet=str(char_data.get("epithet", "")) or None,
                        traits=list(char_data.get("traits", [])),
                    )

    if isinstance(new_locations, list):
        for loc_data in new_locations:
            if isinstance(loc_data, dict) and "id" in loc_data and "name" in loc_data:
                loc_id = str(loc_data["id"])
                if loc_id not in state.locations:
                    state.locations[loc_id] = Location(
                        id=loc_id,
                        name=str(loc_data.get("name", loc_id)),
                        description=str(loc_data.get("description", "")) or None,
                        tags=list(loc_data.get("tags", [])),
                    )


def persist_generated_chapter(
    base_dir: Path,
    cfg: WorldConfig,
    state: WorldState,
    draft: GeneratedChapterDraft,
    chapter_number: int,
    *,
    filename: Optional[str] = None,
    chapter_index: Optional[int] = None,
    write_scene_request: bool = True,
) -> Chapter:
    _register_new_entities(state, draft.new_characters, draft.new_locations)

    chapter_filename = filename or f"chapter-{chapter_number:04d}.md"
    chapter_path = base_dir / "chapters" / chapter_filename
    chapter_path.parent.mkdir(parents=True, exist_ok=True)
    chapter_path.write_text(draft.markdown, encoding="utf-8")

    chapter = Chapter(
        number=chapter_number,
        title=draft.title,
        filename=chapter_filename,
        summary=draft.summary,
        scene_prompt=draft.scene_prompt,
        image_prompt=draft.image_prompt,
        characters_in_scene=list(draft.characters_in_scene),
        choices=list(draft.choices),
        text_model_used=draft.text_model_used,
    )

    if write_scene_request and (draft.image_prompt or draft.scene_prompt):
        _write_scene_request(
            base_dir,
            chapter_number,
            cfg.style_pack,
            draft.image_prompt or draft.scene_prompt or "",
        )

    if chapter_index is None:
        state.chapters.append(chapter)
        state.next_chapter = max(state.next_chapter, chapter_number + 1)
    else:
        state.chapters[chapter_index] = chapter

    return chapter


def generate_chapter(
    base_dir: Path,
    cfg: WorldConfig,
    state: WorldState,
    make_scene_image: bool = True,
    chapter_length: str = "medium",
) -> Chapter:
    draft = generate_chapter_draft(cfg, state, chapter_length=chapter_length)
    return persist_generated_chapter(
        base_dir,
        cfg,
        state,
        draft,
        state.next_chapter,
        write_scene_request=make_scene_image,
    )


def find_latest_scene_path(base_dir: Path, slug: str, chapter_number: int) -> Optional[str]:
    scenes_dir = base_dir / "media" / "scenes"
    if not scenes_dir.exists():
        return None
    pattern = f"scene-{chapter_number:04d}-*.png"
    scene_files = sorted(
        scenes_dir.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True
    )
    if not scene_files:
        return None
    return f"/worlds/{slug}/media/scenes/{scene_files[0].name}"


def serialize_chapter_response(
    slug: str,
    chapter: Chapter,
    *,
    scene: Optional[str] = None,
) -> dict:
    return {
        "number": chapter.number,
        "title": chapter.title,
        "filename": chapter.filename,
        "summary": chapter.summary,
        "scene_prompt": chapter.scene_prompt,
        "image_prompt": chapter.image_prompt,
        "characters_in_scene": list(chapter.characters_in_scene),
        "choices": [choice.to_dict() for choice in chapter.choices],
        "selected_choice_id": chapter.selected_choice_id,
        "choice_reasoning": chapter.choice_reasoning,
        "generated_at": chapter.generated_at,
        "text_model_used": chapter.text_model_used,
        "image_model_used": chapter.image_model_used,
        "scene": scene,
        "ai_summary": chapter.ai_summary,
    }


async def infer_choice_reasoning(
    choice_text: str, chapter_summary: str, world_theme: str, cfg: WorldConfig
) -> str:
    settings = load_user_settings()
    resolved_settings = resolve_generation_settings(cfg, settings)
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
        reasoning, _, _ = _generate_text_with_fallback(
            messages,
            cfg,
            0.7,
            settings=settings,
            resolved_settings=resolved_settings,
        )
        reasoning = reasoning.strip()
        if len(reasoning) > 200:
            reasoning = reasoning[:197] + "..."
        return reasoning
    except Exception as exc:
        logger.warning("Failed to infer choice reasoning: %s", exc)
        return f"The reader chose to {choice_text.lower()}"


async def generate_chapter_summary(chapter_content: str, cfg: WorldConfig) -> str:
    settings = load_user_settings()
    resolved_settings = resolve_generation_settings(cfg, settings)

    content_clean = re.sub(r"<!--.*?-->", "", chapter_content, flags=re.DOTALL)
    content_clean = re.sub(r"<[^>]+>", "", content_clean)
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
        summary, _, _ = _generate_text_with_fallback(
            messages,
            cfg,
            0.3,
            settings=settings,
            resolved_settings=resolved_settings,
        )
        summary = summary.strip()
        if len(summary) > 300:
            summary = summary[:297] + "..."
        return summary
    except Exception as exc:
        logger.warning("Failed to generate chapter summary: %s", exc)
        return ""
