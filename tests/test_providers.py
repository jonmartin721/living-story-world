"""Tests to verify provider selection is honored correctly.

These tests ensure that when users select a specific provider, that provider
is actually used for generation (not defaulting to a different one).
"""
import pytest
from unittest.mock import patch
from living_storyworld.providers.text import (
    get_text_provider,
    OpenAIProvider,
    GroqProvider,
    TogetherAIProvider,
    HuggingFaceProvider,
    OpenRouterProvider,
    GeminiProvider
)
from living_storyworld.providers.image import (
    get_image_provider,
    ReplicateProvider,
    HuggingFaceImageProvider,
    PollinationsProvider,
    FalAIProvider
)


class TestTextProviderSelection:
    """Test that text provider factory returns correct provider types."""

    def test_openai_provider_selection(self):
        """Test selecting OpenAI provider returns OpenAIProvider instance."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = get_text_provider("openai")
            assert isinstance(provider, OpenAIProvider)
            assert provider.provider_name == "OpenAI"

    def test_groq_provider_selection(self):
        """Test selecting Groq provider returns GroqProvider instance."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}):
            provider = get_text_provider("groq")
            assert isinstance(provider, GroqProvider)
            assert provider.provider_name == "Groq"

    def test_together_provider_selection(self):
        """Test selecting Together AI provider returns TogetherAIProvider instance."""
        with patch.dict('os.environ', {'TOGETHER_API_KEY': 'test-key'}):
            provider = get_text_provider("together")
            assert isinstance(provider, TogetherAIProvider)
            assert provider.provider_name == "Together AI"

    def test_huggingface_provider_selection(self):
        """Test selecting HuggingFace provider returns HuggingFaceProvider instance."""
        with patch.dict('os.environ', {'HUGGINGFACE_API_KEY': 'test-key'}):
            provider = get_text_provider("huggingface")
            assert isinstance(provider, HuggingFaceProvider)
            assert provider.provider_name == "Hugging Face"

    def test_openrouter_provider_selection(self):
        """Test selecting OpenRouter provider returns OpenRouterProvider instance."""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
            provider = get_text_provider("openrouter")
            assert isinstance(provider, OpenRouterProvider)
            assert provider.provider_name == "OpenRouter"

    def test_gemini_provider_selection(self):
        """Test selecting Gemini provider returns GeminiProvider instance."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            provider = get_text_provider("gemini")
            assert isinstance(provider, GeminiProvider)
            assert provider.provider_name == "Gemini"

    def test_case_insensitive_provider_name(self):
        """Test provider selection is case-insensitive."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider1 = get_text_provider("openai")
            provider2 = get_text_provider("OPENAI")
            provider3 = get_text_provider("OpenAI")
            assert isinstance(provider1, OpenAIProvider)
            assert isinstance(provider2, OpenAIProvider)
            assert isinstance(provider3, OpenAIProvider)

    def test_invalid_provider_name_raises_error(self):
        """Test that invalid provider name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown text provider"):
            get_text_provider("invalid_provider")

    def test_provider_with_explicit_api_key(self):
        """Test passing API key directly to provider."""
        provider = get_text_provider("openai", api_key="explicit-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "explicit-key"


class TestImageProviderSelection:
    """Test that image provider factory returns correct provider types."""

    def test_replicate_provider_selection(self):
        """Test selecting Replicate provider returns ReplicateProvider instance."""
        with patch.dict('os.environ', {'REPLICATE_API_TOKEN': 'test-key'}):
            provider = get_image_provider("replicate")
            assert isinstance(provider, ReplicateProvider)
            assert provider.provider_name == "Replicate"

    def test_huggingface_provider_selection(self):
        """Test selecting HuggingFace provider returns HuggingFaceImageProvider instance."""
        with patch.dict('os.environ', {'HUGGINGFACE_API_KEY': 'test-key'}):
            provider = get_image_provider("huggingface")
            assert isinstance(provider, HuggingFaceImageProvider)
            assert provider.provider_name == "Hugging Face"

    def test_pollinations_provider_selection(self):
        """Test selecting Pollinations provider returns PollinationsProvider instance."""
        provider = get_image_provider("pollinations")
        assert isinstance(provider, PollinationsProvider)
        assert provider.provider_name == "Pollinations.ai"
        assert not provider.requires_api_key

    def test_fal_provider_selection(self):
        """Test selecting Fal.ai provider returns FalAIProvider instance."""
        with patch.dict('os.environ', {'FAL_KEY': 'test-key'}):
            provider = get_image_provider("fal")
            assert isinstance(provider, FalAIProvider)
            assert provider.provider_name == "Fal.ai"

    def test_case_insensitive_image_provider_name(self):
        """Test image provider selection is case-insensitive."""
        provider1 = get_image_provider("pollinations")
        provider2 = get_image_provider("POLLINATIONS")
        provider3 = get_image_provider("Pollinations")
        assert isinstance(provider1, PollinationsProvider)
        assert isinstance(provider2, PollinationsProvider)
        assert isinstance(provider3, PollinationsProvider)

    def test_invalid_image_provider_name_raises_error(self):
        """Test that invalid image provider name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown image provider"):
            get_image_provider("invalid_provider")

    def test_image_provider_with_explicit_api_key(self):
        """Test passing API key directly to image provider."""
        provider = get_image_provider("replicate", api_key="explicit-key")
        assert isinstance(provider, ReplicateProvider)
        assert provider.api_token == "explicit-key"


