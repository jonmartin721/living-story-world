from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional
import urllib.request

from .config import STYLE_PACKS


def _get_replicate_client():
    try:
        import replicate  # type: ignore
    except Exception as e:
        raise RuntimeError("Replicate SDK not installed. Run: pip install replicate>=1.0") from e

    # Replicate uses REPLICATE_API_TOKEN env var by default
    if not os.environ.get("REPLICATE_API_TOKEN"):
        raise RuntimeError("REPLICATE_API_TOKEN environment variable not set. Get one at https://replicate.com/account/api-tokens")

    return replicate.Client(api_token=os.environ["REPLICATE_API_TOKEN"])


def _cache_key(kind: str, style: str, prompt: str, aspect_ratio: str, model: str) -> str:
    h = hashlib.sha256()
    h.update(kind.encode())
    h.update(style.encode())
    h.update(prompt.encode())
    h.update(aspect_ratio.encode())
    h.update(model.encode())
    return h.hexdigest()[:16]


def generate_scene_image(
    base_dir: Path,
    image_model: str,
    style_pack: str,
    prompt: str,
    chapter_num: Optional[int] = None,
    aspect_ratio: str = "16:9",
) -> Path:
    """Generate a scene image using Flux via Replicate.

    Args:
        base_dir: World base directory
        image_model: Flux model to use ("flux-dev" or "flux-schnell")
        style_pack: Visual style preset key
        prompt: Scene description
        chapter_num: Optional chapter number for filename
        aspect_ratio: Image aspect ratio (default "16:9" for landscape)

    Returns:
        Path to generated PNG image
    """
    client = _get_replicate_client()
    style = STYLE_PACKS.get(style_pack, STYLE_PACKS["storybook-ink"])
    full_prompt = f"{style}. Scene illustration: {prompt}"

    # Map friendly model names to Replicate model IDs
    model_map = {
        "flux-dev": "black-forest-labs/flux-dev",
        "flux-schnell": "black-forest-labs/flux-schnell",
    }
    replicate_model = model_map.get(image_model, "black-forest-labs/flux-dev")

    key = _cache_key("scene", style_pack, full_prompt, aspect_ratio, image_model)
    out = base_dir / "media" / "scenes" / (f"scene-{chapter_num:04d}-{key}.png" if chapter_num else f"scene-{key}.png")
    if out.exists():
        return out

    # Run Flux model via Replicate
    input_params = {
        "prompt": full_prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": "png",
        "output_quality": 90,
    }

    # Add model-specific parameters
    if image_model == "flux-dev":
        input_params["guidance"] = 3.5
        input_params["num_inference_steps"] = 28

    output = client.run(replicate_model, input=input_params)

    # Download image from URL (Replicate returns a FileOutput or list)
    if isinstance(output, list) and len(output) > 0:
        image_url = str(output[0])
    else:
        image_url = str(output)

    # Download and save the image
    urllib.request.urlretrieve(image_url, out)

    _append_media_index(base_dir, {
        "type": "scene",
        "chapter": chapter_num,
        "file": str(out.relative_to(base_dir)),
        "key": key,
        "prompt": prompt,
        "style_pack": style_pack,
        "aspect_ratio": aspect_ratio,
        "model": image_model,
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

