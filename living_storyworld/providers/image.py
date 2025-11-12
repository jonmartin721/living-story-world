"""Image generation provider abstractions and implementations."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _validate_image_data(image_data: bytes) -> bool:
    """Validate that image data is actually a valid image.

    Uses PIL to verify the image data can be opened and is a valid image format.
    Returns True if valid, False otherwise.
    """
    try:
        import io

        from PIL import Image

        # Try to open the image with PIL
        with Image.open(io.BytesIO(image_data)) as img:
            # Verify the image can be loaded
            img.verify()

        # If verify succeeds, try to actually load it to ensure it's fully valid
        with Image.open(io.BytesIO(image_data)) as img:
            # This will raise an exception if the image is corrupted
            img.load()

        return True
    except ImportError:
        # PIL not available, skip validation
        logging.warning("PIL not available, skipping image validation")
        return True
    except Exception as e:
        logging.warning(f"Invalid image data detected: {e}")
        return False


def _safe_download_image(
    url: str, output_path: Path, max_size_mb: int = 50, timeout: int = 30
) -> Path:
    """Safely download an image with size and timeout limits.

    Security: Validates URL scheme, content type, and enforces size limits.
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
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}")

    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        logging.warning(f"Unexpected content type: {content_type}")

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
                    output_path.unlink(missing_ok=True)
                    raise ValueError(f"Download exceeded size limit ({max_size_mb} MB)")
                f.write(chunk)
    except Exception:
        output_path.unlink(missing_ok=True)
        raise

    return output_path


@dataclass
class ImageGenerationResult:
    """Result from image generation."""

    image_path: Path
    provider: str
    model: str
    estimated_cost: float  # in USD
    cached: bool = False


class ImageProvider(ABC):
    """Abstract base class for image generation providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        model: Optional[str] = None,
    ) -> ImageGenerationResult:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            output_path: Where to save the generated image
            aspect_ratio: Image aspect ratio (e.g., "16:9", "1:1", "4:3")
            model: Optional model override

        Returns:
            ImageGenerationResult with path and metadata
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass

    @abstractmethod
    def estimate_cost(self, model: Optional[str] = None) -> float:
        """Estimate cost in USD for generating an image."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key."""
        pass


class ReplicateProvider(ImageProvider):
    """Replicate image generation provider (Flux models)."""

    ALLOWED_MODELS = {"flux-dev", "flux-schnell"}
    ALLOWED_ASPECT_RATIOS = {"1:1", "16:9", "21:9", "4:3", "3:4", "9:16"}

    def __init__(self, api_key: Optional[str] = None):
        self.api_token = api_key or os.environ.get("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise RuntimeError(
                "Replicate API token not found. Set REPLICATE_API_TOKEN environment variable or pass api_key parameter."
            )

    def generate(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        model: Optional[str] = None,
    ) -> ImageGenerationResult:
        # VALIDATION: Aspect ratio
        if aspect_ratio not in self.ALLOWED_ASPECT_RATIOS:
            raise ValueError(
                f"Invalid aspect ratio: {aspect_ratio}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_ASPECT_RATIOS))}"
            )

        try:
            import replicate
        except ImportError as e:
            raise RuntimeError(
                "Replicate SDK not installed. Run: pip install replicate>=1.0"
            ) from e

        client = replicate.Client(api_token=self.api_token)
        model_name = model or self.get_default_model()

        # VALIDATION: Model name
        if model_name not in self.ALLOWED_MODELS:
            raise ValueError(
                f"Unknown Replicate model: {model_name}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_MODELS))}"
            )

        # Map friendly names to Replicate model IDs
        model_map = {
            "flux-dev": "black-forest-labs/flux-dev",
            "flux-schnell": "black-forest-labs/flux-schnell",
        }
        replicate_model = model_map.get(model_name, "black-forest-labs/flux-dev")

        # Build input parameters
        input_params = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
            "output_quality": 90,
        }

        # Add model-specific parameters
        if "flux-dev" in model_name:
            input_params["guidance"] = 3.5
            input_params["num_inference_steps"] = 28

        # Generate image
        output = client.run(replicate_model, input=input_params)

        # Download image
        if isinstance(output, list) and len(output) > 0:
            image_url = str(output[0])
        else:
            image_url = str(output)

        # Download with security checks
        _safe_download_image(image_url, output_path)

        cost = self.estimate_cost(model_name)

        return ImageGenerationResult(
            image_path=output_path,
            provider="replicate",
            model=model_name,
            estimated_cost=cost,
        )

    def get_default_model(self) -> str:
        return "flux-dev"

    def estimate_cost(self, model: Optional[str] = None) -> float:
        """Replicate pricing varies by model."""
        model_name = model or self.get_default_model()
        if "flux-dev" in model_name:
            return 0.025
        elif "flux-schnell" in model_name:
            return 0.003
        return 0.02

    @property
    def provider_name(self) -> str:
        return "Replicate"

    @property
    def requires_api_key(self) -> bool:
        return True


