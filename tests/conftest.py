import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest

from living_storyworld.models import (
    Character,
    Chapter,
    Choice,
    Location,
    WorldConfig,
    WorldState,
)


@pytest.fixture
def tmp_world_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for world storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_world_config() -> WorldConfig:
    """Create a sample WorldConfig for testing."""
    return WorldConfig(
        title="Test World",
        slug="test-world",
        theme="A mysterious fantasy realm",
        text_model="gpt-4",
        style_pack="storybook-ink",
        maturity_level="general",
        memory="This is a test world with magic.",
        authors_note="Keep the tone light and whimsical.",
        world_instructions="Focus on character development.",
    )


@pytest.fixture
def sample_character() -> Character:
    """Create a sample Character for testing."""
    return Character(
        id="char-001",
        name="Test Hero",
        description="A brave adventurer",
    )


@pytest.fixture
def sample_location() -> Location:
    """Create a sample Location for testing."""
    return Location(
        id="loc-001",
        name="Test Village",
        description="A peaceful settlement",
    )


@pytest.fixture
def sample_choice() -> Choice:
    """Create a sample Choice for testing."""
    return Choice(
        id="choice-001",
        text="Explore the forest",
        description="You venture into the unknown",
    )


@pytest.fixture
def sample_chapter(sample_choice: Choice) -> Chapter:
    """Create a sample Chapter for testing."""
    return Chapter(
        number=1,
        title="The Beginning",
        filename="chapter-0001.md",
        summary="The hero's journey begins",
        scene_prompt="A hero standing at a crossroads",
        characters_in_scene=["char-001"],
        choices=[sample_choice],
    )


@pytest.fixture
def sample_world_state(
    sample_character: Character,
    sample_location: Location,
    sample_chapter: Chapter,
) -> WorldState:
    """Create a sample WorldState for testing."""
    return WorldState(
        tick=1,
        characters={"char-001": sample_character.__dict__},
        locations={"loc-001": sample_location.__dict__},
        items={},
        chapters=[sample_chapter],
    )


@pytest.fixture
def mock_text_response() -> dict:
    """Mock text generation provider response."""
    return {
        "content": "# Chapter 1: Test Chapter\n\nThis is test content.",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "cost": 0.001,
    }


@pytest.fixture
def mock_image_response() -> bytes:
    """Mock image generation provider response (1x1 PNG)."""
    # Minimal valid PNG (1x1 transparent pixel)
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82,
    ])


@pytest.fixture
def init_world_filesystem(
    tmp_world_dir: Path,
    sample_world_config: WorldConfig,
    sample_world_state: WorldState,
) -> Path:
    """Initialize a complete world filesystem structure."""
    world_slug = "test-world"
    world_path = tmp_world_dir / world_slug
    world_path.mkdir(parents=True)

    # Create config.json
    config_path = world_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(sample_world_config.to_dict(), f, indent=2)

    # Create world.json
    world_json_path = world_path / "world.json"
    with open(world_json_path, "w") as f:
        json.dump(sample_world_state.to_dict(), f, indent=2)

    # Create subdirectories
    (world_path / "chapters").mkdir()
    (world_path / "media" / "scenes").mkdir(parents=True)

    # Create sample chapter file
    chapter_path = world_path / "chapters" / "chapter-0001.md"
    with open(chapter_path, "w") as f:
        f.write("# Chapter 1: The Beginning\n\nOnce upon a time...")

    # Create media index
    media_index = world_path / "media" / "index.json"
    with open(media_index, "w") as f:
        json.dump({}, f)

    return world_path


@pytest.fixture
def mock_text_provider() -> MagicMock:
    """Create a mock text generation provider."""
    provider = MagicMock()
    provider.generate.return_value = {
        "content": "# Chapter 1\n\nTest content.",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "cost": 0.001,
    }
    provider.validate_model.return_value = True
    provider.estimate_cost.return_value = 0.001
    return provider


@pytest.fixture
def mock_image_provider(mock_image_response: bytes) -> MagicMock:
    """Create a mock image generation provider."""
    provider = MagicMock()
    provider.generate.return_value = mock_image_response
    provider.validate_model.return_value = True
    return provider