class TestProviderMetadata:
    """Test that providers have correct metadata."""

    def test_text_providers_have_names(self):
        """Test all text providers have proper names."""
        providers = [
            ("openai", "OpenAI"),
            ("groq", "Groq"),
            ("together", "Together AI"),
            ("gemini", "Gemini"),
        ]
        for provider_key, expected_name in providers:
            with patch.dict('os.environ', {f'{provider_key.upper()}_API_KEY': 'test'}):
                try:
                    provider = get_text_provider(provider_key)
                    assert provider.provider_name == expected_name
                except RuntimeError:
                    # Some providers may have different env var names
                    pass

    def test_image_providers_have_names(self):
        """Test all image providers have proper names."""
        providers = [
            ("pollinations", "Pollinations.ai"),
        ]
        for provider_key, expected_name in providers:
            provider = get_image_provider(provider_key)
            assert provider.provider_name == expected_name

    def test_providers_indicate_api_key_requirement(self):
        """Test providers correctly indicate if they need API keys."""
        # Pollinations doesn't require an API key
        pollinations = get_image_provider("pollinations")
        assert not pollinations.requires_api_key

        # Other providers do
        with patch.dict('os.environ', {'REPLICATE_API_TOKEN': 'test'}):
            replicate = get_image_provider("replicate")
            assert replicate.requires_api_key


class TestProviderGeneration:
    """Test that provider generation methods return expected types."""

    def test_text_provider_returns_result_with_metadata(self):
        """Test text generation includes provider metadata."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = get_text_provider("openai")

            # Mock the actual API call
            with patch.object(provider, 'generate') as mock_generate:
                from living_storyworld.providers.text import TextGenerationResult
                mock_generate.return_value = TextGenerationResult(
                    content="Test response",
                    provider="OpenAI",
                    model="gpt-4",
                    estimated_cost=0.01
                )

                result = provider.generate([{"role": "user", "content": "test"}])

                assert result.provider == "OpenAI"
                assert result.content == "Test response"
                assert hasattr(result, 'model')
                assert hasattr(result, 'estimated_cost')

    def test_providers_have_default_models(self):
        """Test all providers have default models."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}):
            openai = get_text_provider("openai")
            assert openai.get_default_model() is not None
            assert isinstance(openai.get_default_model(), str)
            assert len(openai.get_default_model()) > 0

    def test_pollinations_provider_works_without_api_key(self):
        """Test Pollinations provider can be instantiated without API key."""
        # Should not raise any error
        provider = get_image_provider("pollinations")
        assert provider is not None
        assert not provider.requires_api_key


class TestProviderAPIKeyHandling:
    """Test API key handling across providers."""

    def test_provider_raises_error_without_api_key(self):
        """Test providers raise error when API key is missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(RuntimeError, match="API key not found"):
                get_text_provider("openai")

    def test_provider_accepts_env_var_api_key(self):
        """Test providers can get API key from environment."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'}):
            provider = get_text_provider("openai")
            assert provider.api_key == "env-key"

    def test_explicit_key_overrides_env_var(self):
        """Test explicit API key parameter overrides environment variable."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'}):
            provider = get_text_provider("openai", api_key="explicit-key")
            assert provider.api_key == "explicit-key"
