"""Provider integration tests - testing real code paths with mocked SDK calls."""

import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from living_storyworld.providers.image import (
    FalAIProvider,
    HuggingFaceImageProvider,
    ImageGenerationResult,
    PollinationsProvider,
    ReplicateProvider,
    get_image_provider,
)
from living_storyworld.providers.text import (
    GeminiProvider,
    GroqProvider,
    HuggingFaceProvider,
    OpenAIProvider,
    OpenRouterProvider,
    TextGenerationResult,
    TogetherAIProvider,
    get_text_provider,
)


# ============================================================================
# Text Provider Core Tests
# ============================================================================


class TestTextProviderCore:
    """Test text provider instantiation and basic methods."""

    def test_openai_provider_init(self):
        """OpenAI provider initializes with API key."""
        provider = OpenAIProvider(api_key="sk-test123")
        assert provider.api_key == "sk-test123"
        assert provider.provider_name == "OpenAI"
        assert provider.requires_api_key is True

    def test_groq_provider_init(self):
        """Groq provider initializes."""
        provider = GroqProvider(api_key="gsk-test")
        assert provider.api_key == "gsk-test"
        assert provider.provider_name == "Groq"

    def test_gemini_provider_init(self):
        """Gemini provider initializes."""
        provider = GeminiProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.provider_name == "Gemini"

    def test_together_provider_init(self):
        """Together AI provider initializes."""
        provider = TogetherAIProvider(api_key="test-key")
        assert provider.provider_name == "Together AI"

    def test_huggingface_provider_init(self):
        """HuggingFace provider initializes."""
        provider = HuggingFaceProvider(api_key="hf_test")
        assert provider.provider_name == "Hugging Face"

    def test_openrouter_provider_init(self):
        """OpenRouter provider initializes."""
        provider = OpenRouterProvider(api_key="sk-or-test")
        assert provider.provider_name == "OpenRouter"

    def test_get_text_provider_factory(self):
        """get_text_provider returns correct provider type."""
        provider = get_text_provider("openai", api_key="sk-test")
        assert isinstance(provider, OpenAIProvider)

        provider = get_text_provider("groq", api_key="gsk-test")
        assert isinstance(provider, GroqProvider)

    def test_unknown_text_provider(self):
        """Unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown text provider"):
            get_text_provider("nonexistent")


class TestTextProviderMethods:
    """Test text provider methods."""

    def test_openai_default_model(self):
        """OpenAI has a default model."""
        provider = OpenAIProvider(api_key="sk-test")
        model = provider.get_default_model()
        assert isinstance(model, str)
        assert model in provider.ALLOWED_MODELS

    def test_groq_default_model(self):
        """Groq has a default model."""
        provider = GroqProvider(api_key="gsk-test")
        model = provider.get_default_model()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_gemini_default_model(self):
        """Gemini has a default model."""
        provider = GeminiProvider(api_key="test")
        model = provider.get_default_model()
        assert "gemini" in model.lower()

    def test_openai_cost_estimation(self):
        """OpenAI estimates costs."""
        provider = OpenAIProvider(api_key="sk-test")
        messages = [{"role": "user", "content": "test"}]
        cost = provider.estimate_cost(messages, "gpt-4o-mini")
        assert isinstance(cost, float)
        assert cost >= 0

    def test_free_providers_zero_cost(self):
        """Free providers return zero cost."""
        gemini = GeminiProvider(api_key="test")
        messages = [{"role": "user", "content": "test"}]
        assert gemini.estimate_cost(messages) == 0.0

        # Groq is technically paid but very cheap
        groq = GroqProvider(api_key="gsk-test")
        cost = groq.estimate_cost(messages)
        assert isinstance(cost, float)
        assert cost >= 0

    def test_together_cost_estimation(self):
        """Together AI estimates costs."""
        provider = TogetherAIProvider(api_key="test")
        messages = [{"role": "user", "content": "test"}]
        cost = provider.estimate_cost(messages)
        assert isinstance(cost, float)
        assert cost >= 0


class TestTextProviderValidation:
    """Test text provider input validation."""

    def test_temperature_validation(self):
        """Temperature must be in valid range."""
        provider = OpenAIProvider(api_key="sk-test")

        with pytest.raises(ValueError, match="Temperature must be between"):
            provider.generate([{"role": "user", "content": "test"}], temperature=3.0)

        with pytest.raises(ValueError, match="Temperature must be between"):
            provider.generate([{"role": "user", "content": "test"}], temperature=-0.5)

    def test_invalid_model_rejection(self):
        """Invalid models are rejected."""
        provider = OpenAIProvider(api_key="sk-test")

        from living_storyworld.exceptions import InvalidModelError

        with pytest.raises(InvalidModelError):
            provider.generate(
                [{"role": "user", "content": "test"}], model="not-real-model-xyz"
            )


class TestTextProviderGeneration:
    """Test text generation with mocked SDK calls."""

    def test_openai_generate_success(self):
        """OpenAI provider generates text successfully."""
        provider = OpenAIProvider(api_key="sk-test")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Generated text"))]

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = provider.generate([{"role": "user", "content": "test"}])

            assert isinstance(result, TextGenerationResult)
            assert result.content == "Generated text"
            assert result.provider == "openai"
            # Model will be the default from get_default_model()
            assert result.model in provider.ALLOWED_MODELS
            assert result.estimated_cost >= 0

    def test_gemini_generate_success(self):
        """Gemini provider generates text."""
        provider = GeminiProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.text = "Gemini generated text"

        with patch("google.generativeai.configure"), patch(
            "google.generativeai.GenerativeModel"
        ) as mock_model_class:
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            result = provider.generate([{"role": "user", "content": "test"}])

            assert result.content == "Gemini generated text"
            assert result.provider == "gemini"

    def test_groq_generate_success(self):
        """Groq provider generates text."""
        pytest.importorskip("groq")
        provider = GroqProvider(api_key="gsk-test")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Groq response"))]

        with patch("groq.Groq") as mock_groq:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_groq.return_value = mock_client

            result = provider.generate([{"role": "user", "content": "test"}])

            assert result.content == "Groq response"
            assert result.provider == "groq"


# ============================================================================
# Image Provider Core Tests
# ============================================================================


class TestImageProviderCore:
    """Test image provider instantiation."""

    def test_pollinations_provider_init(self):
        """Pollinations provider works without API key."""
        provider = PollinationsProvider()
        assert provider.provider_name == "Pollinations.ai"
        assert provider.requires_api_key is False

    def test_replicate_provider_init(self):
        """Replicate provider initializes."""
        provider = ReplicateProvider(api_key="r8_test")
        assert provider.api_token == "r8_test"  # Replicate uses api_token internally
        assert provider.provider_name == "Replicate"
        assert provider.requires_api_key is True

    def test_huggingface_image_provider_init(self):
        """HuggingFace image provider initializes."""
        provider = HuggingFaceImageProvider(api_key="hf_test")
        assert provider.provider_name == "Hugging Face"

    def test_fal_provider_init(self):
        """Fal.ai provider initializes."""
        provider = FalAIProvider(api_key="test-key")
        assert provider.provider_name == "Fal.ai"

    def test_get_image_provider_factory(self):
        """get_image_provider returns correct type."""
        provider = get_image_provider("pollinations")
        assert isinstance(provider, PollinationsProvider)

        provider = get_image_provider("replicate", api_key="r8_test")
        assert isinstance(provider, ReplicateProvider)

    def test_unknown_image_provider(self):
        """Unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown image provider"):
            get_image_provider("nonexistent")