class HuggingFaceImageProvider(ImageProvider):
    """Hugging Face image generation provider (SDXL, Flux, etc.)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Hugging Face API key not found. Set HUGGINGFACE_API_KEY environment variable or pass api_key parameter."
            )

    def generate(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        model: Optional[str] = None,
    ) -> ImageGenerationResult:
        import requests

        model_name = model or self.get_default_model()
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": prompt}

        response = requests.post(api_url, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if content_type and not content_type.startswith("image/"):
            raise RuntimeError(f"Unexpected content type: {content_type}")

        content_length = int(response.headers.get("Content-Length", 0))
        max_bytes = 50 * 1024 * 1024
        if content_length > max_bytes:
            raise ValueError(f"Response too large: {content_length} bytes (max: 50MB)")

        # Stream download with size check
        output_path.parent.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        try:
            with output_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        output_path.unlink(missing_ok=True)
                        raise ValueError("Download exceeded size limit (50MB)")
                    f.write(chunk)
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        cost = self.estimate_cost(model_name)

        return ImageGenerationResult(
            image_path=output_path,
            provider="huggingface",
            model=model_name,
            estimated_cost=cost,
        )

    def get_default_model(self) -> str:
        return "stabilityai/stable-diffusion-xl-base-1.0"

    def estimate_cost(self, model: Optional[str] = None) -> float:
        """Hugging Face Inference API is free (rate-limited)."""
        return 0.0

    @property
    def provider_name(self) -> str:
        return "Hugging Face"

    @property
    def requires_api_key(self) -> bool:
        return True


class PollinationsProvider(ImageProvider):
    """Pollinations.ai free image generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        # Pollinations doesn't require an API key
        pass

    def generate(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        model: Optional[str] = None,
    ) -> ImageGenerationResult:
        import requests

        model_name = model or self.get_default_model()

        # Pollinations.ai simple API
        # URL format:
        # https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&model={model}

        # Convert aspect ratio to dimensions
        width, height = self._aspect_ratio_to_dimensions(aspect_ratio)

        # Pollinations.ai uses GET requests with the prompt in the URL path
        # Pollinations.ai uses GET requests with the prompt in the URL path.
        # The `requests` library can be tricky with URLs that have dynamic path segments
        # and query parameters, so we construct the URL manually.
        import urllib.parse

        # Truncate extremely long prompts if necessary (rarely needed)
        max_prompt_length = 1000  # Conservative limit for URL safety
        if len(prompt) > max_prompt_length:
            logger.warning(
                f"Prompt too long ({
                    len(prompt)} chars), truncating to {max_prompt_length}"
            )
            prompt = prompt[:max_prompt_length]

        # Manually construct the URL with the prompt in the path
        encoded_prompt = urllib.parse.quote(prompt)
        base_url = "https://image.pollinations.ai/prompt/"

        import random
        import time

        # Add random seed to bypass Pollinations caching for regeneration
        seed = f"{int(time.time())}-{random.randint(1000, 9999)}"
        params = {
            "width": width,
            "height": height,
            "model": model_name,
            "nologo": "true",
            "seed": seed,
        }

        # Build the final URL string
        query_string = urllib.parse.urlencode(params)
        url = f"{base_url}{encoded_prompt}?{query_string}"

        try:
            # Always use GET for Pollinations
            response = requests.get(url, stream=True, timeout=30)

            response.raise_for_status()
        except Exception as e:
            from ..exceptions import handle_api_error

            raise handle_api_error(e, "Pollinations") from e

        content_type = response.headers.get("Content-Type", "")
        if content_type and not content_type.startswith("image/"):
            raise RuntimeError(f"Unexpected content type: {content_type}")

        content_length = int(response.headers.get("Content-Length", 0))
        max_bytes = 50 * 1024 * 1024
        if content_length > max_bytes:
            raise ValueError(f"Response too large: {content_length} bytes (max: 50MB)")

        # Download all data first for validation
        output_path.parent.mkdir(parents=True, exist_ok=True)
        downloaded = 0
        image_data = bytearray()

        try:
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded > max_bytes:
                    raise ValueError("Download exceeded size limit (50MB)")
                image_data.extend(chunk)

            # Validate the image data before saving
            if not _validate_image_data(bytes(image_data)):
                raise RuntimeError("Downloaded data is not a valid image")

            # Save validated image data
            with output_path.open("wb") as f:
                f.write(image_data)

        except Exception:
            output_path.unlink(missing_ok=True)
            raise

        return ImageGenerationResult(
            image_path=output_path,
            provider="pollinations",
            model=model_name,
            estimated_cost=0.0,  # Free
        )

    def _aspect_ratio_to_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        """Convert aspect ratio string to pixel dimensions."""
        ratios = {
            "16:9": (1344, 768),
            "1:1": (1024, 1024),
            "4:3": (1152, 896),
            "3:4": (896, 1152),
            "9:16": (768, 1344),
        }
        return ratios.get(aspect_ratio, (1344, 768))

    def get_default_model(self) -> str:
        return "flux"

    def estimate_cost(self, model: Optional[str] = None) -> float:
        """Pollinations.ai is completely free."""
        return 0.0

    @property
    def provider_name(self) -> str:
        return "Pollinations.ai"

    @property
    def requires_api_key(self) -> bool:
        return False


