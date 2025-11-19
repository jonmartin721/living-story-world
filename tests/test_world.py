import json
import pytest
from unittest.mock import MagicMock, patch

from living_storyworld.world import (
    init_world,
    load_world,
    save_world,
    tick_world,
    _deserialize_world_state,
)
from living_storyworld.models import Choice


class TestDeserializeWorldState:
    """Test WorldState deserialization."""

    def test_deserialize_empty_state(self):
        """Test deserializing empty state."""
        data = {
            "tick": 0,
            "next_chapter": 1,
            "characters": {},
            "locations": {},
            "items": {},
            "chapters": [],
        }
        state = _deserialize_world_state(data)
        assert state.tick == 0
        assert state.next_chapter == 1
        assert len(state.characters) == 0
        assert len(state.chapters) == 0

    def test_deserialize_with_chapters_and_choices(self):
        """Test deserializing state with chapters containing choices."""
        data = {
            "tick": 2,
            "next_chapter": 3,
            "characters": {},
            "locations": {},
            "items": {},
            "chapters": [
                {
                    "number": 1,
                    "title": "Chapter 1",
                    "filename": "chapter-0001.md",
                    "choices": [
                        {
                            "id": "choice-1",
                            "text": "Go left",
                            "description": "Take the left path",
                        }
                    ],
                },
                {
                    "number": 2,
                    "title": "Chapter 2",
                    "filename": "chapter-0002.md",
                    "choices": [],
                },
            ],
        }
        state = _deserialize_world_state(data)
        assert len(state.chapters) == 2
        assert len(state.chapters[0].choices) == 1
        assert state.chapters[0].choices[0].id == "choice-1"
        assert isinstance(state.chapters[0].choices[0], Choice)

    def test_deserialize_with_entities(self):
        """Test deserializing state with characters, locations, and items."""
        data = {
            "tick": 1,
            "next_chapter": 2,
            "characters": {
                "hero": {
                    "id": "hero",
                    "name": "Hero Name",
                    "description": "A brave hero",
                }
            },
            "locations": {
                "village": {
                    "id": "village",
                    "name": "Starting Village",
                    "description": "A peaceful place",
                }
            },
            "items": {
                "sword": {
                    "id": "sword",
                    "name": "Magic Sword",
                    "description": "A powerful weapon",
                }
            },
            "chapters": [],
        }
        state = _deserialize_world_state(data)
        assert "hero" in state.characters
        assert state.characters["hero"].name == "Hero Name"
        assert "village" in state.locations
        assert state.locations["village"].name == "Starting Village"
        assert "sword" in state.items
        assert state.items["sword"].name == "Magic Sword"

    def test_deserialize_defaults(self):
        """Test deserialization with missing fields uses defaults."""
        data = {}
        state = _deserialize_world_state(data)
        assert state.tick == 0
        assert state.next_chapter == 1
        assert len(state.characters) == 0
        assert len(state.locations) == 0
        assert len(state.items) == 0
        assert len(state.chapters) == 0


