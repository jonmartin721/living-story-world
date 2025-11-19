"""Tests for settings management."""
import json
import os

from living_storyworld.settings import (
    UserSettings,
    load_user_settings,
    save_user_settings,
    ensure_api_key_from_settings,
    ensure_provider_api_keys,
    get_api_key_for_provider,
    get_available_text_providers,
)


class TestUserSettings:
    """Test UserSettings dataclass."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = UserSettings()
        assert settings.text_provider == "gemini"
        assert settings.image_provider == "pollinations"
        assert settings.default_style_pack == "storybook-ink"
        assert settings.global_instructions is None

    def test_settings_with_custom_values(self):
        """Test creating settings with custom values."""
        settings = UserSettings(
            text_provider="openai",
            openai_api_key="test-key",
            global_instructions="Be creative",
        )
        assert settings.text_provider == "openai"
        assert settings.openai_api_key == "test-key"
        assert settings.global_instructions == "Be creative"


class TestLoadUserSettings:
    """Test loading user settings."""

    def test_load_nonexistent_file(self, tmp_path, monkeypatch):
        """Test loading when config file doesn't exist."""
        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", tmp_path / "config.json")

        settings = load_user_settings()

        assert isinstance(settings, UserSettings)
        assert settings.text_provider == "gemini"  # Default

    def test_load_valid_config(self, tmp_path, monkeypatch):
        """Test loading valid config file."""
        config_path = tmp_path / "config.json"
        config_data = {
            "text_provider": "openai",
            "openai_api_key": "test-key-123",
            "global_instructions": "Test instructions",
            "default_style_pack": "pixel-rpg",
        }
        config_path.write_text(json.dumps(config_data))

        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        settings = load_user_settings()

        assert settings.text_provider == "openai"
        assert settings.openai_api_key == "test-key-123"
        assert settings.global_instructions == "Test instructions"
        assert settings.default_style_pack == "pixel-rpg"

    def test_load_corrupted_json(self, tmp_path, monkeypatch):
        """Test loading corrupted JSON returns defaults."""
        config_path = tmp_path / "config.json"
        config_path.write_text("{invalid json")

        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        settings = load_user_settings()

        # Should return defaults when JSON is invalid
        assert isinstance(settings, UserSettings)
        assert settings.text_provider == "gemini"

    def test_load_with_extra_fields(self, tmp_path, monkeypatch):
        """Test loading config with unknown fields (should ignore them)."""
        config_path = tmp_path / "config.json"
        config_data = {
            "text_provider": "groq",
            "unknown_field": "should be ignored",
            "another_unknown": 123,
        }
        config_path.write_text(json.dumps(config_data))

        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        settings = load_user_settings()

        assert settings.text_provider == "groq"
        assert not hasattr(settings, "unknown_field")


