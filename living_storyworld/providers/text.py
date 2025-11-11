"""Text generation provider abstractions and implementations."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


def _init_api_key(env_var: str, provider_name: str, api_key: Optional[str] = None) -> str:
    """Initialize API key from parameter or environment.

    Args:
        env_var: Environment variable name to check
        provider_name: Human-readable provider name for error messages
        api_key: Optional API key passed directly

    Returns:
        The API key

    Raises:
        RuntimeError: If no API key is found
    """
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
    estimated_cost: float  # in USD


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
    def estimate_cost(self, messages: list[dict[str, str]], model: Optional[str] = None) -> float:
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
            raise RuntimeError("OpenAI SDK not installed. Run: pip install openai>=1.0") from e

        base_url = self.get_base_url()
        if base_url:
            client = OpenAI(api_key=self.api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=self.api_key)

        model_name = model or self.get_default_model()

        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore
            temperature=temperature,
        )

        content = resp.choices[0].message.content or ""
        cost = self.estimate_cost(messages, model_name)

        return TextGenerationResult(
            content=content,
            provider=self.provider_name.lower(),
            model=model_name,
            estimated_cost=cost,
        )


class OpenAIProvider(TextProvider):
    """OpenAI text generation provider."""

    ALLOWED_MODELS = {
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
        # VALIDATION: Temperature bounds
        if not 0.0 <= temperature <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")

        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("OpenAI SDK not installed. Run: pip install openai>=1.0") from e

        client = OpenAI(api_key=self.api_key)
        model_name = model or self.get_default_model()

        # VALIDATION: Model name
        if model_name not in self.ALLOWED_MODELS:
            raise ValueError(
                f"Unknown OpenAI model: {model_name}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_MODELS))}"
            )

        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore
            temperature=temperature,
        )

        content = resp.choices[0].message.content or ""
        cost = self.estimate_cost(messages, model_name)

        return TextGenerationResult(
            content=content,
            provider="openai",
            model=model_name,
            estimated_cost=cost,
        )

    def get_default_model(self) -> str:
        return "gpt-5-mini"

    def estimate_cost(self, messages: list[dict[str, str]], model: Optional[str] = None) -> float:
        """Rough cost estimate based on typical chapter length."""
        # Very rough approximation: ~1000 input tokens, ~1000 output tokens
        # gpt-4o-mini: $0.150/1M input, $0.600/1M output
        model_name = model or self.get_default_model()
        if "gpt-4o-mini" in model_name:
            return (1000 * 0.150 / 1_000_000) + (1000 * 0.600 / 1_000_000)
        elif "gpt-4o" in model_name:
            # gpt-4o: $2.50/1M input, $10.00/1M output
            return (1000 * 2.50 / 1_000_000) + (1000 * 10.00 / 1_000_000)
        return 0.01  # Default fallback

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
        return "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

    def estimate_cost(self, messages: list[dict[str, str]], model: Optional[str] = None) -> float:
        """Together AI pricing varies by model."""
        model_name = model or self.get_default_model()
        # Llama 3.1 70B: $0.88/1M input, $0.88/1M output (approximate)
        if "70B" in model_name or "70b" in model_name:
            return (1000 * 0.88 / 1_000_000) + (1000 * 0.88 / 1_000_000)
        # Smaller models are cheaper
        return 0.002

    @property
    def provider_name(self) -> str:
        return "Together AI"

    @property
    def requires_api_key(self) -> bool:
        return True


class HuggingFaceProvider(TextProvider):
    """Hugging Face Inference API provider.

    Works with or without API key:
    - With API key: Higher rate limits
    - Without API key: Free tier with lower rate limits
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("HUGGINGFACE_API_KEY")
        # API key is optional - free tier is available without one
        self.using_free_tier = not self.api_key

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> TextGenerationResult:
        import requests

        model_name = model or self.get_default_model()
        api_url = f"https://api-inference.huggingface.co/models/{model_name}"

        # Convert messages to prompt (Hugging Face expects text prompt)
        prompt = self._messages_to_prompt(messages)

        # Build headers - include auth only if we have an API key
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": 1000,
                "return_full_text": False,
            }
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)

            # Handle rate limiting
            if response.status_code == 429:
                if self.using_free_tier:
                    raise RuntimeError(
                        "Rate limit reached on HuggingFace free tier. "
                        "Please wait a few minutes or add a HuggingFace API key in Settings for higher limits. "
                        "Get a free key at: https://huggingface.co/settings/tokens"
                    )
                else:
                    raise RuntimeError(
                        "Rate limit reached on HuggingFace API. Please wait a moment and try again."
                    )

            # Handle model loading
            if response.status_code == 503:
                error_data = response.json() if response.content else {}
                if "loading" in str(error_data).lower():
                    raise RuntimeError(
                        f"Model {model_name} is loading. Please wait 20-30 seconds and try again. "
                        "HuggingFace models need to warm up on first use."
                    )
                raise RuntimeError(f"HuggingFace service temporarily unavailable: {error_data}")

            response.raise_for_status()

            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get("generated_text", "")
            else:
                content = result.get("generated_text", "")

            cost = self.estimate_cost(messages, model_name)

            return TextGenerationResult(
                content=content,
                provider="huggingface" + (" (free)" if self.using_free_tier else ""),
                model=model_name,
                estimated_cost=cost,
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                "HuggingFace API request timed out. The model may be slow to respond. Try again in a moment."
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"HuggingFace API error: {str(e)}")

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """Convert chat messages to a single prompt string."""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        return "\n\n".join(prompt_parts) + "\n\nAssistant:"

    def get_default_model(self) -> str:
        return "mistralai/Mistral-7B-Instruct-v0.3"

    def estimate_cost(self, messages: list[dict[str, str]], model: Optional[str] = None) -> float:
        """Hugging Face Inference API is free (rate-limited)."""
        return 0.0

    @property
    def provider_name(self) -> str:
        return "Hugging Face"

    @property
    def requires_api_key(self) -> bool:
        return False  # API key is optional - works on free tier without one


