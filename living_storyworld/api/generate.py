from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/generate", tags=["generate"])

executor = ThreadPoolExecutor(max_workers=2)


class ThemeResponse(BaseModel):
    theme: str


class WorldResponse(BaseModel):
    title: str
    theme: str
    style_pack: str
    preset: str
    maturity_level: str
    memory: str


def _generate_random_theme() -> str:
    """Generate a random theme using OpenAI"""
    try:
        from openai import OpenAI
        import os

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a creative writing assistant. Generate unique, evocative themes for narrative storyworlds. Be creative, poetic, and specific. Each theme should be one concise sentence describing an interesting setting or concept."
                },
                {
                    "role": "user",
                    "content": "Generate one unique and creative theme for a storyworld. Make it vivid and specific. Just the theme, no explanation."
                }
            ],
            temperature=1.2,
            max_tokens=50
        )

        theme = response.choices[0].message.content.strip()
        # Remove quotes if present
        theme = theme.strip('"').strip("'")
        return theme

    except Exception:
        # Fallback themes if API fails
        import random
        fallbacks = [
            "A city of floating gardens suspended in eternal twilight",
            "Underground libraries carved from crystalline caverns",
            "A marketplace where memories are traded as currency",
            "Steam-powered archipelago of migrating islands",
            "Bioluminescent forests where trees sing at dawn",
        ]
        return random.choice(fallbacks)


