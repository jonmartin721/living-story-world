from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from pathlib import Path

from ..storage import WORLDS_DIR, get_current_world, set_current_world
from ..world import init_world, load_world
from .dependencies import get_validated_world_slug

router = APIRouter(prefix="/api/worlds", tags=["worlds"])


class WorldCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="World title")
    theme: str = Field(..., min_length=1, max_length=1000, description="World theme/description")
    style_pack: str = Field(default="storybook-ink", max_length=100)
    maturity_level: str = Field(default="general", max_length=20)
    preset: str = Field(default="cozy-adventure", max_length=50)
    enable_choices: bool = Field(default=False)
    slug: Optional[str] = Field(None, max_length=100)
    memory: Optional[str] = Field(None, max_length=10000, description="Persistent world memory")
    authors_note: Optional[str] = Field(None, max_length=5000, description="Author's notes/instructions")
    world_instructions: Optional[str] = Field(None, max_length=5000, description="World-specific instructions")

    @validator('title', 'theme', 'memory', 'authors_note', 'world_instructions')
    def strip_whitespace(cls, v):  # pylint: disable=no-self-argument
        return v.strip() if v else v


class WorldUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    theme: Optional[str] = Field(None, min_length=1, max_length=1000)
    style_pack: Optional[str] = Field(None, max_length=100)
    maturity_level: Optional[str] = Field(None, max_length=20)
    preset: Optional[str] = Field(None, max_length=50)
    enable_choices: Optional[bool] = Field(None)
    memory: Optional[str] = Field(None, max_length=10000)
    authors_note: Optional[str] = Field(None, max_length=5000)
    world_instructions: Optional[str] = Field(None, max_length=5000)

    @validator('title', 'theme', 'memory', 'authors_note', 'world_instructions')
    def strip_whitespace(cls, v):  # pylint: disable=no-self-argument
        return v.strip() if v else v


class WorldResponse(BaseModel):
    title: str
    slug: str
    theme: str
    style_pack: str
    text_model: str
    maturity_level: str
    preset: str
    enable_choices: bool
    tick: int
    chapter_count: int
    is_current: bool
    memory: Optional[str] = None
    authors_note: Optional[str] = None
    world_instructions: Optional[str] = None


@router.get("", response_model=List[WorldResponse])
async def list_worlds():
    """List all available worlds"""
    worlds = []
    current = get_current_world()

    for world_dir in WORLDS_DIR.glob("*/"):
        if world_dir.is_dir():
            try:
                cfg, state, _ = load_world(world_dir.name)
                worlds.append(WorldResponse(
                    title=cfg.title,
                    slug=cfg.slug,
                    theme=cfg.theme,
                    style_pack=cfg.style_pack,
                    text_model=cfg.text_model,
                    maturity_level=getattr(cfg, 'maturity_level', 'general'),
                    preset=getattr(cfg, 'preset', 'cozy-adventure'),
                    enable_choices=getattr(cfg, 'enable_choices', False),
                    tick=state.tick,
                    chapter_count=len(state.chapters),
                    is_current=(cfg.slug == current),
                    memory=getattr(cfg, 'memory', None),
                    authors_note=getattr(cfg, 'authors_note', None),
                    world_instructions=getattr(cfg, 'world_instructions', None)
                ))
            except Exception:
                # Skip invalid worlds
                pass

    return worlds


@router.post("", response_model=WorldResponse)
async def create_world(request: WorldCreateRequest):
    """Create a new world"""
    import os
    import shutil

    existing_worlds = len(list(WORLDS_DIR.glob("*/"))) if WORLDS_DIR.exists() else 0
    max_worlds = int(os.environ.get("MAX_WORLDS_PER_INSTANCE", "100"))

    if existing_worlds >= max_worlds:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum number of worlds ({max_worlds}) reached. Delete some worlds before creating new ones."
        )

    try:
        stat = shutil.disk_usage(WORLDS_DIR.parent if WORLDS_DIR.exists() else Path.home())
        min_free_mb = 100
        free_mb = stat.free / (1024 * 1024)
        if free_mb < min_free_mb:
            raise HTTPException(
                status_code=507,
                detail=f"Insufficient disk space ({free_mb:.0f}MB free, need {min_free_mb}MB minimum)"
            )
    except Exception as e:
        # Log but don't block on disk check failure
        import logging
        logging.warning(f"Failed to check disk space: {e}")

    slug = init_world(
        title=request.title,
        theme=request.theme,
        style_pack=request.style_pack,
        slug=request.slug,
        maturity_level=request.maturity_level,
        preset=request.preset,
        enable_choices=request.enable_choices,
        memory=request.memory,
        authors_note=request.authors_note,
        world_instructions=request.world_instructions
    )

    cfg, state, _ = load_world(slug)
    return WorldResponse(
        title=cfg.title,
        slug=cfg.slug,
        theme=cfg.theme,
        style_pack=cfg.style_pack,
        text_model=cfg.text_model,
        maturity_level=cfg.maturity_level,
        preset=cfg.preset,
        enable_choices=cfg.enable_choices,
        tick=state.tick,
        chapter_count=len(state.chapters),
        is_current=True,
        memory=cfg.memory,
        authors_note=cfg.authors_note,
        world_instructions=cfg.world_instructions
    )