class FalAIProvider(ImageProvider):
    """Fal.ai image generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FAL_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Fal.ai API key not found. Set FAL_KEY environment variable or pass api_key parameter."
            )

    def generate(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        model: Optional[str] = None,
    ) -> ImageGenerationResult:
        import requests

        model_name = model or self.get_default_model()

        # Fal.ai API endpoint
        api_url = f"https://fal.run/fal-ai/{model_name}"

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

        # Convert aspect ratio to image size
        image_size = self._aspect_ratio_to_size(aspect_ratio)

        payload = {
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": 28,
            "num_images": 1,
        }

        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        image_url = result["images"][0]["url"]

        # Download the image
        # Download with security checks
        _safe_download_image(image_url, output_path)

        cost = self.estimate_cost(model_name)

        return ImageGenerationResult(
            image_path=output_path,
            provider="fal",
            model=model_name,
            estimated_cost=cost,
        )

    def _aspect_ratio_to_size(self, aspect_ratio: str) -> str:
        """Convert aspect ratio to Fal.ai size string."""
        sizes = {
            "16:9": "landscape_16_9",
            "1:1": "square",
            "4:3": "landscape_4_3",
            "3:4": "portrait_4_3",
            "9:16": "portrait_16_9",
        }
        return sizes.get(aspect_ratio, "landscape_16_9")

    def get_default_model(self) -> str:
        return "flux/dev"

    def estimate_cost(self, model: Optional[str] = None) -> float:
        """Fal.ai pricing varies by model."""
        model_name = model or self.get_default_model()
        if "flux/dev" in model_name:
            return 0.025
        elif "flux/schnell" in model_name:
            return 0.003
        return 0.01

    @property
    def provider_name(self) -> str:
        return "Fal.ai"

    @property
    def requires_api_key(self) -> bool:
        return True


def get_image_provider(
    provider_name: str, api_key: Optional[str] = None
) -> ImageProvider:
    """Factory function to get an image provider by name.

    Args:
        provider_name: One of "replicate", "huggingface", "pollinations", "fal"
        api_key: Optional API key (falls back to environment variables)

    Returns:
        Configured ImageProvider instance

    Raises:
        ValueError: If provider_name is not recognized
    """
    providers = {
        "replicate": ReplicateProvider,
        "huggingface": HuggingFaceImageProvider,
        "pollinations": PollinationsProvider,
        "fal": FalAIProvider,
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown image provider: {provider_name}. "
            f"Available providers: {', '.join(providers.keys())}"
        )

    return provider_class(api_key=api_key)
