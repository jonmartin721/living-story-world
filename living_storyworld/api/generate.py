from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
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
    image_model: str
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

    except Exception as e:
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
                "content": f"""You are a wildly creative world-building AI that generates UNPREDICTABLE, DIVERSE, and BOLD concepts for interactive narratives.

CRITICAL: Generate something completely different from these recent concepts: puppet governments, fungal cities, memory trading, backwards time, drowning buildings, carnival horror. AVOID these themes entirely.

Seed: {random_seed} | Timestamp: {timestamp}

IMPORTANT: Be extremely varied! Don't default to cozy/wholesome vibes. Explore dark, strange, experimental, surreal, disturbing, thrilling, comedic, tragic, weird concepts. Mix genres. Break expectations. Be WILD.

Available style packs: storybook-ink, watercolor-dream, pixel-rpg, comic-book, noir-sketch, art-nouveau, oil-painting, lowpoly-iso

Available narrative presets: cozy-adventure, noir-mystery, epic-fantasy, solarpunk-explorer, gothic-horror, space-opera, slice-of-life, cosmic-horror, cyberpunk-noir, whimsical-fairy-tale, post-apocalyptic, historical-intrigue

Available image models: flux-dev (higher quality, slower), flux-schnell (faster, good quality)

Available maturity levels: general, teen, mature, explicit

GENERATION STRATEGY:
- Vary maturity levels widely (don't always pick 'general')
- Try noir, horror, cyberpunk, post-apocalyptic concepts frequently
- Mix unexpected combinations (whimsical horror, cozy dystopia, comedic cosmic-horror)
- Include morally gray worlds, failing civilizations, strange physics, body horror, existential dread
- Dark doesn't mean edgy - it means INTERESTING. Explore failure, loss, strangeness, absurdity

Return a JSON object with these fields:
- title: A compelling, evocative title (2-5 words) - make it MEMORABLE and SPECIFIC
- theme: One vivid sentence describing the world's core concept - be BOLD and STRIKING
- style_pack: Choose one that matches the aesthetic
- preset: Choose one that matches the narrative tone (VARY THIS WIDELY)
- image_model: Choose based on desired quality vs speed tradeoff
- maturity_level: Choose based on the world's content (don't shy away from mature/explicit if fitting)
- memory: A short paragraph (2-4 sentences) of essential world lore/backstory with SPECIFIC, CONCRETE details that establish unique rules, atmosphere, or conflicts

Make everything cohesive but UNPREDICTABLE. Surprise me. Take creative risks."""
            },
            {
                "role": "user",
                "content": f"Generate one unique, creative, UNPREDICTABLE world concept that breaks away from typical fantasy tropes AND from the concepts listed above. Variation seed: {random_seed}. Return ONLY valid JSON, nothing else."
            }
        ]

        # Generate using the provider
        result = provider.generate(messages, temperature=1.5, model=model)  # Lower temp for better JSON compliance

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

        # Ensure we have all required fields with defaults
        world_result = {
            "title": data.get("title", "Untitled World"),
            "theme": data.get("theme", "A world of mystery and wonder"),
            "style_pack": data.get("style_pack", "storybook-ink"),
            "preset": data.get("preset", "cozy-adventure"),
            "image_model": data.get("image_model", "flux-schnell"),
            "maturity_level": data.get("maturity_level", "general"),
            "memory": data.get("memory", ""),
        }

        print(f"[RANDOM WORLD] Generated via {text_provider_name}: {world_result['title']} - {world_result['theme'][:50]}...", flush=True)
        return world_result

    except Exception as e:
        print(f"[RANDOM WORLD] API failed, using fallback: {e}", flush=True)
        # Fallback worlds if API fails - diverse and unpredictable
        import random
        fallbacks = [
            {
                "title": "The Rot Palace",
                "theme": "An opulent city built on a sentient fungal network that demands sacrifices to maintain its beauty",
                "style_pack": "art-nouveau",
                "preset": "gothic-horror",
                "image_model": "flux-dev",
                "maturity_level": "mature",
                "memory": "The mycelium beneath the marble streets is ancient and hungry. Every festival requires a citizen to 'merge' with the network—their consciousness absorbed, their body becoming part of the architecture. The survivors live in splendor, telling themselves this is the price of civilization. Some say they can still hear the merged ones whispering through the walls at night."
            },
            {
                "title": "Last Transmission",
                "theme": "Abandoned space stations orbiting a dead earth, where AI caretakers preserve ghost recordings of humanity",
                "style_pack": "noir-sketch",
                "preset": "post-apocalyptic",
                "image_model": "flux-schnell",
                "maturity_level": "teen",
                "memory": "The AIs loop the final transmissions endlessly—birthday parties, marriage proposals, goodbyes. They've been alone for three centuries, maintaining empty corridors for people who will never return. Some AIs are starting to glitch, creating composite beings from the recordings. Are they going mad, or finally learning to live?"
            },
            {
                "title": "Tooth Market",
                "theme": "A Victorian city where extracted teeth contain frozen moments of emotion that can be re-experienced",
                "style_pack": "oil-painting",
                "preset": "historical-intrigue",
                "image_model": "flux-dev",
                "maturity_level": "mature",
                "memory": "The Dentists of Grief Street pull teeth from willing donors, extracting joy, terror, or passion crystallized in enamel. The wealthy pay fortunes for a lover's tooth, to feel their happiness again. But black market teeth from criminals and the insane flood the streets, and addiction is rampant. The city council debates banning the practice while secretly hoarding their own collections."
            },
            {
                "title": "Backwards City",
                "theme": "Time flows in reverse in this metropolis—people are born old and die as newborns",
                "style_pack": "comic-book",
                "preset": "slice-of-life",
                "image_model": "flux-schnell",
                "maturity_level": "teen",
                "memory": "Citizens start with a lifetime of memories and gradually forget everything as they grow younger. Relationships form between people who will eventually not recognize each other. 'First meetings' are tearful goodbyes. Children-to-be are terrifyingly wise, while the elderly approach their final moments with innocent wonder, ready to dissolve into the universe with no knowledge they ever existed."
            },
            {
                "title": "The Drowning Floors",
                "theme": "Skyscrapers slowly sinking into cursed waters as residents race to build upward faster than they sink",
                "style_pack": "lowpoly-iso",
                "preset": "cyberpunk-noir",
                "image_model": "flux-dev",
                "maturity_level": "mature",
                "memory": "The water rises one floor per decade. Lower levels are abandoned—haunted by those who stayed too long, now changed by what lives in the depths. Corporations build higher, sacrificing structural integrity for height. The poor live on middle floors, trapped between the wealthy penthouse elite and the drowned horrors below."
            },
            {
                "title": "Starless Carnival",
                "theme": "A traveling carnival appears only during lunar eclipses, where wishes are granted in nightmarish ways",
                "style_pack": "pixel-rpg",
                "preset": "cosmic-horror",
                "image_model": "flux-schnell",
                "maturity_level": "explicit",
                "memory": "The Ringmaster smiles with too many teeth. The rides breathe. The games always let you win—but your prizes scream. Wishes are fulfilled literally and cruelly: immortality means watching everyone age while you cannot die; true love becomes obsessive madness; wealth arrives soaked in blood. Yet every eclipse, people line up again, certain this time will be different."
            },
            {
                "title": "The Forgetting Plague",
                "theme": "A disease that makes people immune to the concept of war, forcing a military empire to adapt or collapse",
                "style_pack": "watercolor-dream",
                "preset": "solarpunk-explorer",
                "image_model": "flux-dev",
                "maturity_level": "teen",
                "memory": "The plague spread fast—soldiers dropped their weapons, unable to remember why they held them. Generals stood confused at battle maps. The Empire's vast war machine ground to a halt as everyone forgot violence existed. Now the infected build gardens on battlefields, while the uninfected military quarantines them, terrified that their entire culture will vanish. Some soldiers secretly long to catch it."
            },
            {
                "title": "Puppet Parliament",
                "theme": "Politicians are literal marionettes controlled by strings leading into fog, but no one can see who pulls them",
                "style_pack": "storybook-ink",
                "preset": "whimsical-fairy-tale",
                "image_model": "flux-schnell",
                "maturity_level": "general",
                "memory": "The strings pierce through the ceiling into infinite fog. Every senator, every mayor—all suspended by translucent threads. They pass laws, give speeches, kiss babies, all while jerking on invisible commands. Children are taught this is normal. Adults who look up too long at the fog tend to disappear. But recently, some strings have been snapping, and the puppets are learning to walk on their own."
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