class TestInitAndLoadWorld:
    """Test world initialization and loading (integration style)."""

    def test_init_and_load_roundtrip(self, tmp_path):
        """Test creating and loading a world."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"), \
             patch("living_storyworld.world.load_user_settings") as mock_settings, \
             patch("living_storyworld.world.get_text_provider") as mock_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_prov = MagicMock()
            mock_prov.get_default_model.return_value = "gpt-4"
            mock_provider.return_value = mock_prov

            slug = init_world(
                title="Test World",
                theme="Fantasy adventure",
                memory="Test memory",
                enable_choices=True,
            )

            assert slug == "test-world"

            # Load it back
            cfg, state, dirs = load_world(slug)

            assert cfg.title == "Test World"
            assert cfg.theme == "Fantasy adventure"
            assert cfg.memory == "Test memory"
            assert cfg.enable_choices is True
            assert state.tick == 0
            assert state.next_chapter == 1

    def test_init_with_provider_failure(self, tmp_path):
        """Test init when provider fails."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"), \
             patch("living_storyworld.world.load_user_settings") as mock_settings, \
             patch("living_storyworld.world.get_text_provider") as mock_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="fallback-model",
            )
            mock_provider.side_effect = Exception("Provider error")

            slug = init_world(title="Fallback", theme="Theme")

            cfg, state, dirs = load_world(slug)
            assert cfg.text_model == "fallback-model"

    def test_load_missing_world(self, tmp_path):
        """Test loading non-existent world."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"):
            with pytest.raises(RuntimeError, match="config.json not found"):
                load_world("nonexistent")

    def test_load_corrupted_config(self, tmp_path):
        """Test loading world with corrupted config."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"):
            # Create world with bad config
            world_dir = tmp_path / "worlds" / "bad"
            world_dir.mkdir(parents=True)
            (world_dir / "config.json").write_text("{invalid")

            with pytest.raises(RuntimeError, match="config.json not found or corrupted"):
                load_world("bad")

    def test_load_backward_compat_image_model(self, tmp_path):
        """Test loading world with old image_model field."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"):
            world_dir = tmp_path / "worlds" / "old"
            world_dir.mkdir(parents=True)

            # Old format with image_model
            config = {
                "title": "Old",
                "slug": "old",
                "theme": "Theme",
                "text_model": "gpt-4",
                "image_model": "old-image-model",
                "style_pack": "storybook-ink",
            }
            (world_dir / "config.json").write_text(json.dumps(config))

            state = {
                "tick": 0,
                "next_chapter": 1,
                "characters": {},
                "locations": {},
                "items": {},
                "chapters": [],
            }
            (world_dir / "world.json").write_text(json.dumps(state))

            # Should load without error
            cfg, _, _ = load_world("old")
            assert cfg.title == "Old"


class TestSaveAndTickWorld:
    """Test world saving and tick operations."""

    def test_save_world(self, tmp_path):
        """Test saving world modifications."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"), \
             patch("living_storyworld.world.load_user_settings") as mock_settings, \
             patch("living_storyworld.world.get_text_provider") as mock_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_prov = MagicMock()
            mock_prov.get_default_model.return_value = "gpt-4"
            mock_provider.return_value = mock_prov

            slug = init_world(title="Save Test", theme="Theme")

            # Modify and save
            cfg, state, dirs = load_world(slug)
            state.tick = 42
            save_world(slug, cfg, state, dirs)

            # Reload and verify
            _, state2, _ = load_world(slug)
            assert state2.tick == 42

    def test_save_world_without_dirs(self, tmp_path):
        """Test saving without providing dirs."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"), \
             patch("living_storyworld.world.load_user_settings") as mock_settings, \
             patch("living_storyworld.world.get_text_provider") as mock_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_prov = MagicMock()
            mock_prov.get_default_model.return_value = "gpt-4"
            mock_provider.return_value = mock_prov

            slug = init_world(title="Save Test 2", theme="Theme")

            cfg, state, _ = load_world(slug)
            state.tick = 99
            save_world(slug, cfg, state)  # No dirs

            _, state2, _ = load_world(slug)
            assert state2.tick == 99

    def test_tick_world(self, tmp_path):
        """Test incrementing world tick."""
        with patch("living_storyworld.storage.WORLDS_DIR", tmp_path / "worlds"), \
             patch("living_storyworld.world.load_user_settings") as mock_settings, \
             patch("living_storyworld.world.get_text_provider") as mock_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_prov = MagicMock()
            mock_prov.get_default_model.return_value = "gpt-4"
            mock_provider.return_value = mock_prov

            slug = init_world(title="Tick Test", theme="Theme")

            # Tick multiple times
            tick1 = tick_world(slug)
            assert tick1 == 1

            tick2 = tick_world(slug)
            assert tick2 == 2

            # Verify persistence
            _, state, _ = load_world(slug)
            assert state.tick == 2
