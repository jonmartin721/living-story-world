"""Text generation provider abstractions and implementations."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .catalog import TEXT_PROVIDERS, default_model, text_cost

logger = logging.getLogger(__name__)


def _init_api_key(
    env_var: str, provider_name: str, api_key: Optional[str] = None
) -> str:
    """Get API key from parameter or environment variable."""
    key = api_key or os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"{provider_name} API key not found. "
            f"Set {env_var} environment variable or pass api_key parameter."
        )
    return key


@dataclass
class TextGenerationResult:
    """Result from text generation."""

    content: str
    provider: str
    model: str
    estimated_cost: Optional[float]  # USD; None when pricing is not known


class TextProvider(ABC):
    """Abstract base class for text generation providers."""

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> TextGenerationResult:
        """Generate text from messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-2.0)
            model: Optional model override

        Returns:
            TextGenerationResult with generated content and metadata
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass

    @abstractmethod
    def estimate_cost(
        self, messages: list[dict[str, str]], model: Optional[str] = None
    ) -> float:
        """Estimate cost in USD for generating with these messages."""
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


class OpenAICompatibleProvider(TextProvider):
    """Base class for providers using the OpenAI SDK with custom base URLs."""

    @abstractmethod
    def get_base_url(self) -> Optional[str]:
        """Get the base URL for this provider. None for native OpenAI."""
        pass

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> TextGenerationResult:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "OpenAI SDK not installed. Run: pip install openai>=1.0"
            ) from e

        base_url = self.get_base_url()
        if base_url:
            client = OpenAI(
                api_key=self.api_key, base_url=base_url, timeout=120, max_retries=1
            )  # pylint: disable=no-member
        else:
            client = OpenAI(api_key=self.api_key, timeout=120, max_retries=1)  # pylint: disable=no-member

        model_name = model or self.get_default_model()

        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore
            temperature=temperature,
        )

        content = resp.choices[0].message.content or ""
        cost = self.estimate_cost(messages, model_name)
        provider_id = {"Together AI": "together", "Hugging Face": "huggingface"}.get(self.provider_name, self.provider_name.lower())
        usage = getattr(resp, "usage", None)
        if usage and isinstance(usage.prompt_tokens, int) and isinstance(usage.completion_tokens, int):
            cost = text_cost(provider_id, model_name, usage.prompt_tokens, usage.completion_tokens)
        if not content.strip():
            raise RuntimeError(f"{self.provider_name} returned no story. Please try again.")

        return TextGenerationResult(
            content=content,
            provider=provider_id,
            model=model_name,
            estimated_cost=cost,
        )


