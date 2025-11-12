"""Tests to verify all required packages and modules can be imported.

These tests ensure that PyInstaller bundles include all necessary dependencies.
"""
import sys
import importlib


class TestCoreModules:
    """Test that all core application modules can be imported."""

    def test_main_module(self):
        """Test main entry point can be imported."""
        import living_storyworld
        assert living_storyworld is not None

    def test_cli_module(self):
        """Test CLI module can be imported."""
        import living_storyworld.cli
        assert living_storyworld.cli is not None

    def test_webapp_module(self):
        """Test webapp module can be imported."""
        import living_storyworld.webapp
        assert living_storyworld.webapp is not None

    def test_desktop_module(self):
        """Test desktop module can be imported."""
        import living_storyworld.desktop
        assert living_storyworld.desktop is not None

    def test_generator_module(self):
        """Test generator module can be imported."""
        import living_storyworld.generator
        assert living_storyworld.generator is not None

    def test_world_module(self):
        """Test world module can be imported."""
        import living_storyworld.world
        assert living_storyworld.world is not None

    def test_storage_module(self):
        """Test storage module can be imported."""
        import living_storyworld.storage
        assert living_storyworld.storage is not None

    def test_models_module(self):
        """Test models module can be imported."""
        import living_storyworld.models
        assert living_storyworld.models is not None

    def test_config_module(self):
        """Test config module can be imported."""
        import living_storyworld.config
        assert living_storyworld.config is not None

    def test_presets_module(self):
        """Test presets module can be imported."""
        import living_storyworld.presets
        assert living_storyworld.presets is not None

    def test_settings_module(self):
        """Test settings module can be imported."""
        import living_storyworld.settings
        assert living_storyworld.settings is not None

    def test_image_module(self):
        """Test image module can be imported."""
        import living_storyworld.image
        assert living_storyworld.image is not None

    def test_wizard_module(self):
        """Test wizard module can be imported."""
        import living_storyworld.wizard
        assert living_storyworld.wizard is not None

    def test_tui_module(self):
        """Test TUI module can be imported."""
        import living_storyworld.tui
        assert living_storyworld.tui is not None


class TestAPIModules:
    """Test that all API modules can be imported."""

    def test_api_package(self):
        """Test API package can be imported."""
        import living_storyworld.api
        assert living_storyworld.api is not None

    def test_api_worlds(self):
        """Test API worlds module can be imported."""
        import living_storyworld.api.worlds
        assert living_storyworld.api.worlds is not None

    def test_api_chapters(self):
        """Test API chapters module can be imported."""
        import living_storyworld.api.chapters
        assert living_storyworld.api.chapters is not None

    def test_api_images(self):
        """Test API images module can be imported."""
        import living_storyworld.api.images
        assert living_storyworld.api.images is not None

    def test_api_settings(self):
        """Test API settings module can be imported."""
        import living_storyworld.api.settings
        assert living_storyworld.api.settings is not None

    def test_api_generate(self):
        """Test API generate module can be imported."""
        import living_storyworld.api.generate
        assert living_storyworld.api.generate is not None

    def test_api_dependencies(self):
        """Test API dependencies module can be imported."""
        import living_storyworld.api.dependencies
        assert living_storyworld.api.dependencies is not None


class TestProviderModules:
    """Test that all provider modules can be imported."""

    def test_providers_package(self):
        """Test providers package can be imported."""
        import living_storyworld.providers
        assert living_storyworld.providers is not None

    def test_text_providers(self):
        """Test text providers module can be imported."""
        import living_storyworld.providers.text
        assert living_storyworld.providers.text is not None

    def test_image_providers(self):
        """Test image providers module can be imported."""
        import living_storyworld.providers.image
        assert living_storyworld.providers.image is not None


class TestRequiredPackages:
    """Test that all required third-party packages are available."""

    def test_fastapi_available(self):
        """Test FastAPI is available."""
        import fastapi
        assert fastapi is not None

    def test_uvicorn_available(self):
        """Test Uvicorn is available."""
        import uvicorn
        assert uvicorn is not None

    def test_uvicorn_logging(self):
        """Test Uvicorn logging module."""
        import uvicorn.logging
        assert uvicorn.logging is not None

    def test_uvicorn_protocols(self):
        """Test Uvicorn protocols."""
        import uvicorn.protocols.http
        import uvicorn.protocols.websockets
        assert uvicorn.protocols.http is not None
        assert uvicorn.protocols.websockets is not None

    def test_requests_available(self):
        """Test requests is available."""
        import requests
        assert requests is not None

    def test_httpx_available(self):
        """Test httpx is available."""
        import httpx
        assert httpx is not None

    def test_openai_available(self):
        """Test OpenAI SDK is available."""
        import openai
        assert openai is not None

    def test_replicate_available(self):
        """Test Replicate SDK is available."""
        import replicate
        assert replicate is not None

    def test_rich_available(self):
        """Test Rich is available."""
        import rich
        assert rich is not None

    def test_textual_available(self):
        """Test Textual is available."""
        import textual
        assert textual is not None

    def test_webview_available(self):
        """Test PyWebView is available."""
        import webview
        assert webview is not None


class TestPlatformSpecific:
    """Test platform-specific dependencies."""

    def test_windows_dependencies(self):
        """Test Windows-specific dependencies if on Windows."""
        if sys.platform != 'win32':
            return

        try:
            import pythoncom
            import pywintypes
            import win32com.client
            assert pythoncom is not None
            assert pywintypes is not None
            assert win32com.client is not None
        except ImportError as e:
            raise AssertionError(f"Windows dependencies missing: {e}")


class TestProviderClasses:
    """Test that all provider classes can be instantiated."""

    def test_text_provider_classes_available(self):
        """Test all text provider classes exist."""
        from living_storyworld.providers.text import (
            TextProvider,
            OpenAIProvider,
            GroqProvider,
            TogetherAIProvider,
            HuggingFaceProvider,
            OpenRouterProvider,
            GeminiProvider
        )
        assert TextProvider is not None
        assert OpenAIProvider is not None
        assert GroqProvider is not None
        assert TogetherAIProvider is not None
        assert HuggingFaceProvider is not None
        assert OpenRouterProvider is not None
        assert GeminiProvider is not None

    def test_image_provider_classes_available(self):
        """Test all image provider classes exist."""
        from living_storyworld.providers.image import (
            ImageProvider,
            ReplicateProvider,
            HuggingFaceImageProvider,
            PollinationsProvider,
            FalAIProvider
        )
        assert ImageProvider is not None
        assert ReplicateProvider is not None
        assert HuggingFaceImageProvider is not None
        assert PollinationsProvider is not None
        assert FalAIProvider is not None
