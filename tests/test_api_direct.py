"""
Direct API function tests (bypass FastAPI routing).

Tests API route functions by importing and calling them directly with mocked
dependencies, avoiding FastAPI TestClient patch context issues.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

# API modules to test
from living_storyworld.api import chapters
from living_storyworld.api.chapters import (
    ChapterGenerateRequest,
    ChoiceSelectionRequest,
    get_cached_settings,
    get_chapter_content,
    select_choice,
    start_chapter_generation,
)
from living_storyworld.api.dependencies import (
    get_validated_world_slug,
    get_world_data,
    load_world_async,
)
from living_storyworld.api.generate import (
    _generate_random_theme,
    _generate_random_world,
    generate_theme,
    generate_world,
)
from living_storyworld.api.images import ImageGenerateRequest, generate_image
from living_storyworld.api.settings import (
    SettingsUpdateRequest,
    check_api_key_exists,
    clear_api_keys,
    get_settings,
    set_api_key,
    update_settings,
    validate_api_key,
)
from living_storyworld.api.worlds import (
    WorldCreateRequest,
    WorldUpdateRequest,
    create_world,
    delete_world,
    get_world,
    list_worlds,
    set_current,
    update_world,
)
from living_storyworld.models import Chapter, Choice, WorldConfig, WorldState
from living_storyworld.settings import UserSettings


# ============================================================================
# API Dependencies Tests
# ============================================================================


class TestAPIDependencies:
    """Test api/dependencies.py functions."""

    def test_get_validated_world_slug_success(self, tmp_path):
        """Valid slug and existing world returns validated slug and path."""
        worlds_dir = tmp_path / "worlds"
        worlds_dir.mkdir()
        (worlds_dir / "test-world").mkdir()

        with patch("living_storyworld.api.dependencies.WORLDS_DIR", worlds_dir):
            slug, path = get_validated_world_slug("test-world")
            assert slug == "test-world"
            assert path == worlds_dir / "test-world"

    def test_get_validated_world_slug_invalid_slug(self, tmp_path):
        """Invalid slug raises HTTPException 400."""
        with patch("living_storyworld.api.dependencies.WORLDS_DIR", tmp_path):
            with pytest.raises(HTTPException) as exc:
                get_validated_world_slug("../invalid")
            assert exc.value.status_code == 400

    def test_get_validated_world_slug_not_found(self, tmp_path):
        """Non-existent world raises HTTPException 404."""
        with patch("living_storyworld.api.dependencies.WORLDS_DIR", tmp_path):
            with pytest.raises(HTTPException) as exc:
                get_validated_world_slug("nonexistent")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_load_world_async(self, sample_world_config, sample_world_state):
        """load_world_async runs load_world in executor."""
        mock_dirs = {"base": Path("/fake")}

        with patch("living_storyworld.api.dependencies.load_world") as mock_load:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)
            cfg, state, dirs = await load_world_async("test-world")

            assert cfg == sample_world_config
            assert state == sample_world_state
            assert dirs == mock_dirs
            mock_load.assert_called_once_with("test-world")

    @pytest.mark.asyncio
    async def test_get_world_data_success(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """get_world_data validates and loads world."""
        worlds_dir = tmp_path / "worlds"
        worlds_dir.mkdir()
        (worlds_dir / "test-world").mkdir()
        mock_dirs = {"base": worlds_dir / "test-world"}

        with patch("living_storyworld.api.dependencies.WORLDS_DIR", worlds_dir), patch(
            "living_storyworld.api.dependencies.load_world"
        ) as mock_load:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)
            slug, cfg, state, dirs = await get_world_data("test-world")

            assert slug == "test-world"
            assert cfg == sample_world_config
            assert state == sample_world_state


# ============================================================================
# Settings API Tests
# ============================================================================


class TestSettingsAPI:
    """Test api/settings.py functions."""

    def test_validate_api_key_success(self):
        """Valid API key is accepted."""
        key = validate_api_key("sk-1234567890abcdef12345", "OpenAI", prefix="sk-")
        assert key == "sk-1234567890abcdef12345"

    def test_validate_api_key_strips_whitespace(self):
        """API key whitespace is stripped."""
        key = validate_api_key("  sk-1234567890abcdef12345  ", "OpenAI", prefix="sk-")
        assert key == "sk-1234567890abcdef12345"

    def test_validate_api_key_empty(self):
        """Empty API key raises HTTPException."""
        with pytest.raises(HTTPException) as exc:
            validate_api_key("", "OpenAI")
        assert exc.value.status_code == 400
        assert "cannot be empty" in exc.value.detail

    def test_validate_api_key_too_short(self):
        """Too-short API key raises HTTPException."""
        with pytest.raises(HTTPException) as exc:
            validate_api_key("short", "OpenAI", min_length=20)
        assert exc.value.status_code == 400
        assert "too short" in exc.value.detail

    def test_validate_api_key_too_long(self):
        """Too-long API key raises HTTPException."""
        with pytest.raises(HTTPException) as exc:
            validate_api_key("x" * 300, "OpenAI", max_length=200)
        assert exc.value.status_code == 400
        assert "too long" in exc.value.detail

    def test_validate_api_key_wrong_prefix(self):
        """Wrong prefix raises HTTPException."""
        with pytest.raises(HTTPException) as exc:
            validate_api_key("pk-1234567890abcdef12345", "OpenAI", prefix="sk-")
        assert exc.value.status_code == 400
        assert "must start with" in exc.value.detail

    def test_check_api_key_exists_in_settings(self):
        """check_api_key_exists returns True if key in settings."""
        settings = UserSettings(openai_api_key="sk-test123")
        assert check_api_key_exists(settings, "openai_api_key", "OPENAI_API_KEY")

    def test_check_api_key_exists_in_env(self):
        """check_api_key_exists returns True if key in environment."""
        settings = UserSettings()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            assert check_api_key_exists(settings, "openai_api_key", "OPENAI_API_KEY")

    def test_check_api_key_exists_not_found(self):
        """check_api_key_exists returns False if key not found."""
        settings = UserSettings()
        with patch.dict(os.environ, {}, clear=True):
            assert not check_api_key_exists(settings, "openai_api_key", "OPENAI_API_KEY")

    def test_set_api_key_success(self):
        """set_api_key updates settings and environment."""
        settings = UserSettings()
        set_api_key(
            settings,
            "sk-1234567890abcdef12345",
            "openai_api_key",
            "OPENAI_API_KEY",
            "OpenAI",
            "sk-",
        )
        assert settings.openai_api_key == "sk-1234567890abcdef12345"
        assert os.environ["OPENAI_API_KEY"] == "sk-1234567890abcdef12345"

    def test_set_api_key_none_value(self):
        """set_api_key with None does nothing."""
        settings = UserSettings()
        set_api_key(settings, None, "openai_api_key", "OPENAI_API_KEY", "OpenAI", "sk-")
        assert settings.openai_api_key is None

    def test_set_api_key_empty_string(self):
        """set_api_key with empty string does nothing."""
        settings = UserSettings()
        set_api_key(settings, "", "openai_api_key", "OPENAI_API_KEY", "OpenAI", "sk-")
        assert settings.openai_api_key is None

    @pytest.mark.asyncio
    async def test_get_settings(self):
        """get_settings returns masked settings."""
        mock_settings = UserSettings(
            text_provider="openai",
            image_provider="replicate",
            openai_api_key="sk-test123",
        )

        with patch(
            "living_storyworld.api.settings.load_user_settings", return_value=mock_settings
        ):
            response = await get_settings()

            assert response.text_provider == "openai"
            assert response.image_provider == "replicate"
            assert response.has_openai_key is True
            assert response.has_together_key is False

    @pytest.mark.asyncio
    async def test_update_settings_providers(self):
        """update_settings updates provider selections."""
        mock_settings = UserSettings()

        with patch(
            "living_storyworld.api.settings.load_user_settings", return_value=mock_settings
        ), patch("living_storyworld.api.settings.save_user_settings") as mock_save:
            request = SettingsUpdateRequest(
                text_provider="groq", image_provider="pollinations"
            )
            response = await update_settings(request)

            assert response["message"] == "Settings updated"
            assert mock_settings.text_provider == "groq"
            assert mock_settings.image_provider == "pollinations"
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_settings_api_keys(self):
        """update_settings validates and sets API keys."""
        mock_settings = UserSettings()

        with patch(
            "living_storyworld.api.settings.load_user_settings", return_value=mock_settings
        ), patch("living_storyworld.api.settings.save_user_settings"):
            request = SettingsUpdateRequest(openai_api_key="sk-1234567890abcdef12345")
            await update_settings(request)

            assert mock_settings.openai_api_key == "sk-1234567890abcdef12345"

    @pytest.mark.asyncio
    async def test_clear_api_keys(self):
        """clear_api_keys removes all API keys."""
        mock_settings = UserSettings(
            openai_api_key="sk-test1", groq_api_key="gsk-test2"
        )

        with patch(
            "living_storyworld.api.settings.load_user_settings", return_value=mock_settings
        ), patch("living_storyworld.api.settings.save_user_settings") as mock_save, patch.dict(
            os.environ, {"OPENAI_API_KEY": "sk-test1", "GROQ_API_KEY": "gsk-test2"}
        ):
            response = await clear_api_keys()

            assert response["message"] == "All API keys cleared"
            assert mock_settings.openai_api_key is None
            assert mock_settings.groq_api_key is None
            assert "OPENAI_API_KEY" not in os.environ
            assert "GROQ_API_KEY" not in os.environ
            mock_save.assert_called_once()


# ============================================================================
# Worlds API Tests
# ============================================================================


class TestWorldsAPI:
    """Test api/worlds.py functions."""

    @pytest.mark.asyncio
    async def test_list_worlds_empty(self, tmp_path):
        """list_worlds returns empty list when no worlds exist."""
        with patch("living_storyworld.api.worlds.WORLDS_DIR", tmp_path):
            worlds = await list_worlds()
            assert worlds == []

    @pytest.mark.asyncio
    async def test_list_worlds_with_data(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """list_worlds returns world information."""
        worlds_dir = tmp_path / "worlds"
        worlds_dir.mkdir()
        (worlds_dir / "test-world").mkdir()

        with patch("living_storyworld.api.worlds.WORLDS_DIR", worlds_dir), patch(
            "living_storyworld.api.worlds.load_world"
        ) as mock_load, patch(
            "living_storyworld.api.worlds.get_current_world", return_value="test-world"
        ):
            mock_load.return_value = (sample_world_config, sample_world_state, {})
            worlds = await list_worlds()

            assert len(worlds) == 1
            assert worlds[0].slug == "test-world"
            assert worlds[0].is_current is True

    @pytest.mark.asyncio
    async def test_list_worlds_skips_invalid(self, tmp_path):
        """list_worlds skips worlds that fail to load."""
        worlds_dir = tmp_path / "worlds"
        worlds_dir.mkdir()
        (worlds_dir / "bad-world").mkdir()

        with patch("living_storyworld.api.worlds.WORLDS_DIR", worlds_dir), patch(
            "living_storyworld.api.worlds.load_world", side_effect=Exception("Load failed")
        ), patch("living_storyworld.api.worlds.get_current_world", return_value=None):
            worlds = await list_worlds()
            assert worlds == []

    @pytest.mark.asyncio
    async def test_create_world_success(self, tmp_path):
        """create_world initializes a new world."""
        mock_config = WorldConfig(
            title="Test World",
            slug="test-world",
            theme="A test world",
            style_pack="storybook-ink",
            text_model="gpt-4o-mini",
        )
        mock_state = WorldState()

        with patch("living_storyworld.api.worlds.WORLDS_DIR", tmp_path), patch(
            "living_storyworld.api.worlds.init_world", return_value="test-world"
        ) as mock_init, patch(
            "living_storyworld.api.worlds.load_world",
            return_value=(mock_config, mock_state, {}),
        ):
            request = WorldCreateRequest(title="Test World", theme="A test world")
            response = await create_world(request)

            assert response.slug == "test-world"
            assert response.title == "Test World"
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_world_max_worlds_reached(self, tmp_path):
        """create_world enforces max worlds limit."""
        # Create 100 world directories
        for i in range(100):
            (tmp_path / f"world-{i}").mkdir()

        with patch("living_storyworld.api.worlds.WORLDS_DIR", tmp_path), patch.dict(
            os.environ, {"MAX_WORLDS_PER_INSTANCE": "100"}
        ):
            request = WorldCreateRequest(title="Too Many", theme="Overflow")
            with pytest.raises(HTTPException) as exc:
                await create_world(request)
            assert exc.value.status_code == 429
            assert "Maximum number of worlds" in exc.value.detail

    @pytest.mark.asyncio
    async def test_get_world_success(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """get_world returns detailed world information."""
        worlds_dir = tmp_path / "worlds"
        world_dir = worlds_dir / "test-world"
        world_dir.mkdir(parents=True)
        (world_dir / "media").mkdir()

        mock_dirs = {"base": world_dir}

        # Add a chapter with choices
        choice = Choice(id="c1", text="Go left", description="Turn left")
        chapter = Chapter(
            number=1,
            title="Test",
            filename="chapter-0001.md",
            summary="A test",
            scene_prompt="A scene",
            characters_in_scene=[],
            choices=[choice],
            selected_choice_id=None,
        )
        sample_world_state.chapters = [chapter]

        with patch("living_storyworld.api.worlds.load_world") as mock_load, patch(
            "living_storyworld.api.worlds.get_current_world", return_value="test-world"
        ), patch("living_storyworld.storage.read_json", return_value=[]):
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            world_info = ("test-world", world_dir)
            response = await get_world(world_info)

            assert response["config"]["slug"] == "test-world"
            assert response["is_current"] is True
            assert len(response["chapters"]) == 1
            assert len(response["chapters"][0]["choices"]) == 1

    @pytest.mark.asyncio
    async def test_set_current_world(self, tmp_path):
        """set_current updates current world."""
        world_dir = tmp_path / "test-world"
        world_dir.mkdir()

        with patch(
            "living_storyworld.api.worlds.set_current_world"
        ) as mock_set_current:
            world_info = ("test-world", world_dir)
            response = await set_current(world_info)

            assert "Current world set to test-world" in response["message"]
            mock_set_current.assert_called_once_with("test-world")

    @pytest.mark.asyncio
    async def test_update_world_config(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """update_world modifies world configuration."""
        world_dir = tmp_path / "test-world"
        mock_dirs = {"base": world_dir}

        with patch("living_storyworld.api.worlds.load_world") as mock_load, patch(
            "living_storyworld.world.save_world"
        ) as mock_save:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            request = WorldUpdateRequest(
                title="Updated Title", theme="Updated theme", enable_choices=True
            )
            world_info = ("test-world", world_dir)
            response = await update_world(request, world_info)

            assert response["config"]["title"] == "Updated Title"
            assert response["config"]["enable_choices"] is True
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_world(self, tmp_path):
        """delete_world removes world directory."""
        world_dir = tmp_path / "test-world"
        world_dir.mkdir()
        (world_dir / "test.txt").write_text("test")

        with patch(
            "living_storyworld.api.worlds.get_current_world", return_value="other-world"
        ):
            world_info = ("test-world", world_dir)
            response = await delete_world(world_info)

            assert "deleted" in response["message"]
            assert not world_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_current_world(self, tmp_path):
        """delete_world clears current world if deleting active world."""
        world_dir = tmp_path / "test-world"
        world_dir.mkdir()
        current_file = tmp_path / "current.txt"

        with patch(
            "living_storyworld.api.worlds.get_current_world", return_value="test-world"
        ), patch("living_storyworld.storage.CURRENT_FILE", current_file):
            current_file.write_text("test-world")

            world_info = ("test-world", world_dir)
            await delete_world(world_info)

            assert not current_file.exists()


# ============================================================================
# Chapters API Tests
# ============================================================================


class TestChaptersAPI:
    """Test api/chapters.py functions."""

    @pytest.mark.asyncio
    async def test_start_chapter_generation_invalid_slug(self):
        """start_chapter_generation validates slug."""
        request = ChapterGenerateRequest()
        with pytest.raises(HTTPException) as exc:
            await start_chapter_generation("../invalid", request)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_start_chapter_generation_world_not_found(self, tmp_path):
        """start_chapter_generation checks world exists."""
        with patch("living_storyworld.api.chapters.WORLDS_DIR", tmp_path):
            request = ChapterGenerateRequest()
            with pytest.raises(HTTPException) as exc:
                await start_chapter_generation("nonexistent", request)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_start_chapter_generation_success(self, tmp_path):
        """start_chapter_generation returns job ID."""
        worlds_dir = tmp_path / "worlds"
        worlds_dir.mkdir()
        (worlds_dir / "test-world").mkdir()

        with patch("living_storyworld.api.chapters.WORLDS_DIR", worlds_dir):
            request = ChapterGenerateRequest()
            response = await start_chapter_generation("test-world", request)

            assert "job_id" in response
            assert response["job_id"] in chapters.active_jobs

    @pytest.mark.asyncio
    async def test_get_chapter_content_success(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """get_chapter_content returns chapter markdown."""
        world_dir = tmp_path / "test-world"
        chapters_dir = world_dir / "chapters"
        chapters_dir.mkdir(parents=True)
        chapter_file = chapters_dir / "chapter-0001.md"
        chapter_file.write_text("# Chapter 1\n\nContent here.")

        mock_dirs = {"base": world_dir}
        chapter = Chapter(
            number=1,
            title="Test",
            filename="chapter-0001.md",
            summary="A test",
            scene_prompt="A scene",
            characters_in_scene=[],
        )
        sample_world_state.chapters = [chapter]

        with patch("living_storyworld.api.chapters.WORLDS_DIR", tmp_path), patch(
            "living_storyworld.api.chapters.load_world"
        ) as mock_load:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            response = await get_chapter_content("test-world", 1)
            assert response["content"] == "# Chapter 1\n\nContent here."

    @pytest.mark.asyncio
    async def test_get_chapter_content_not_found(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """get_chapter_content raises 404 for missing chapter."""
        world_dir = tmp_path / "test-world"
        world_dir.mkdir()
        mock_dirs = {"base": world_dir}

        with patch("living_storyworld.api.chapters.WORLDS_DIR", tmp_path), patch(
            "living_storyworld.api.chapters.load_world"
        ) as mock_load:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            with pytest.raises(HTTPException) as exc:
                await get_chapter_content("test-world", 999)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_select_choice_success(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """select_choice records user's choice selection."""
        world_dir = tmp_path / "test-world"
        world_dir.mkdir()
        mock_dirs = {"base": world_dir}

        # Create chapter with choices
        choice = Choice(id="c1", text="Go left", description="Turn left")
        chapter = Chapter(
            number=1,
            title="Test",
            filename="chapter-0001.md",
            summary="A test",
            scene_prompt="A scene",
            characters_in_scene=[],
            choices=[choice],
        )
        sample_world_state.chapters = [chapter]

        with patch("living_storyworld.api.chapters.load_world") as mock_load, patch(
            "living_storyworld.api.chapters.save_world"
        ) as mock_save:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            request = ChoiceSelectionRequest(choice_id="c1")
            response = await select_choice("test-world", 1, request)

            assert response["success"] is True
            assert response["choice"]["id"] == "c1"
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_choice_auto(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """select_choice handles auto selection."""
        world_dir = tmp_path / "test-world"
        world_dir.mkdir()
        mock_dirs = {"base": world_dir}

        # Create chapter with choices
        choice = Choice(id="c1", text="Go left", description="Turn left")
        chapter = Chapter(
            number=1,
            title="Test",
            filename="chapter-0001.md",
            summary="A test",
            scene_prompt="A scene",
            characters_in_scene=[],
            choices=[choice],
        )
        sample_world_state.chapters = [chapter]

        with patch("living_storyworld.api.chapters.load_world") as mock_load, patch(
            "living_storyworld.world.save_world"
        ):
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            request = ChoiceSelectionRequest(choice_id="auto")
            response = await select_choice("test-world", 1, request)

            assert response["success"] is True
            assert response["choice"]["id"] == "c1"

    @pytest.mark.asyncio
    async def test_select_choice_invalid_id(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """select_choice raises 400 for invalid choice ID."""
        world_dir = tmp_path / "test-world"
        mock_dirs = {"base": world_dir}

        choice = Choice(id="c1", text="Go left", description="Turn left")
        chapter = Chapter(
            number=1,
            title="Test",
            filename="chapter-0001.md",
            summary="A test",
            scene_prompt="A scene",
            characters_in_scene=[],
            choices=[choice],
        )
        sample_world_state.chapters = [chapter]

        with patch("living_storyworld.api.chapters.load_world") as mock_load:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            request = ChoiceSelectionRequest(choice_id="invalid")
            with pytest.raises(HTTPException) as exc:
                await select_choice("test-world", 1, request)
            assert exc.value.status_code == 400
            assert "Invalid choice ID" in exc.value.detail

    def test_get_cached_settings_fresh(self):
        """get_cached_settings loads fresh settings when cache empty."""
        # Reset cache
        chapters._settings_cache = None
        chapters._settings_cache_time = 0

        mock_settings = UserSettings(text_provider="openai")

        with patch(
            "living_storyworld.api.chapters.load_user_settings",
            return_value=mock_settings,
        ):
            settings = get_cached_settings()
            assert settings.text_provider == "openai"

    def test_get_cached_settings_uses_cache(self):
        """get_cached_settings returns cached value within TTL."""
        import time

        mock_settings = UserSettings(text_provider="cached")
        chapters._settings_cache = mock_settings
        chapters._settings_cache_time = time.time()

        with patch(
            "living_storyworld.api.chapters.load_user_settings"
        ) as mock_load:
            settings = get_cached_settings()
            assert settings.text_provider == "cached"
            mock_load.assert_not_called()


# ============================================================================
# Generate API Tests
# ============================================================================


class TestGenerateAPI:
    """Test api/generate.py functions."""

    def test_generate_random_theme_success(self):
        """_generate_random_theme uses OpenAI to generate theme."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='"A city in the clouds"'))]

        with patch("openai.OpenAI") as mock_openai, patch.dict(
            os.environ, {"OPENAI_API_KEY": "sk-test"}
        ):
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            theme = _generate_random_theme()
            assert theme == "A city in the clouds"

    def test_generate_random_theme_fallback(self):
        """_generate_random_theme uses fallback on error."""
        with patch("openai.OpenAI", side_effect=Exception("API error")):
            theme = _generate_random_theme()
            # Should be one of the fallback themes (non-empty string)
            assert len(theme) > 20  # Fallback themes are descriptive
            assert isinstance(theme, str)

    def test_generate_random_world_success(self):
        """_generate_random_world generates complete world config."""
        mock_settings = UserSettings(
            text_provider="openai", default_text_model="gpt-4o-mini"
        )
        mock_provider = Mock()
        mock_result = Mock(
            content=json.dumps(
                {
                    "title": "Test World",
                    "theme": "A test theme",
                    "memory": "World lore here",
                }
            )
        )
        mock_provider.generate.return_value = mock_result

        with patch(
            "living_storyworld.settings.load_user_settings",
            return_value=mock_settings,
        ), patch(
            "living_storyworld.settings.get_api_key_for_provider",
            return_value="sk-test",
        ), patch(
            "living_storyworld.providers.get_text_provider",
            return_value=mock_provider,
        ):
            world = _generate_random_world()

            assert world["title"] == "Test World"
            assert world["theme"] == "A test theme"
            assert "style_pack" in world
            assert "preset" in world

    def test_generate_random_world_fallback(self):
        """_generate_random_world uses fallback on error."""
        with patch(
            "living_storyworld.settings.load_user_settings",
            side_effect=Exception("Settings error"),
        ):
            world = _generate_random_world()
            # Should be one of the fallback worlds
            assert "title" in world
            assert "theme" in world
            assert "style_pack" in world

    @pytest.mark.asyncio
    async def test_generate_theme_endpoint(self):
        """generate_theme endpoint returns theme."""
        with patch(
            "living_storyworld.api.generate._generate_random_theme",
            return_value="Test theme",
        ):
            response = await generate_theme()
            assert response.theme == "Test theme"

    @pytest.mark.asyncio
    async def test_generate_world_endpoint(self):
        """generate_world endpoint returns world config."""
        mock_world = {
            "title": "Test World",
            "theme": "A theme",
            "style_pack": "storybook-ink",
            "preset": "cozy-adventure",
            "maturity_level": "general",
            "memory": "Lore",
        }

        with patch(
            "living_storyworld.api.generate._generate_random_world",
            return_value=mock_world,
        ):
            response = await generate_world()
            assert response.title == "Test World"
            assert response.theme == "A theme"


# ============================================================================
# Images API Tests
# ============================================================================


class TestImagesAPI:
    """Test api/images.py functions."""

    @pytest.mark.asyncio
    async def test_generate_image_with_prompt(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """generate_image creates image from provided prompt."""
        world_dir = tmp_path / "test-world"
        media_dir = world_dir / "media" / "scenes"
        media_dir.mkdir(parents=True)
        mock_image_path = media_dir / "scene-0001-abc123.png"
        mock_image_path.write_text("fake image")

        mock_dirs = {"base": world_dir}
        mock_settings = UserSettings(default_image_model="flux-schnell")

        with patch("living_storyworld.api.images.load_world_async") as mock_load, patch(
            "living_storyworld.settings.load_user_settings", return_value=mock_settings
        ), patch(
            "living_storyworld.api.images.generate_scene_image",
            return_value=mock_image_path,
        ) as mock_gen:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            request = ImageGenerateRequest(prompt="A beautiful scene", chapter=1)
            world_info = ("test-world", world_dir)
            response = await generate_image(request, world_info)

            assert "scene" in response
            assert "/worlds/test-world/media/scenes/" in response["scene"]
            assert ".png" in response["scene"]
            mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_from_chapter(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """generate_image uses chapter's scene_prompt when no prompt provided."""
        world_dir = tmp_path / "test-world"
        media_dir = world_dir / "media" / "scenes"
        media_dir.mkdir(parents=True)
        mock_image_path = media_dir / "scene-0001-abc123.png"
        mock_image_path.write_text("fake image")

        mock_dirs = {"base": world_dir}
        mock_settings = UserSettings(default_image_model="flux-schnell")

        # Add chapter with scene_prompt
        chapter = Chapter(
            number=1,
            title="Test",
            filename="chapter-0001.md",
            summary="A test",
            scene_prompt="Chapter scene prompt",
            characters_in_scene=[],
        )
        sample_world_state.chapters = [chapter]

        with patch("living_storyworld.api.images.load_world_async") as mock_load, patch(
            "living_storyworld.settings.load_user_settings", return_value=mock_settings
        ), patch(
            "living_storyworld.api.images.generate_scene_image",
            return_value=mock_image_path,
        ) as mock_gen, patch(
            "living_storyworld.world.save_world"
        ):
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            request = ImageGenerateRequest(chapter=1)
            world_info = ("test-world", world_dir)
            response = await generate_image(request, world_info)

            assert "scene" in response
            # Verify it called generate_scene_image with the chapter's scene_prompt
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args[0]
            assert call_args[3] == "Chapter scene prompt"  # prompt argument

    @pytest.mark.asyncio
    async def test_generate_image_no_prompt_error(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """generate_image raises 400 when no prompt available."""
        world_dir = tmp_path / "test-world"
        mock_dirs = {"base": world_dir}

        with patch(
            "living_storyworld.api.images.load_world_async"
        ) as mock_load:
            mock_load.return_value = (sample_world_config, sample_world_state, mock_dirs)

            request = ImageGenerateRequest()
            world_info = ("test-world", world_dir)

            with pytest.raises(HTTPException) as exc:
                await generate_image(request, world_info)
            assert exc.value.status_code == 400
            assert "No prompt provided" in exc.value.detail