class OpenAIProvider(TextProvider):
    """OpenAI text generation provider."""

    ALLOWED_MODELS = {
        "gpt-5.6-luna",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-5-chat",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("OPENAI_API_KEY", "OpenAI", api_key)

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> TextGenerationResult:
        from ..exceptions import InvalidModelError, handle_api_error

        # VALIDATION: Temperature bounds
        if not 0.0 <= temperature <= 2.0:
            raise ValueError(
                f"Temperature must be between 0.0 and 2.0, got {temperature}"
            )

        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "OpenAI SDK not installed. Run: pip install openai>=1.0"
            ) from e

        client = OpenAI(api_key=self.api_key, timeout=120, max_retries=1)
        model_name = model or self.get_default_model()

        # VALIDATION: Model name
        if model_name not in self.ALLOWED_MODELS and not model_name.startswith(("gpt-", "ft:", "o3", "o4")):
            raise InvalidModelError("OpenAI", model_name, list(self.ALLOWED_MODELS))

        # The original GPT-5 reasoning models reject sampling parameters.
        # https://developers.openai.com/api/docs/guides/latest-model
        generation_options = {}
        if not model_name.startswith(("gpt-5", "gpt-6", "o3", "o4")):
            generation_options["temperature"] = temperature
        if model_name.startswith("gpt-5.6"):
            generation_options["reasoning_effort"] = "none"

        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,  # type: ignore
                **generation_options,
            )
        except Exception as e:
            # Convert to user-friendly error
            raise handle_api_error(e, "OpenAI") from e

        content = resp.choices[0].message.content or ""
        cost = self.estimate_cost(messages, model_name)
        usage = getattr(resp, "usage", None)
        if usage and isinstance(usage.prompt_tokens, int) and isinstance(usage.completion_tokens, int):
            provider_id = {"Together AI": "together", "Hugging Face": "huggingface"}.get(self.provider_name, self.provider_name.lower())
            cost = text_cost(provider_id, model_name, usage.prompt_tokens, usage.completion_tokens)
        if not content.strip():
            raise RuntimeError(f"{self.provider_name} returned no story. Please try again.")

        return TextGenerationResult(
            content=content,
            provider="openai",
            model=model_name,
            estimated_cost=cost,
        )

    def get_default_model(self) -> str:
        return default_model("openai")

    def estimate_cost(self, messages, model=None):
        input_tokens = max(1, sum(len(m["content"]) for m in messages) // 4)
        return text_cost("openai", model or self.get_default_model(), input_tokens, 1000)

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    @property
    def requires_api_key(self) -> bool:
        return True


class TogetherAIProvider(OpenAICompatibleProvider):
    """Together AI text generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("TOGETHER_API_KEY", "Together AI", api_key)

    def get_base_url(self) -> Optional[str]:
        return "https://api.together.xyz/v1"

    def get_default_model(self) -> str:
        return default_model("together")

    def estimate_cost(self, messages, model=None):
        input_tokens = max(1, sum(len(m["content"]) for m in messages) // 4)
        return text_cost("together", model or self.get_default_model(), input_tokens, 1000)

    @property
    def provider_name(self) -> str:
        return "Together AI"

    @property
    def requires_api_key(self) -> bool:
        return True


class HuggingFaceProvider(OpenAICompatibleProvider):
    """Hugging Face Inference Providers router (authenticated)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("HUGGINGFACE_API_KEY", "Hugging Face", api_key)

    def get_base_url(self) -> str:
        return "https://router.huggingface.co/v1"

    def get_default_model(self) -> str:
        return default_model("huggingface")

    def estimate_cost(self, messages, model=None):
        return None

    @property
    def provider_name(self) -> str:
        return "Hugging Face"

    @property
    def requires_api_key(self) -> bool:
        return True


class GroqProvider(OpenAICompatibleProvider):
    """Groq text generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("GROQ_API_KEY", "Groq", api_key)

    def get_base_url(self) -> Optional[str]:
        return "https://api.groq.com/openai/v1"

    def get_default_model(self) -> str:
        return default_model("groq")

    def estimate_cost(self, messages, model=None):
        input_tokens = max(1, sum(len(m["content"]) for m in messages) // 4)
        return text_cost("groq", model or self.get_default_model(), input_tokens, 1000)

    @property
    def provider_name(self) -> str:
        return "Groq"

    @property
    def requires_api_key(self) -> bool:
        return True


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter text generation provider - supports GLM-4.6 and many other models."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("OPENROUTER_API_KEY", "OpenRouter", api_key)

    def get_base_url(self) -> Optional[str]:
        return "https://openrouter.ai/api/v1"

    def get_default_model(self) -> str:
        return default_model("openrouter")

    def estimate_cost(self, messages, model=None):
        input_tokens = max(1, sum(len(m["content"]) for m in messages) // 4)
        return text_cost("openrouter", model or self.get_default_model(), input_tokens, 1000)

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    @property
    def requires_api_key(self) -> bool:
        return True


class GeminiProvider(TextProvider):
    """Google Gemini text generation provider."""

    ALLOWED_MODELS = {item["id"] for item in TEXT_PROVIDERS["gemini"]["models"]}

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("GEMINI_API_KEY", "Gemini", api_key)

    def generate(self, messages, temperature=1.0, model=None) -> TextGenerationResult:
        from google import genai
        from google.genai import types

        model_name = model or self.get_default_model()
        if model_name.startswith(("gemini-1.", "gemini-2.0")):
            raise ValueError("This Gemini model has retired. Choose a current model in Settings or Edit world.")
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=m["content"])],
        ) for m in messages if m["role"] != "system"]
        with genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=120_000)) as client:
            response = client.models.generate_content(
                model=model_name, contents=contents,
                config=types.GenerateContentConfig(system_instruction=system or None, temperature=temperature),
            )
        if not response.text:
            raise ValueError("Gemini returned no story. The request may have been blocked; try a different premise.")
        usage = response.usage_metadata
        cost = self.estimate_cost(messages, model_name)
        if usage and isinstance(usage.prompt_token_count, int):
            cost = text_cost("gemini", model_name, usage.prompt_token_count,
                             (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0))
        return TextGenerationResult(response.text, "gemini", model_name, cost)

    def get_default_model(self) -> str:
        return default_model("gemini")

    def estimate_cost(self, messages, model=None):
        input_tokens = max(1, sum(len(m["content"]) for m in messages) // 4)
        return text_cost("gemini", model or self.get_default_model(), input_tokens, 1000)

    @property
    def provider_name(self) -> str:
        return "Gemini"

    @property
    def requires_api_key(self) -> bool:
        return True


def get_text_provider(
    provider_name: str, api_key: Optional[str] = None
) -> TextProvider:
    """Factory function to get a text provider by name.

    Args:
        provider_name: One of "openai", "together", "huggingface", "groq", "openrouter", "gemini"
        api_key: Optional API key (falls back to environment variables)

    Returns:
        Configured TextProvider instance

    Raises:
        ValueError: If provider_name is not recognized
    """
    if provider_name.lower() in {"local", "ollama"}:
        from .local import LocalProvider
        return LocalProvider(api_key, provider=provider_name.lower())
    providers = {
        "openai": OpenAIProvider,
        "together": TogetherAIProvider,
        "huggingface": HuggingFaceProvider,
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
        "gemini": GeminiProvider,
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown text provider: {provider_name}. "
            f"Available providers: {', '.join(providers.keys())}"
        )

    return provider_class(api_key=api_key)