class TestSaveUserSettings:
    """Test saving user settings."""

    def test_save_new_config(self, tmp_path, monkeypatch):
        """Test saving config when file doesn't exist."""
        config_path = tmp_path / "config.json"
        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        settings = UserSettings(
            text_provider="openai",
            openai_api_key="test-key",
            global_instructions="Custom instructions",
        )

        save_user_settings(settings)

        assert config_path.exists()
        loaded_data = json.loads(config_path.read_text())
        assert loaded_data["text_provider"] == "openai"
        assert loaded_data["openai_api_key"] == "test-key"
        assert loaded_data["global_instructions"] == "Custom instructions"

    def test_save_updates_existing(self, tmp_path, monkeypatch):
        """Test saving updates existing config."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"text_provider": "old"}))

        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        settings = UserSettings(text_provider="new")
        save_user_settings(settings)

        loaded_data = json.loads(config_path.read_text())
        assert loaded_data["text_provider"] == "new"

    def test_save_creates_directory(self, tmp_path, monkeypatch):
        """Test saving creates parent directory if needed."""
        config_path = tmp_path / "subdir" / "config.json"
        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        settings = UserSettings()
        save_user_settings(settings)

        assert config_path.exists()
        assert config_path.parent.is_dir()

    def test_save_roundtrip(self, tmp_path, monkeypatch):
        """Test save and load roundtrip."""
        config_path = tmp_path / "config.json"
        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        original = UserSettings(
            text_provider="together",
            together_api_key="key-123",
            default_preset="noir-mystery",
            reader_font_size="large",
        )

        save_user_settings(original)
        loaded = load_user_settings()

        assert loaded.text_provider == original.text_provider
        assert loaded.together_api_key == original.together_api_key
        assert loaded.default_preset == original.default_preset
        assert loaded.reader_font_size == original.reader_font_size


class TestEnsureAPIKey:
    """Test API key environment management."""

    def test_ensure_api_key_from_env(self, monkeypatch):
        """Test when key is already in environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")

        result = ensure_api_key_from_settings()

        assert result is True
        assert os.environ["OPENAI_API_KEY"] == "env-key"

    def test_ensure_api_key_from_settings(self, tmp_path, monkeypatch):
        """Test loading key from settings into environment."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        settings = UserSettings(openai_api_key="settings-key")

        result = ensure_api_key_from_settings(settings)

        assert result is True
        assert os.environ["OPENAI_API_KEY"] == "settings-key"

    def test_ensure_api_key_missing(self, tmp_path, monkeypatch):
        """Test when no key is available."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))
        monkeypatch.setattr("living_storyworld.settings.CONFIG_PATH", config_path)

        result = ensure_api_key_from_settings()

        assert result is False

    def test_ensure_provider_api_keys(self, monkeypatch):
        """Test loading all provider keys into environment."""
        # Clear environment
        for env_var in ["OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"]:
            monkeypatch.delenv(env_var, raising=False)

        settings = UserSettings(
            openai_api_key="openai-key",
            groq_api_key="groq-key",
            gemini_api_key="gemini-key",
        )

        ensure_provider_api_keys(settings)

        assert os.environ["OPENAI_API_KEY"] == "openai-key"
        assert os.environ["GROQ_API_KEY"] == "groq-key"
        assert os.environ["GEMINI_API_KEY"] == "gemini-key"

    def test_ensure_provider_keys_respects_env(self, monkeypatch):
        """Test that environment keys take precedence."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")

        settings = UserSettings(openai_api_key="settings-key")

        ensure_provider_api_keys(settings)

        # Should not overwrite existing env var
        assert os.environ["OPENAI_API_KEY"] == "env-key"


class TestGetAPIKeyForProvider:
    """Test getting API keys for specific providers."""

    def test_get_key_from_env(self, monkeypatch):
        """Test getting key from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")

        settings = UserSettings(openai_api_key="settings-key")
        key = get_api_key_for_provider("openai", settings)

        # Environment should take precedence
        assert key == "env-key"

    def test_get_key_from_settings(self, monkeypatch):
        """Test getting key from settings when not in env."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        settings = UserSettings(groq_api_key="settings-key")
        key = get_api_key_for_provider("groq", settings)

        assert key == "settings-key"

    def test_get_key_not_found(self, monkeypatch):
        """Test when key is not available."""
        monkeypatch.delenv("TOGETHER_API_KEY", raising=False)

        settings = UserSettings()
        key = get_api_key_for_provider("together", settings)

        assert key is None

    def test_get_key_for_all_providers(self, monkeypatch):
        """Test getting keys for all supported providers."""
        # Clear environment
        for var in ["OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "REPLICATE_API_TOKEN", "FAL_KEY"]:
            monkeypatch.delenv(var, raising=False)

        settings = UserSettings(
            openai_api_key="openai-key",
            groq_api_key="groq-key",
            gemini_api_key="gemini-key",
            together_api_key="together-key",
            huggingface_api_key="hf-key",
            openrouter_api_key="or-key",
            replicate_api_token="replicate-token",
            fal_api_key="fal-key",
        )

        assert get_api_key_for_provider("openai", settings) == "openai-key"
        assert get_api_key_for_provider("groq", settings) == "groq-key"
        assert get_api_key_for_provider("gemini", settings) == "gemini-key"
        assert get_api_key_for_provider("together", settings) == "together-key"
        assert get_api_key_for_provider("huggingface", settings) == "hf-key"
        assert get_api_key_for_provider("openrouter", settings) == "or-key"
        assert get_api_key_for_provider("replicate", settings) == "replicate-token"
        assert get_api_key_for_provider("fal", settings) == "fal-key"

    def test_get_key_unknown_provider(self):
        """Test getting key for unknown provider returns None."""
        settings = UserSettings()
        key = get_api_key_for_provider("unknown-provider", settings)

        assert key is None


class TestGetAvailableTextProviders:
    """Test getting list of available text providers."""

    def test_no_providers_configured(self, monkeypatch):
        """Test when no API keys are configured."""
        for var in ["OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"]:
            monkeypatch.delenv(var, raising=False)

        settings = UserSettings()
        providers = get_available_text_providers(settings)

        assert providers == []

    def test_single_provider(self, monkeypatch):
        """Test with single provider configured."""
        for var in ["OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "TOGETHER_API_KEY", "HUGGINGFACE_API_KEY", "OPENROUTER_API_KEY"]:
            monkeypatch.delenv(var, raising=False)

        settings = UserSettings(
            text_provider="groq",
            groq_api_key="test-key",
        )
        providers = get_available_text_providers(settings)

        assert providers == ["groq"]

    def test_multiple_providers_ordered(self, monkeypatch):
        """Test providers are returned in preferred order."""
        for var in ["OPENAI_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"]:
            monkeypatch.delenv(var, raising=False)

        settings = UserSettings(
            text_provider="openai",
            openai_api_key="openai-key",
            groq_api_key="groq-key",
            gemini_api_key="gemini-key",
        )
        providers = get_available_text_providers(settings)

        # Primary provider first, then free providers, then paid
        assert providers[0] == "openai"  # Primary
        assert "groq" in providers or "gemini" in providers  # Free providers

    def test_free_providers_prioritized(self, monkeypatch):
        """Test free providers come before paid ones."""
        for var in ["OPENAI_API_KEY", "GROQ_API_KEY", "TOGETHER_API_KEY"]:
            monkeypatch.delenv(var, raising=False)

        settings = UserSettings(
            text_provider="together",  # Paid provider as primary
            together_api_key="together-key",
            groq_api_key="groq-key",
            openai_api_key="openai-key",
        )
        providers = get_available_text_providers(settings)

        # Primary first, then groq (free), then openai (paid)
        assert providers[0] == "together"
        groq_idx = providers.index("groq") if "groq" in providers else 999
        openai_idx = providers.index("openai") if "openai" in providers else 999
        if groq_idx < 999 and openai_idx < 999:
            assert groq_idx < openai_idx

    def test_no_duplicates(self, monkeypatch):
        """Test provider list has no duplicates."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        settings = UserSettings(
            text_provider="groq",
            groq_api_key="key",
            gemini_api_key="key2",
        )
        providers = get_available_text_providers(settings)

        assert len(providers) == len(set(providers))  # No duplicates
        assert providers.count("groq") == 1