class TestImageProviderMethods:
    """Test image provider methods."""

    def test_pollinations_default_model(self):
        """Pollinations has a default model."""
        provider = PollinationsProvider()
        model = provider.get_default_model()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_replicate_default_model(self):
        """Replicate has a default model."""
        provider = ReplicateProvider(api_key="r8_test")
        model = provider.get_default_model()
        assert "flux" in model.lower()

    def test_pollinations_aspect_ratio_conversion(self):
        """Pollinations converts aspect ratios correctly."""
        provider = PollinationsProvider()

        # Test various aspect ratios
        width, height = provider._aspect_ratio_to_dimensions("1:1")
        assert width == 1024
        assert height == 1024

        width, height = provider._aspect_ratio_to_dimensions("16:9")
        assert width > height
        assert isinstance(width, int)
        assert isinstance(height, int)

        width, height = provider._aspect_ratio_to_dimensions("9:16")
        assert height > width


class TestImageProviderGeneration:
    """Test image generation with mocked calls."""

    def test_pollinations_generate(self, tmp_path):
        """Pollinations generates images via URL."""
        provider = PollinationsProvider()
        output_path = tmp_path / "test.png"

        # Minimal valid 1x1 PNG image (67 bytes)
        valid_png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/png", "content-length": str(len(valid_png_bytes))}
        mock_response.iter_content = lambda chunk_size: [valid_png_bytes]

        with patch("requests.get", return_value=mock_response):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result = provider.generate("A sunset", output_path, aspect_ratio="16:9")

            assert isinstance(result, ImageGenerationResult)
            assert result.image_path == output_path
            assert result.provider == "pollinations"
            assert result.estimated_cost == 0.0  # Free provider

    @pytest.mark.skip(reason="Complex mocking of Replicate SDK - tested via integration")
    def test_replicate_generate(self, tmp_path):
        """Replicate generates images."""
        provider = ReplicateProvider(api_key="r8_test")
        output_path = tmp_path / "test.png"

        mock_output = ["https://example.com/image.png"]

        with patch("replicate.run") as mock_run, patch(
            "living_storyworld.image.safe_download_image"
        ) as mock_download:
            mock_run.return_value = mock_output
            mock_download.return_value = output_path
            output_path.write_bytes(b"fake image")

            result = provider.generate("A sunset", output_path)

            assert isinstance(result, ImageGenerationResult)
            assert result.image_path == output_path
            assert result.provider == "replicate"

    @pytest.mark.skip(reason="Complex mocking of HuggingFace API - tested via integration")
    def test_huggingface_generate(self, tmp_path):
        """HuggingFace generates images."""
        provider = HuggingFaceImageProvider(api_key="hf_test")
        output_path = tmp_path / "test.png"

        with patch("requests.post") as mock_post, patch(
            "living_storyworld.image.safe_download_image"
        ) as mock_download:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"fake image data"
            mock_post.return_value = mock_response
            mock_download.return_value = output_path
            output_path.write_bytes(b"fake image")

            result = provider.generate("A sunset", output_path)

            assert isinstance(result, ImageGenerationResult)
            assert result.provider == "huggingface"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestProviderErrorHandling:
    """Test provider error handling."""

    def test_missing_api_key_error(self):
        """Providers raise error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises((ValueError, RuntimeError), match="API key"):
                OpenAIProvider()

            with pytest.raises((ValueError, RuntimeError), match="API"):
                ReplicateProvider()

    def test_sdk_import_error_handling(self):
        """Providers handle missing SDK gracefully."""
        provider = OpenAIProvider(api_key="sk-test")

        # Patch at import level to simulate missing SDK
        import sys
        with patch.dict(sys.modules, {"openai": None}):
            with pytest.raises(RuntimeError, match="OpenAI SDK not installed"):
                provider.generate([{"role": "user", "content": "test"}])

    def test_api_error_handling(self):
        """Providers handle API errors."""
        provider = OpenAIProvider(api_key="sk-test")

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client

            with pytest.raises(Exception, match="API Error"):
                provider.generate([{"role": "user", "content": "test"}])


# ============================================================================
# Result Object Tests
# ============================================================================


class TestResultObjects:
    """Test result object creation."""

    def test_text_generation_result(self):
        """TextGenerationResult can be created."""
        result = TextGenerationResult(
            content="Generated text",
            provider="openai",
            model="gpt-4o-mini",
            estimated_cost=0.001,
        )
        assert result.content == "Generated text"
        assert result.provider == "openai"
        assert result.model == "gpt-4o-mini"
        assert result.estimated_cost == 0.001

    def test_image_generation_result(self):
        """ImageGenerationResult can be created."""
        result = ImageGenerationResult(
            image_path=Path("/tmp/image.png"),
            provider="pollinations",
            model="flux-schnell",
            estimated_cost=0.0,
            cached=False,
        )
        assert result.image_path == Path("/tmp/image.png")
        assert result.provider == "pollinations"
        assert result.model == "flux-schnell"
        assert result.estimated_cost == 0.0
        assert result.cached is False
