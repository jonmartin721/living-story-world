"""Text generation provider abstractions and implementations."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


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


class OpenAIProvider(TextProvider):
    """OpenAI text generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or pass api_key parameter.")

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
            provider="openai",
            model=model_name,
            estimated_cost=cost,
        )

    def get_default_model(self) -> str:
        return "gpt-4o-mini"

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


class TogetherAIProvider(TextProvider):
    """Together AI text generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        if not self.api_key:
            raise RuntimeError("Together AI API key not found. Set TOGETHER_API_KEY environment variable or pass api_key parameter.")

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> TextGenerationResult:
        try:
            from openai import OpenAI  # Together AI uses OpenAI SDK
        except ImportError as e:
            raise RuntimeError("OpenAI SDK not installed. Run: pip install openai>=1.0") from e

        # Together AI is OpenAI-compatible
        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.together.xyz/v1",
        )
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
            provider="together",
            model=model_name,
            estimated_cost=cost,
        )

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
    """Hugging Face Inference API provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Hugging Face API key not found. Set HUGGINGFACE_API_KEY environment variable or pass api_key parameter.")

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

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": 1000,
                "return_full_text": False,
            }
        }

        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            content = result[0].get("generated_text", "")
        else:
            content = result.get("generated_text", "")

        cost = self.estimate_cost(messages, model_name)

        return TextGenerationResult(
            content=content,
            provider="huggingface",
            model=model_name,
            estimated_cost=cost,
        )

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
        return True


class GroqProvider(TextProvider):
    """Groq text generation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("Groq API key not found. Set GROQ_API_KEY environment variable or pass api_key parameter.")

    def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> TextGenerationResult:
        try:
            from openai import OpenAI  # Groq uses OpenAI SDK
        except ImportError as e:
            raise RuntimeError("OpenAI SDK not installed. Run: pip install openai>=1.0") from e

        # Groq is OpenAI-compatible
        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1",
        )
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
            provider="groq",
            model=model_name,
            estimated_cost=cost,
        )

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


def get_text_provider(provider_name: str, api_key: Optional[str] = None) -> TextProvider:
    """Factory function to get a text provider by name.

    Args:
        provider_name: One of "openai", "together", "huggingface", "groq"
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
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown text provider: {provider_name}. "
            f"Available providers: {', '.join(providers.keys())}"
        )

    return provider_class(api_key=api_key)
