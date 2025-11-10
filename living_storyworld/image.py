from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional
import urllib.request

from .config import STYLE_PACKS
from .settings import load_user_settings, get_api_key_for_provider
from .providers import get_image_provider


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
    """Generate a scene image using the configured image provider.

    Args:
        base_dir: World base directory
        image_model: Model to use (provider-specific)
        style_pack: Visual style preset key
        prompt: Scene description
        chapter_num: Optional chapter number for filename
        aspect_ratio: Image aspect ratio (default "16:9" for landscape)

    Returns:
        Path to generated PNG image
    """
    style = STYLE_PACKS.get(style_pack, STYLE_PACKS["storybook-ink"])
    full_prompt = f"{style}. Scene illustration: {prompt}"

    key = _cache_key("scene", style_pack, full_prompt, aspect_ratio, image_model)
    out = base_dir / "media" / "scenes" / (f"scene-{chapter_num:04d}-{key}.png" if chapter_num else f"scene-{key}.png")

    # Check cache first
    if out.exists():
        print(f"[INFO] Using cached image: {out.name}", flush=True)
        return out

    # Load settings to determine which provider to use
    settings = load_user_settings()
    image_provider_name = settings.image_provider
    api_key = get_api_key_for_provider(image_provider_name, settings)

    # Get the image provider
    try:
        provider = get_image_provider(image_provider_name, api_key=api_key)
        result = provider.generate(
            prompt=full_prompt,
            output_path=out,
            aspect_ratio=aspect_ratio,
            model=image_model
        )
        print(f"[INFO] Generated image using {result.provider} ({result.model}), cost: ${result.estimated_cost:.4f}", flush=True)
    except Exception as e:
        # Fallback to legacy Replicate client if provider setup fails
        print(f"[WARN] Provider {image_provider_name} failed, falling back to Replicate: {e}", flush=True)
        client = _get_replicate_client()

        # Map friendly model names to Replicate model IDs
        model_map = {
            "flux-dev": "black-forest-labs/flux-dev",
            "flux-schnell": "black-forest-labs/flux-schnell",
        }
        replicate_model = model_map.get(image_model, "black-forest-labs/flux-dev")

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
        out.parent.mkdir(parents=True, exist_ok=True)
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

