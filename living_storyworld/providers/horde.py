"""Free community image generation through an AI Horde account."""

import base64
import time

import requests

from .image import ImageGenerationResult, ImageProvider
from .local_image import save_image_bytes
from .text import _init_api_key


class HordeImageProvider(ImageProvider):
    def __init__(self, api_key=None):
        self.api_key = _init_api_key("HORDE_API_KEY", "AI Horde", api_key)
        if self.api_key == "0000000000":
            raise ValueError(
                "Use a free AI Horde account key. Anonymous access shares generated images."
            )

    def generate(self, prompt, output_path, aspect_ratio="16:9", model=None):
        sizes = {
            "16:9": (768, 448),
            "1:1": (512, 512),
            "4:3": (640, 512),
            "3:4": (512, 640),
            "9:16": (448, 768),
        }
        width, height = sizes.get(aspect_ratio, sizes["16:9"])
        body = {
            "prompt": prompt,
            "params": {"n": 1, "steps": 20, "width": width, "height": height},
            "r2": False,
            "shared": False,
            "trusted_workers": True,
            "censor_nsfw": True,
            "allow_downgrade": True,
        }
        if model:
            body["models"] = [model]
        base = "https://aihorde.net/api/v2"
        with requests.Session() as session:
            session.headers.update(
                {
                    "apikey": self.api_key,
                    "Client-Agent": "LivingStoryworld:1:https://github.com/jonmartin721/living-story-world",
                }
            )
            response = session.post(f"{base}/generate/async", json=body, timeout=20)
            response.raise_for_status()
            job_id = response.json()["id"]
            completed = False
            try:
                deadline = time.monotonic() + 300
                while time.monotonic() < deadline:
                    response = session.get(
                        f"{base}/generate/check/{job_id}", timeout=20
                    )
                    response.raise_for_status()
                    status = response.json()
                    if status.get("faulted"):
                        raise RuntimeError(
                            "AI Horde could not generate this image. Try again or choose another available model."
                        )
                    if status.get("done"):
                        response = session.get(
                            f"{base}/generate/status/{job_id}", timeout=20
                        )
                        response.raise_for_status()
                        results = response.json().get("generations", [])
                        if not results or results[0].get("censored"):
                            raise RuntimeError(
                                "AI Horde returned no usable image. Try a different scene description."
                            )
                        item = results[0]
                        save_image_bytes(
                            base64.b64decode(item["img"], validate=True), output_path
                        )
                        completed = True
                        return ImageGenerationResult(
                            output_path,
                            "horde",
                            item.get("model", model or "available"),
                            0.0,
                        )
                    time.sleep(3)
                raise RuntimeError(
                    "AI Horde's community queue took more than five minutes. Your request was cancelled; try again later."
                )
            finally:
                if not completed:
                    try:
                        session.delete(f"{base}/generate/status/{job_id}", timeout=10)
                    except requests.RequestException:
                        pass

    def get_default_model(self):
        return ""

    def estimate_cost(self, model=None):
        return 0.0

    @property
    def provider_name(self):
        return "AI Horde"

    @property
    def requires_api_key(self):
        return True
