from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .config import STYLE_PACKS
from .providers import get_image_provider
from .settings import get_api_key_for_provider, load_user_settings

logger = logging.getLogger(__name__)


def safe_download_image(
    url: str, output_path: Path, max_size_mb: int = 50, timeout: int = 30
) -> Path:
    """Safely download an image with size and timeout limits.

    Security: Validates URL scheme, content type, and enforces size limits
    to prevent SSRF, DoS, and other attacks.

    Args:
        url: The URL to download from
        output_path: Where to save the downloaded file
        max_size_mb: Maximum file size in MB (default: 50)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Path to the downloaded file

    Raises:
        ValueError: If URL scheme is invalid, content type is wrong, or file too large
        RuntimeError: If download fails
    """
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library required. Run: pip install requests")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed."
        )

    # Stream download with limits
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Download timed out after {timeout} seconds")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Download failed: {e}")

    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        logging.warning(f"Unexpected content type: {content_type} (expected image/*)")

    content_length = int(response.headers.get("Content-Length", 0))
    max_bytes = max_size_mb * 1024 * 1024
    if content_length > max_bytes:
        raise ValueError(f"File too large: {content_length} bytes (max: {max_bytes})")

    # Download in chunks
    output_path.parent.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    try:
        with output_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded > max_bytes:
                    # Clean up partial file
                    output_path.unlink(missing_ok=True)
                    raise ValueError(f"Download exceeded size limit ({max_size_mb} MB)")
                f.write(chunk)
    except Exception:
        # Clean up partial file on any error
        output_path.unlink(missing_ok=True)
        raise

    logging.info(f"Downloaded {downloaded} bytes to {output_path}")
    return output_path


def _cache_key(
    kind: str, style: str, prompt: str, aspect_ratio: str, model: str
) -> str:
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
    bypass_cache: bool = False,
) -> Path:
    """Generate a scene image using the configured image provider.

    Args:
        base_dir: World base directory
        image_model: Model to use (provider-specific)
        style_pack: Visual style preset key
        prompt: Scene description
        chapter_num: Optional chapter number for filename
        aspect_ratio: Image aspect ratio (default "16:9" for landscape)
        bypass_cache: If True, generate a new image even if cached version exists

    Returns:
        Path to generated PNG image
    """
    style = STYLE_PACKS.get(style_pack, STYLE_PACKS["storybook-ink"])
    # Emphasize style by putting it at beginning AND wrapping the prompt
    # Explicitly prevent text generation - models sometimes render text instead of scenes
    full_prompt = f"{style} | {prompt}. Style: {style}. IMPORTANT: Generate a visual scene illustration only, no text, no words, no letters, no signs, no writing of any kind."

    import random
    import time

    cache_suffix = (
        f"-{int(time.time())}-{random.randint(1000, 9999)}" if bypass_cache else ""
    )
    key = _cache_key("scene", style_pack, full_prompt, aspect_ratio, image_model)
    out = (
        base_dir
        / "media"
        / "scenes"
        / (
            f"scene-{chapter_num:04d}-{key}{cache_suffix}.png"
            if chapter_num
            else f"scene-{key}{cache_suffix}.png"
        )
    )

    if not bypass_cache and out.exists():
        logger.debug("Using cached image: %s", out.name)
        return out

    settings = load_user_settings()
    image_provider_name = settings.image_provider
    api_key = get_api_key_for_provider(image_provider_name, settings)

    try:
        provider = get_image_provider(image_provider_name, api_key=api_key)
        image_result = provider.generate(
            prompt=full_prompt,
            output_path=out,
            aspect_ratio=aspect_ratio,
            model=image_model,
        )
        logger.info(
            "Generated image using %s (%s), cost: $%.4f",
            image_result.provider,
            image_result.model,
            image_result.estimated_cost,
        )
    except Exception as e:
        # Fallback to Pollinations if the chosen provider fails
        if image_provider_name != "pollinations":
            logger.warning(
                "Failed to generate with %s (%s), falling back to Pollinations: %s",
                image_provider_name,
                image_model,
                str(e),
            )
            try:
                pollinations_provider = get_image_provider("pollinations", api_key=None)
                result = pollinations_provider.generate(
                    prompt=full_prompt,
                    output_path=out,
                    aspect_ratio=aspect_ratio,
                    model="flux",  # Pollinations default
                )
                logger.info(
                    "Generated image using Pollinations fallback (%s), cost: $%.4f",
                    result.model,
                    result.estimated_cost,
                )
            except Exception as fallback_error:
                logger.error(
                    "Both %s and Pollinations fallback failed: %s",
                    image_provider_name,
                    str(fallback_error),
                )
                raise RuntimeError(
                    f"Image generation failed with both {image_provider_name} and Pollinations: {fallback_error}"
                )
        else:
            # If already using Pollinations and it failed, just raise the original error
            logger.error("Pollinations image generation failed: %s", str(e))
            raise

    _append_media_index(
        base_dir,
        {
            "type": "scene",
            "chapter": chapter_num,
            "file": str(out.relative_to(base_dir)),
            "key": key,
            "prompt": prompt,
            "style_pack": style_pack,
            "aspect_ratio": aspect_ratio,
            "model": image_model,
        },
    )
    return out


def _append_media_index(base_dir: Path, entry: dict) -> None:
    idx = base_dir / "media" / "index.json"
    idx.parent.mkdir(parents=True, exist_ok=True)
    data = []
    if idx.exists():
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
        except Exception:
            data = []
    data.append(entry)
    idx.write_text(json.dumps(data, indent=2), encoding="utf-8")
