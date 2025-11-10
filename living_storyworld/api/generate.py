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
    chapter_length: str


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
    """Generate a complete random world configuration using OpenAI"""
    try:
        from openai import OpenAI
        import os

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a creative world-building assistant. Generate complete, cohesive world concepts for interactive narratives.

Available style packs: storybook-ink, watercolor-dream, pixel-rpg, comic-book, noir-sketch, art-nouveau, oil-painting, lowpoly-iso

Available narrative presets: cozy-adventure, noir-mystery, epic-fantasy, solarpunk-explorer, gothic-horror, space-opera, slice-of-life, cosmic-horror, cyberpunk-noir, whimsical-fairy-tale, post-apocalyptic, historical-intrigue

Available image models: flux-dev (higher quality, slower), flux-schnell (faster, good quality)

Available maturity levels: general, teen, mature, explicit

Available chapter lengths: short (~500 words), medium (~1000 words), long (~2000 words)

Return a JSON object with these fields:
- title: A compelling, evocative title (2-5 words)
- theme: One vivid sentence describing the world's core concept
- style_pack: Choose one that matches the aesthetic
- preset: Choose one that matches the narrative tone
- image_model: Choose based on desired quality vs speed tradeoff
- maturity_level: Choose based on the world's content
- chapter_length: Choose based on the world's pacing needs

Make everything cohesive - the style, preset, image model, maturity, and chapter length should all match the overall vibe."""
                },
                {
                    "role": "user",
                    "content": "Generate one unique, creative world concept. Return ONLY valid JSON, nothing else."
                }
            ],
            temperature=1.3,
            max_tokens=200,
            response_format={"type": "json_object"}
        )

        data = json.loads(response.choices[0].message.content)

        # Ensure we have all required fields with defaults
        return {
            "title": data.get("title", "Untitled World"),
            "theme": data.get("theme", "A world of mystery and wonder"),
            "style_pack": data.get("style_pack", "storybook-ink"),
            "preset": data.get("preset", "cozy-adventure"),
            "image_model": data.get("image_model", "flux-schnell"),
            "maturity_level": data.get("maturity_level", "general"),
            "chapter_length": data.get("chapter_length", "medium"),
        }

    except Exception as e:
        # Fallback worlds if API fails
        import random
        fallbacks = [
            {
                "title": "Twilight Gardens",
                "theme": "A city of floating gardens suspended in eternal twilight",
                "style_pack": "watercolor-dream",
                "preset": "cozy-adventure",
                "image_model": "flux-dev",
                "maturity_level": "general",
                "chapter_length": "medium"
            },
            {
                "title": "Crystal Archives",
                "theme": "Underground libraries carved from crystalline caverns where knowledge takes physical form",
                "style_pack": "art-nouveau",
                "preset": "noir-mystery",
                "image_model": "flux-schnell",
                "maturity_level": "teen",
                "chapter_length": "short"
            },
            {
                "title": "Memory Market",
                "theme": "A marketplace where memories are traded as currency and identity is fluid",
                "style_pack": "comic-book",
                "preset": "cyberpunk-noir",
                "image_model": "flux-dev",
                "maturity_level": "mature",
                "chapter_length": "long"
            },
            {
                "title": "Singing Forests",
                "theme": "Bioluminescent forests where trees sing at dawn and night creatures speak in riddles",
                "style_pack": "storybook-ink",
                "preset": "whimsical-fairy-tale",
                "image_model": "flux-schnell",
                "maturity_level": "general",
                "chapter_length": "medium"
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
