from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/generate", tags=["generate"])

executor = ThreadPoolExecutor(max_workers=2)


class ThemeResponse(BaseModel):
    theme: str


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


@router.get("/theme", response_model=ThemeResponse)
async def generate_theme():
    """Generate a random theme using AI"""
    loop = asyncio.get_event_loop()
    theme = await loop.run_in_executor(executor, _generate_random_theme)
    return ThemeResponse(theme=theme)