class GroqProvider(OpenAICompatibleProvider):
    """Groq text generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("GROQ_API_KEY", "Groq", api_key)

    def get_base_url(self) -> Optional[str]:
        return "https://api.groq.com/openai/v1"

    def get_default_model(self) -> str:
        return "llama-3.3-70b-versatile"

    def estimate_cost(self, messages: list[dict[str, str]], model: Optional[str] = None) -> float:
        """Groq has free tier with rate limits."""
        # Groq charges per token: $0.59/1M input, $0.79/1M output for Llama 3.3 70B
        model_name = model or self.get_default_model()
        if "70b" in model_name.lower():
            return (1000 * 0.59 / 1_000_000) + (1000 * 0.79 / 1_000_000)
        # Smaller models are cheaper/free
        return 0.001

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
        return "z-ai/glm-4.6"  # GLM-4.6 with 200K context, advanced reasoning and coding

    def estimate_cost(self, messages: list[dict[str, str]], model: Optional[str] = None) -> float:
        """OpenRouter pricing varies by model."""
        model_name = model or self.get_default_model()
        # GLM-4.6: ~$0.15/1M input, ~$0.60/1M output (15% cheaper than GLM-4-Plus)
        if "glm-4.6" in model_name.lower():
            return (1000 * 0.15 / 1_000_000) + (1000 * 0.60 / 1_000_000)
        # GLM-4-Plus: ~$0.50/1M input, ~$2.00/1M output
        elif "glm-4" in model_name.lower():
            return (1000 * 0.50 / 1_000_000) + (1000 * 2.00 / 1_000_000)
        # Other models vary
        return 0.003

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    @property
    def requires_api_key(self) -> bool:
        return True


class GeminiProvider(TextProvider):
    """Google Gemini text generation provider."""

    ALLOWED_MODELS = {
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = _init_api_key("GEMINI_API_KEY", "Gemini", api_key)

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> TextGenerationResult:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)

        model_name = model or self.get_default_model()
        if model_name not in self.ALLOWED_MODELS:
            raise ValueError(
                f"Unknown Gemini model: {model_name}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_MODELS))}"
            )

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({
                "role": role,
                "parts": [msg["content"]]
            })

        model_instance = genai.GenerativeModel(model_name)

        # Gemini doesn't support separate system/user like OpenAI
        # If first message is system, prepend it to first user message
        if messages and messages[0]["role"] == "system":
            system_content = messages[0]["content"]
            if len(gemini_messages) > 1:
                gemini_messages[1]["parts"][0] = f"{system_content}\n\n{gemini_messages[1]['parts'][0]}"
                gemini_messages = gemini_messages[1:]  # Remove the system message

        response = model_instance.generate_content(
            gemini_messages,
            generation_config={
                "temperature": temperature,
            }
        )

        content = response.text
        cost = self.estimate_cost(messages, model_name)

        return TextGenerationResult(
            content=content,
            provider="gemini",
            model=model_name,
            estimated_cost=cost,
        )

    def get_default_model(self) -> str:
        return "gemini-2.5-flash"

    def estimate_cost(self, messages: list[dict[str, str]], model: Optional[str] = None) -> float:
        """Gemini Flash is free for up to 15 requests/minute, 1500 requests/day."""
        # Flash models are free tier
        model_name = model or self.get_default_model()
        if "flash" in model_name.lower():
            return 0.0  # Free tier
        # Pro models have costs but still very cheap
        return (1000 * 1.25 / 1_000_000) + (1000 * 5.00 / 1_000_000)

    @property
    def provider_name(self) -> str:
        return "Gemini"

    @property
    def requires_api_key(self) -> bool:
        return True


def get_text_provider(provider_name: str, api_key: Optional[str] = None) -> TextProvider:
    """Factory function to get a text provider by name.

    Args:
        provider_name: One of "openai", "together", "huggingface", "groq", "openrouter", "gemini"
        api_key: Optional API key (falls back to environment variables)

    Returns:
        Configured TextProvider instance

    Raises:
        ValueError: If provider_name is not recognized
    """
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
