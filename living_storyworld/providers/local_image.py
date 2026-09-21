"""Local ComfyUI workflows, using the server's standard HTTP API."""

import copy
import io
import json
import secrets
import time
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

from .image import ImageGenerationResult, ImageProvider
from .local import validate_local_url


def validate_workflow(value: str, prompt_node: str) -> dict:
    try:
        workflow = json.loads(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Import a ComfyUI workflow exported in API format.") from exc
    if (
        not isinstance(workflow, dict)
        or not workflow
        or any(
            not isinstance(node, dict)
            or not isinstance(node.get("inputs"), dict)
            or not isinstance(node.get("class_type"), str)
            for node in workflow.values()
        )
    ):
        raise ValueError("This is not an API workflow. Use Export (API) in ComfyUI.")
    if not isinstance(workflow.get(prompt_node, {}).get("inputs", {}).get("text"), str):
        raise ValueError("Choose the positive prompt node: it must have a text input.")
    return workflow


def save_image_bytes(data: bytes, output_path: Path) -> Path:
    """Decode before writing so failed responses cannot replace a valid image."""
    if len(data) > 50 * 1024 * 1024:
        raise RuntimeError("The image exceeds the 50 MB limit.")
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")
    return output_path


class ComfyUIProvider(ImageProvider):
    def __init__(self, api_key=None):
        from ..settings import load_user_settings

        settings = load_user_settings()
        self.base_url = validate_local_url(settings.comfyui_base_url, default_path="")
        self.workflow = validate_workflow(
            settings.comfyui_workflow, settings.comfyui_prompt_node
        )
        self.prompt_node = settings.comfyui_prompt_node

    def generate(self, prompt, output_path, aspect_ratio="16:9", model=None):
        if model not in {None, "", "workflow"}:
            raise ValueError(
                "ComfyUI uses the imported workflow. Clear this world's illustration model override first."
            )
        workflow = copy.deepcopy(self.workflow)
        workflow[self.prompt_node]["inputs"]["text"] = prompt
        for node in workflow.values():
            for name in ("seed", "noise_seed"):
                if isinstance(node["inputs"].get(name), int):
                    node["inputs"][name] = secrets.randbelow(2**32)
        with requests.Session() as session:
            response = session.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow},
                timeout=15,
                allow_redirects=False,
            )
            response.raise_for_status()
            job_id = response.json().get("prompt_id")
            if not job_id:
                raise RuntimeError(
                    "ComfyUI rejected the workflow. Check its models and nodes in ComfyUI."
                )
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                response = session.get(
                    f"{self.base_url}/history/{quote(str(job_id), safe='')}",
                    timeout=15,
                    allow_redirects=False,
                )
                response.raise_for_status()
                result = response.json().get(job_id)
                if result:
                    if result.get("status", {}).get("status_str") == "error":
                        raise RuntimeError(
                            "ComfyUI could not run the workflow. Check its error log for a missing model or node."
                        )
                    images = [
                        image
                        for output in result.get("outputs", {}).values()
                        for image in output.get("images", [])
                    ]
                    if images:
                        # Prefer saved output over preview images from intermediate nodes.
                        image = next(
                            (item for item in images if item.get("type") == "output"),
                            images[0],
                        )
                        response = session.get(
                            f"{self.base_url}/view",
                            params=image,
                            timeout=30,
                            allow_redirects=False,
                        )
                        response.raise_for_status()
                        save_image_bytes(response.content, output_path)
                        return ImageGenerationResult(
                            output_path, "comfyui", "workflow", None
                        )
                    if result.get("status", {}).get("completed"):
                        raise RuntimeError(
                            "The ComfyUI workflow finished without an image. Add a Save Image node."
                        )
                time.sleep(1)
            # Remove only our queued item; never interrupt somebody else's active job.
            session.post(
                f"{self.base_url}/queue",
                json={"delete": [job_id]},
                timeout=10,
                allow_redirects=False,
            )
        raise RuntimeError(
            "ComfyUI took more than five minutes. Check its queue before trying again."
        )

    def get_default_model(self):
        return "workflow"

    def estimate_cost(self, model=None):
        return None

    @property
    def provider_name(self):
        return "ComfyUI"

    @property
    def requires_api_key(self):
        return False