def _generate_random_world() -> dict:
    """Generate a complete random world configuration using configured text provider"""
    try:
        import random
        import time
        from ..settings import load_user_settings, get_api_key_for_provider
        from ..providers import get_text_provider

        # Pre-select preset and style pack for guaranteed variety
        presets = [
            "cozy-adventure", "noir-mystery", "epic-fantasy", "solarpunk-explorer",
            "gothic-horror", "space-opera", "slice-of-life", "cosmic-horror",
            "cyberpunk-noir", "whimsical-fairy-tale", "post-apocalyptic", "historical-intrigue"
        ]
        style_packs = [
            "storybook-ink", "watercolor-dream", "pixel-rpg", "comic-book",
            "noir-sketch", "art-nouveau", "oil-painting", "lowpoly-iso"
        ]
        maturity_levels = ["general", "teen", "mature", "explicit"]

        # Randomly select preset, style, and maturity level
        selected_preset = random.choice(presets)
        selected_style = random.choice(style_packs)
        # Weighted random for maturity - favor general/teen
        selected_maturity = random.choices(
            maturity_levels,
            weights=[50, 35, 12, 3],  # Heavily favor general/teen
            k=1
        )[0]

        # Add entropy to the prompt to force variation
        random_seed = random.randint(1000, 9999)
        timestamp = int(time.time())

        # Use the configured text provider, fallback to OpenAI if no key
        settings = load_user_settings()
        text_provider_name = settings.text_provider
        api_key = get_api_key_for_provider(text_provider_name, settings)

        # If no API key for configured provider, fallback to OpenAI
        if not api_key:
            print(f"[RANDOM WORLD] No API key for {text_provider_name}, falling back to OpenAI", flush=True)
            text_provider_name = "openai"
            api_key = get_api_key_for_provider("openai", settings)
            model = "gpt-4o-mini"
        else:
            model = settings.default_text_model

        if not api_key:
            raise ValueError("No API key available for text generation")

        provider = get_text_provider(text_provider_name, api_key=api_key)

        messages = [
            {
                "role": "system",
                "content": f"""You are a creative world-building AI that generates diverse, engaging story world concepts.

Seed: {random_seed} | Timestamp: {timestamp}

The user has requested a world with these characteristics:
- Narrative preset: {selected_preset}
- Visual style: {selected_style}
- Maturity level: {selected_maturity}

GENERATION STRATEGY - Follow this distribution:
- 50% of concepts should be FAMILIAR and approachable (cozy fantasy villages, mystery academies, adventure guilds, space exploration, magical schools, merchant cities)
- 30% should be INTERESTING with a unique twist (fantasy with unusual magic system, sci-fi with interesting tech, historical with supernatural elements)
- 15% can be UNUSUAL or experimental (strange physics, surreal elements, genre mashups)
- 5% can be truly OUTLANDISH or bizarre

Most worlds should feel like something readers would recognize or enjoy reading. Think popular novels, games, and shows.

Return a JSON object with these fields:
- title: A compelling title (2-5 words) that matches the {selected_preset} tone and is inviting and clear
- theme: One sentence describing the world's core concept - be specific and vivid, matching the {selected_preset} style
- memory: A short paragraph (2-4 sentences) of essential world lore/backstory with specific details that establish the setting, atmosphere, and key elements suitable for {selected_maturity} audiences

Make everything cohesive with the selected preset and engaging. Most concepts should feel like something people would want to read."""
            },
            {
                "role": "user",
                "content": f"Generate one engaging story world concept for the {selected_preset} genre. Variation seed: {random_seed}. Return ONLY valid JSON with title, theme, and memory fields. Nothing else."
            }
        ]

        # Generate using the provider
        result = provider.generate(messages, temperature=0.9, model=model)

        # Extract JSON from response (might be wrapped in markdown code blocks)
        content = result.content.strip()
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
        if content.startswith('```'):
            content = content[3:]  # Remove ```
        if content.endswith('```'):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()

        data = json.loads(content)

        # Build result using pre-selected values for preset, style, and maturity
        world_result = {
            "title": data.get("title", "Untitled World"),
            "theme": data.get("theme", "A world of mystery and wonder"),
            "style_pack": selected_style,
            "preset": selected_preset,
            "maturity_level": selected_maturity,
            "memory": data.get("memory", ""),
        }

        print(f"[RANDOM WORLD] Generated via {text_provider_name} [{selected_preset}/{selected_style}]: {world_result['title']} - {world_result['theme'][:50]}...", flush=True)
        return world_result

    except Exception as e:
        print(f"[RANDOM WORLD] API failed, using fallback: {e}", flush=True)
        # Fallback worlds with balanced distribution
        import random
        fallbacks = [
            # Familiar concepts (50%)
            {
                "title": "Silverport Trading Company",
                "theme": "A bustling harbor city where merchant guilds compete for trade routes to distant magical lands",
                "style_pack": "watercolor-dream",
                "preset": "cozy-adventure",
                "maturity_level": "general",
                "memory": "Silverport sits at the crossroads of three continents, where exotic spices, enchanted goods, and rare artifacts change hands daily. The five great trading companies maintain a delicate balance of power, each with their own fleet, secrets, and ambitions. Young merchants apprentice under guild masters, learning not just commerce but navigation, diplomacy, and the art of spotting a cursed trinket from a genuine treasure."
            },
            {
                "title": "Academy of Stars",
                "theme": "A prestigious magical university where students master elemental magic and uncover ancient mysteries",
                "style_pack": "storybook-ink",
                "preset": "epic-fantasy",
                "maturity_level": "general",
                "memory": "The Academy stands on a floating island, its towers reaching toward the sky. Students are sorted into four houses based on their primary element: Fire, Water, Earth, or Air. The Grand Library holds thousands of spellbooks, some helpful, some dangerous, and a few that are strictly forbidden. This year, strange magical disturbances suggest something ancient is awakening beneath the school."
            },
            {
                "title": "The Wandering Inn",
                "theme": "A magical inn that appears in different locations each night, serving travelers from across dimensions",
                "style_pack": "pixel-rpg",
                "preset": "slice-of-life",
                "maturity_level": "general",
                "memory": "The Crossroads Inn never stays in one place. Each sunrise it materializes somewhere new—a snowy mountain pass, a desert oasis, a bustling city square. The innkeeper welcomes all travelers, whether they're adventurers, merchants, or refugees from collapsing worlds. Regular patrons have learned to follow the signs: a blue lantern, a crow's call, the smell of fresh bread. Inside, the food is always warm, the beds always comfortable, and strangers become friends over shared tales."
            },
            {
                "title": "Starship Horizon",
                "theme": "A generation ship's crew explores uncharted systems while maintaining their mobile home for thousands of colonists",
                "style_pack": "lowpoly-iso",
                "preset": "space-opera",
                "maturity_level": "teen",
                "memory": "The Horizon has been traveling for three generations, its 5,000 inhabitants living in rotating habitats while seeking a new Earth. The ship's crew discovers strange phenomena: abandoned alien stations, resource-rich asteroids, and signals that might be first contact. As resources dwindle and factions form, the captain must balance exploration with survival, all while the ship's AI begins displaying unexpected behaviors."
            },

            # Interesting with a twist (30%)
            {
                "title": "The Library of Lost Voices",
                "theme": "A vast library where forgotten stories manifest as living characters seeking someone to remember them",
                "style_pack": "art-nouveau",
                "preset": "whimsical-fairy-tale",
                "maturity_level": "general",
                "memory": "When a story is completely forgotten by the world, it appears in the Library—characters, settings, and all. The Archivists maintain this impossible place, helping faded heroes and villains find new readers before they dissolve entirely. But something is wrong: stories are vanishing faster than ever, and some characters are rewriting themselves, desperate to be remembered at any cost."
            },
            {
                "title": "Resonance City",
                "theme": "A city where music is magic, and sound-shapers protect citizens from the silence that consumes reality",
                "style_pack": "comic-book",
                "preset": "solarpunk-explorer",
                "maturity_level": "teen",
                "memory": "Resonance was built on a frequency anomaly where sound waves can reshape matter. Musicians aren't just artists—they're engineers, healers, and warriors. The city hums with constant melody, from the bass rumble of the foundry-orchestras to the delicate chimes of the healing wards. But beyond the city walls lies the Dead Zone, where all sound is swallowed by an expanding silence that erases whatever it touches."
            },

            # Unusual (15%)
            {
                "title": "The Gardeners",
                "theme": "Reality is a garden tended by mysterious beings, and you've just been recruited as an apprentice gardener",
                "style_pack": "watercolor-dream",
                "preset": "cosmic-horror",
                "maturity_level": "teen",
                "memory": "The Gardeners move between worlds like farmers tending crops, pruning timelines, planting possibilities, and harvesting destinies. They exist outside causality, appearing as whatever form brings comfort. As an apprentice, you're learning to see reality as they do: a living, growing thing that needs care. But some Gardens are diseased, some have gone wild, and some are being invaded by something the Gardeners won't name."
            },

            # Outlandish (5%)
            {
                "title": "The Dreaming City",
                "theme": "A metropolis that exists only while people dream, built from collective unconscious and fading with each awakening",
                "style_pack": "oil-painting",
                "preset": "noir-mystery",
                "maturity_level": "mature",
                "memory": "Every night, millions of dreamers contribute to the City's existence—a skyscraper from Tokyo, a cafe from Paris, a park from memories of childhood. The permanent residents are those who've learned to never fully wake, navigating the shifting architecture and investigating crimes that blur the line between dream and reality. But recently, nightmares have been taking physical form, and some dreamers aren't waking up at all."
            },
        ]
        return random.choice(fallbacks)


@router.get("/theme", response_model=ThemeResponse)
async def generate_theme():
    """Generate a random theme using AI (legacy endpoint)"""
    loop = asyncio.get_event_loop()
    theme = await loop.run_in_executor(executor, _generate_random_theme)
    return ThemeResponse(theme=theme)


@router.get("/world", response_model=WorldResponse)
async def generate_world():
    """Generate a complete random world configuration using AI"""
    loop = asyncio.get_event_loop()
    world_data = await loop.run_in_executor(executor, _generate_random_world)
    return WorldResponse(**world_data)
