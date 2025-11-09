from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ..storage import WORLDS_DIR, get_current_world, set_current_world
from ..world import init_world, load_world
from ..models import WorldConfig, WorldState

router = APIRouter(prefix="/api/worlds", tags=["worlds"])


class WorldCreateRequest(BaseModel):
    title: str
    theme: str
    style_pack: str = "storybook-ink"
    image_model: str = "flux-dev"
    slug: Optional[str] = None


class WorldUpdateRequest(BaseModel):
    title: Optional[str] = None
    theme: Optional[str] = None
    style_pack: Optional[str] = None
    image_model: Optional[str] = None


class WorldResponse(BaseModel):
    title: str
    slug: str
    theme: str
    style_pack: str
    text_model: str
    image_model: str
    tick: int
    chapter_count: int
    is_current: bool


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
                    image_model=cfg.image_model,
                    tick=state.tick,
                    chapter_count=len(state.chapters),
                    is_current=(cfg.slug == current)
                ))
            except Exception:
                # Skip invalid worlds
                pass

    return worlds


@router.post("", response_model=WorldResponse)
async def create_world(request: WorldCreateRequest):
    """Create a new world"""
    slug = init_world(
        title=request.title,
        theme=request.theme,
        style_pack=request.style_pack,
        slug=request.slug,
        image_model=request.image_model
    )

    cfg, state, _ = load_world(slug)
    return WorldResponse(
        title=cfg.title,
        slug=cfg.slug,
        theme=cfg.theme,
        style_pack=cfg.style_pack,
        text_model=cfg.text_model,
        image_model=cfg.image_model,
        tick=state.tick,
        chapter_count=len(state.chapters),
        is_current=True
    )


@router.get("/{slug}", response_model=dict)
async def get_world(slug: str):
    """Get detailed world information including chapters"""
    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

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
        chapters.append({
            "number": ch.get("number"),
            "title": ch.get("title"),
            "filename": ch.get("filename"),
            "summary": ch.get("summary"),
            "scene": scene_for_chapter.get(ch.get("number")),
            "characters_in_scene": ch.get("characters_in_scene", [])
        })

    return {
        "config": {
            "title": cfg.title,
            "slug": cfg.slug,
            "theme": cfg.theme,
            "style_pack": cfg.style_pack,
            "text_model": cfg.text_model,
            "image_model": cfg.image_model
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
async def set_current(slug: str):
    """Set the current world"""
    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    set_current_world(slug)
    return {"message": f"Current world set to {slug}"}


@router.put("/{slug}")
async def update_world(slug: str, request: WorldUpdateRequest):
    """Update world configuration"""
    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    from ..world import save_world
    cfg, state, dirs = load_world(slug)

    # Update fields if provided
    if request.title is not None:
        cfg.title = request.title
    if request.theme is not None:
        cfg.theme = request.theme
    if request.style_pack is not None:
        cfg.style_pack = request.style_pack
    if request.image_model is not None:
        cfg.image_model = request.image_model

    save_world(slug, cfg, state, dirs)

    return {
        "message": "World updated",
        "config": {
            "title": cfg.title,
            "slug": cfg.slug,
            "theme": cfg.theme,
            "style_pack": cfg.style_pack,
            "image_model": cfg.image_model
        }
    }


@router.delete("/{slug}")
async def delete_world(slug: str):
    """Delete a world"""
    if not (WORLDS_DIR / slug).exists():
        raise HTTPException(status_code=404, detail="World not found")

    import shutil
    shutil.rmtree(WORLDS_DIR / slug)

    # If this was the current world, unset it
    if get_current_world() == slug:
        from ..storage import CURRENT_WORLD_FILE
        if CURRENT_WORLD_FILE.exists():
            CURRENT_WORLD_FILE.unlink()

    return {"message": f"World {slug} deleted"}
