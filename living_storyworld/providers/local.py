"""Ollama and OpenAI-compatible servers running on this computer."""

from ipaddress import ip_address
from urllib.parse import urlparse

from .text import TextGenerationResult, TextProvider


def validate_local_url(value: str, default_path: str = "/v1") -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    try:
        loopback = (
            parsed.hostname == "localhost"
            or ip_address(parsed.hostname or "").is_loopback
        )
        port = parsed.port
    except ValueError:
        loopback = False
        port = None
    if (
        not loopback
        or parsed.scheme not in {"http", "https"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use a local server URL such as http://127.0.0.1:1234/v1.")
    if port == 0:
        raise ValueError("The local server port must be greater than zero.")
    return value if parsed.path.rstrip("/") else f"{value}{default_path}"


class LocalProvider(TextProvider):
    def __init__(self, api_key=None, *, provider="local", base_url=None):
        from ..settings import load_user_settings

        settings = load_user_settings()
        self.provider = provider
        self.base_url = validate_local_url(
            base_url or getattr(settings, f"{provider}_base_url")
        )
        self.api_key = (
            api_key
            or (settings.local_api_key if provider == "local" else None)
            or "local"
        )
        self.reasoning_effort = settings.local_reasoning_effort

    def list_models(self) -> list[str]:
        from openai import OpenAI

        with OpenAI(
            base_url=self.base_url, api_key=self.api_key, timeout=8, max_retries=0
        ) as client:
            models = [item.id for item in client.models.list()]
        if self.provider == "ollama":
            models = [
                name for name in models if not name.endswith((":cloud", "-cloud"))
            ]
        return models

    def get_default_model(self) -> str:
        try:
            models = self.list_models()
        except Exception as exc:
            raise RuntimeError(
                "Could not reach your local model server. Start it and check the connection in Settings."
            ) from exc
        if not models:
            raise RuntimeError(
                "No local models found. Load a model in your server, then check the connection in Settings."
            )
        return models[0]

    def generate(self, messages, temperature=1.0, model=None):
        from openai import OpenAI

        model_name = model or self.get_default_model()
        if self.provider == "ollama" and model_name.endswith((":cloud", "-cloud")):
            raise ValueError(
                "Choose an installed local model for Ollama. Cloud models are not part of the free local connection."
            )
        try:
            options = (
                {}
                if self.reasoning_effort == "default"
                else {"reasoning_effort": self.reasoning_effort}
            )
            with OpenAI(
                base_url=self.base_url, api_key=self.api_key, timeout=300, max_retries=0
            ) as client:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    **options,
                )
        except Exception as exc:
            raise RuntimeError(
                "The local model could not finish the request. Check that your server is running and the selected model is loaded."
            ) from exc
        if response.choices[0].finish_reason == "length":
            raise RuntimeError(
                "The local model reached its output limit. Turn reasoning off in Settings or increase your server's output limit."
            )
        content = response.choices[0].message.content or ""
        # Some reasoning servers include this channel in message.content.
        if "</think>" in content:
            content = content.split("</think>", 1)[1].lstrip()
        if not content.strip():
            raise RuntimeError(
                "The local model returned no story. Try a different model or increase its output limit."
            )
        return TextGenerationResult(content, self.provider, model_name, 0.0)

    def estimate_cost(self, messages, model=None):
        return 0.0

    @property
    def provider_name(self):
        return "Ollama" if self.provider == "ollama" else "Local"

    @property
    def requires_api_key(self):
        return False