@router.get("/{slug}", response_model=dict)
async def get_world(world_info: tuple[str, Path] = Depends(get_validated_world_slug)):
    """Get detailed world information including chapters"""
    slug, world_path = world_info
    cfg, state, dirs = load_world(slug)

    # Load media index for scene images
    from ..storage import read_json
    media_idx = read_json(dirs["base"] / "media" / "index.json", [])
    scene_for_chapter = {}
    for m in media_idx:
        if m.get("type") == "scene" and m.get("chapter"):
            scene_for_chapter[m["chapter"]] = f"/worlds/{slug}/" + m["file"]

    chapters = []
    for ch in state.chapters:
        # Convert Choice dataclass objects to dicts
        choices_data = []
        for choice in ch.choices:
            choices_data.append({
                "id": choice.id,
                "text": choice.text,
                "description": choice.description
            })

        chapters.append({
            "number": ch.number,
            "title": ch.title,
            "filename": ch.filename,
            "summary": ch.summary,
            "scene": scene_for_chapter.get(ch.number),
            "characters_in_scene": ch.characters_in_scene,
            "choices": choices_data,
            "selected_choice_id": ch.selected_choice_id,
            "generated_at": getattr(ch, 'generated_at', None),
            "text_model_used": getattr(ch, 'text_model_used', None),
            "image_model_used": getattr(ch, 'image_model_used', None)
        })

    return {
        "config": {
            "title": cfg.title,
            "slug": cfg.slug,
            "theme": cfg.theme,
            "style_pack": cfg.style_pack,
            "text_model": cfg.text_model,
            "maturity_level": getattr(cfg, 'maturity_level', 'general'),
            "preset": getattr(cfg, 'preset', 'cozy-adventure'),
            "enable_choices": getattr(cfg, 'enable_choices', False),
            "memory": getattr(cfg, 'memory', None),
            "authors_note": getattr(cfg, 'authors_note', None),
            "world_instructions": getattr(cfg, 'world_instructions', None)
        },
        "state": {
            "tick": state.tick,
            "next_chapter": state.next_chapter,
            "characters": state.characters,
            "locations": state.locations
        },
        "chapters": chapters,
        "is_current": slug == get_current_world()
    }


@router.put("/{slug}/current")
async def set_current(world_info: tuple[str, Path] = Depends(get_validated_world_slug)):
    """Set the current world"""
    slug, world_path = world_info
    set_current_world(slug)
    return {"message": f"Current world set to {slug}"}


@router.put("/{slug}")
async def update_world(request: WorldUpdateRequest, world_info: tuple[str, Path] = Depends(get_validated_world_slug)):
    """Update world configuration"""
    slug, world_path = world_info

    from ..world import save_world
    cfg, state, dirs = load_world(slug)

    # Update fields if provided
    if request.title is not None:
        cfg.title = request.title
    if request.theme is not None:
        cfg.theme = request.theme
    if request.style_pack is not None:
        cfg.style_pack = request.style_pack
    if request.maturity_level is not None:
        cfg.maturity_level = request.maturity_level
    if request.preset is not None:
        cfg.preset = request.preset
    if request.enable_choices is not None:
        cfg.enable_choices = request.enable_choices
    if request.memory is not None:
        cfg.memory = request.memory
    if request.authors_note is not None:
        cfg.authors_note = request.authors_note
    if request.world_instructions is not None:
        cfg.world_instructions = request.world_instructions

    save_world(slug, cfg, state, dirs)

    return {
        "message": "World updated",
        "config": {
            "title": cfg.title,
            "slug": cfg.slug,
            "theme": cfg.theme,
            "style_pack": cfg.style_pack,
            "maturity_level": getattr(cfg, 'maturity_level', 'general'),
            "preset": getattr(cfg, 'preset', 'cozy-adventure'),
            "enable_choices": getattr(cfg, 'enable_choices', False),
            "memory": cfg.memory,
            "authors_note": cfg.authors_note,
            "world_instructions": cfg.world_instructions
        }
    }


@router.delete("/{slug}")
async def delete_world(world_info: tuple[str, Path] = Depends(get_validated_world_slug)):
    """Delete a world"""
    slug, world_path = world_info

    import shutil
    shutil.rmtree(world_path)

    # If this was the current world, unset it
    if get_current_world() == slug:
        from ..storage import CURRENT_FILE
        if CURRENT_FILE.exists():
            CURRENT_FILE.unlink()

    return {"message": f"World {slug} deleted"}
