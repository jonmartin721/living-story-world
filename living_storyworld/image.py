from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Optional

from .config import STYLE_PACKS


def _get_client():
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("OpenAI SDK not installed. Run: pip install openai>=1.0") from e
    return OpenAI()


def _cache_key(kind: str, style: str, prompt: str, size: str) -> str:
    h = hashlib.sha256()
    h.update(kind.encode())
    h.update(style.encode())
    h.update(prompt.encode())
    h.update(size.encode())
    return h.hexdigest()[:16]


def generate_scene_image(
    base_dir: Path,
    image_model: str,
    style_pack: str,
    prompt: str,
    chapter_num: Optional[int] = None,
    size: str = "1536x1024",
) -> Path:
    client = _get_client()
    style = STYLE_PACKS.get(style_pack, STYLE_PACKS["storybook-ink"])
    full_prompt = f"{style}. Scene illustration: {prompt}"

    key = _cache_key("scene", style_pack, full_prompt, size)
    out = base_dir / "media" / "scenes" / (f"scene-{chapter_num:04d}-{key}.png" if chapter_num else f"scene-{key}.png")
    if out.exists():
        return out

    resp = client.images.generate(
        model=image_model,
        prompt=full_prompt,
        size=size,
        quality="high",
        n=1,
    )
    b64 = resp.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    out.write_bytes(img_bytes)
    _append_media_index(base_dir, {
        "type": "scene",
        "chapter": chapter_num,
        "file": str(out.relative_to(base_dir)),
        "key": key,
        "prompt": prompt,
        "style_pack": style_pack,
        "size": size,
    })
    return out


def _append_media_index(base_dir: Path, entry: dict) -> None:
    idx = base_dir / "media" / "index.json"
    data = []
    if idx.exists():
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
        except Exception:
            data = []
    data.append(entry)
    idx.write_text(json.dumps(data, indent=2), encoding="utf-8")

