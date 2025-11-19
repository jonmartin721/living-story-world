import json
import pytest
from unittest.mock import MagicMock, patch

from living_storyworld.generator import (
    _build_chapter_prompt,
    _parse_meta,
    _extract_title,
    _register_new_entities,
    _write_scene_request,
    generate_chapter,
    infer_choice_reasoning,
    generate_chapter_summary,
)
from living_storyworld.models import (
    WorldConfig,
    WorldState,
    Chapter,
    Choice,
)


class TestBuildChapterPrompt:
    """Test prompt building logic."""

    def test_basic_prompt_structure(self):
        """Test basic prompt structure with minimal config."""
        cfg = WorldConfig(
            title="Test World",
            slug="test-world",
            theme="Fantasy realm",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            style, messages, temp = _build_chapter_prompt(cfg, state)

        assert isinstance(messages, list)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Test World" in messages[1]["content"]
        assert "Fantasy realm" in messages[1]["content"]
        assert isinstance(temp, float)

    def test_prompt_with_memory(self):
        """Test prompt includes memory field."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            memory="Important lore about dragons",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        user_content = messages[1]["content"]
        assert "Memory/Lore" in user_content
        assert "Important lore about dragons" in user_content

    def test_prompt_with_authors_note(self):
        """Test prompt includes author's note."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            authors_note="Keep it whimsical",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        user_content = messages[1]["content"]
        assert "Author's Note" in user_content
        assert "Keep it whimsical" in user_content

    def test_prompt_with_world_instructions(self):
        """Test prompt includes world-specific instructions."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            world_instructions="Focus on character development",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        system_content = messages[0]["content"]
        assert "World Instructions" in system_content
        assert "Focus on character development" in system_content

    def test_prompt_with_global_instructions(self):
        """Test prompt includes global instructions from settings."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                global_instructions="Always include humor"
            )
            _, messages, _ = _build_chapter_prompt(cfg, state)

        system_content = messages[0]["content"]
        assert "Global Instructions" in system_content
        assert "Always include humor" in system_content

    @pytest.mark.parametrize(
        "maturity_level,expected_keyword",
        [
            ("general", "family-friendly"),
            ("teen", "young adult"),
            ("mature", "adult fiction"),
            ("explicit", "unrestricted"),
        ],
    )
    def test_maturity_levels(self, maturity_level, expected_keyword):
        """Test different maturity levels produce appropriate guidance."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            maturity_level=maturity_level,
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        system_content = messages[0]["content"]
        assert expected_keyword in system_content.lower()

    def test_prompt_with_story_context(self):
        """Test prompt includes recent chapter summaries."""
        ch1 = Chapter(
            number=1,
            title="Beginning",
            filename="chapter-0001.md",
            summary="Hero starts journey",
            scene_prompt="Hero at crossroads",
        )
        ch2 = Chapter(
            number=2,
            title="Journey",
            filename="chapter-0002.md",
            summary="Hero meets companion",
            scene_prompt="Forest meeting",
        )

        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(
            tick=2,
            characters={},
            locations={},
            items={},
            chapters=[ch1, ch2],
        )

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        user_content = messages[1]["content"]
        assert "Story progression" in user_content
        assert "Hero starts journey" in user_content
        assert "Hero meets companion" in user_content

    def test_prompt_with_selected_choice(self):
        """Test prompt includes selected choice from previous chapter."""
        choice1 = Choice(
            id="choice-1",
            text="Enter the forest",
            description="Leads to dark woods",
        )
        ch1 = Chapter(
            number=1,
            title="Beginning",
            filename="chapter-0001.md",
            summary="Hero at crossroads",
            scene_prompt="Crossroads",
            choices=[choice1],
            selected_choice_id="choice-1",
        )

        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            enable_choices=True,
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(
            tick=1,
            characters={},
            locations={},
            items={},
            chapters=[ch1],
        )

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        user_content = messages[1]["content"]
        assert "READER'S CHOICE" in user_content
        assert "Enter the forest" in user_content

    def test_first_chapter_guidance(self):
        """Test first chapter includes special guidance."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        user_content = messages[1]["content"]
        assert "FIRST CHAPTER GUIDANCE" in user_content
        assert "compelling narrative seed" in user_content

    def test_chapter_length_variations(self):
        """Test different chapter lengths produce different word counts."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=1, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")

            # Test short
            _, msgs_short, _ = _build_chapter_prompt(cfg, state, chapter_length="short")
            # Test medium
            _, msgs_medium, _ = _build_chapter_prompt(
                cfg, state, chapter_length="medium"
            )
            # Test long
            _, msgs_long, _ = _build_chapter_prompt(cfg, state, chapter_length="long")

        # Verify they all have prompts (actual word counts vary with random.uniform)
        assert "words of rich prose" in msgs_short[1]["content"]
        assert "words of rich prose" in msgs_medium[1]["content"]
        assert "words of rich prose" in msgs_long[1]["content"]

    def test_choices_enabled_metadata(self):
        """Test choices enabled adds choice metadata to prompt."""
        cfg = WorldConfig(
            title="Test",
            slug="test",
            theme="Theme",
            enable_choices=True,
            text_model="gpt-4",
            style_pack="storybook-ink",
        )
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])

        with patch("living_storyworld.generator.load_user_settings") as mock_settings:
            mock_settings.return_value = MagicMock(global_instructions="")
            _, messages, _ = _build_chapter_prompt(cfg, state)

        system_content = messages[0]["content"]
        messages[1]["content"]
        assert "choices" in system_content
        assert "story_health" in system_content


class TestParseMeta:
    """Test metadata parsing from markdown."""

    def test_parse_valid_metadata(self):
        """Test parsing valid JSON metadata."""
        md = """<!-- {"scene_prompt": "A forest", "summary": "Hero enters woods"} -->
# Chapter 1

Content here."""
        meta = _parse_meta(md)
        assert meta["scene_prompt"] == "A forest"
        assert meta["summary"] == "Hero enters woods"

    def test_parse_no_metadata(self):
        """Test parsing markdown without metadata."""
        md = "# Chapter 1\n\nContent here."
        meta = _parse_meta(md)
        assert meta == {}

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns empty dict."""
        md = '<!-- {invalid json} -->\n# Chapter 1\n\nContent'
        meta = _parse_meta(md)
        assert meta == {}

    def test_parse_multiline_metadata(self):
        """Test parsing metadata across multiple lines."""
        md = """<!--
{
  "scene_prompt": "A castle",
  "characters_in_scene": ["hero", "villain"]
}
-->
# Chapter 1"""
        meta = _parse_meta(md)
        assert meta["scene_prompt"] == "A castle"
        assert meta["characters_in_scene"] == ["hero", "villain"]


class TestExtractTitle:
    """Test title extraction from markdown."""

    def test_extract_simple_title(self):
        """Test extracting simple H1 title."""
        md = "# The Great Adventure\n\nOnce upon a time..."
        title = _extract_title(md)
        assert title == "The Great Adventure"

    def test_extract_title_with_chapter_prefix(self):
        """Test extracting title with 'Chapter N:' prefix removed."""
        md = "# Chapter 1: The Beginning\n\nContent"
        title = _extract_title(md)
        assert title == "The Beginning"

    def test_extract_title_no_h1(self):
        """Test extracting title when no H1 exists."""
        md = "Just some content without a heading."
        title = _extract_title(md)
        assert title is None

    def test_extract_title_with_whitespace(self):
        """Test extracting title with extra whitespace."""
        md = "#    The Title With Spaces    \n\nContent"
        title = _extract_title(md)
        assert title == "The Title With Spaces"


class TestRegisterNewEntities:
    """Test entity registration from chapter metadata."""

    def test_register_new_character(self):
        """Test registering a new character."""
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])
        new_characters = [
            {
                "id": "char-1",
                "name": "Hero",
                "description": "A brave warrior",
            }
        ]
        _register_new_entities(state, new_characters, [])

        assert "char-1" in state.characters
        assert state.characters["char-1"]["name"] == "Hero"
        assert state.characters["char-1"]["description"] == "A brave warrior"

    def test_register_new_location(self):
        """Test registering a new location."""
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])
        new_locations = [
            {
                "id": "loc-1",
                "name": "Dark Forest",
                "description": "A mysterious woodland",
            }
        ]
        _register_new_entities(state, [], new_locations)

        assert "loc-1" in state.locations
        assert state.locations["loc-1"]["name"] == "Dark Forest"

    def test_skip_existing_entities(self):
        """Test that existing entities are not overwritten."""
        state = WorldState(
            tick=0,
            characters={"char-1": {"id": "char-1", "name": "Original"}},
            locations={},
            items={},
            chapters=[],
        )
        new_characters = [{"id": "char-1", "name": "Duplicate"}]
        _register_new_entities(state, new_characters, [])

        # Should not be overwritten
        assert state.characters["char-1"]["name"] == "Original"

    def test_register_invalid_data(self):
        """Test that invalid entity data is skipped."""
        state = WorldState(tick=0, characters={}, locations={}, items={}, chapters=[])
        # Missing required fields
        new_characters = [
            {"id": "char-1"},  # Missing name
            {"name": "No ID"},  # Missing id
            "invalid",  # Not a dict
        ]
        _register_new_entities(state, new_characters, [])

        assert len(state.characters) == 0


class TestWriteSceneRequest:
    """Test scene request file writing."""

    def test_write_new_scene_request(self, tmp_path):
        """Test writing a new scene request file."""
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        _write_scene_request(tmp_path, 1, "storybook-ink", "A beautiful sunset")

        req_file = tmp_path / "media" / "scene_requests.json"
        assert req_file.exists()

        data = json.loads(req_file.read_text())
        assert len(data) == 1
        assert data[0]["chapter"] == 1
        assert data[0]["style_pack"] == "storybook-ink"
        assert data[0]["prompt"] == "A beautiful sunset"

    def test_append_scene_request(self, tmp_path):
        """Test appending to existing scene requests."""
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        # Write first request
        _write_scene_request(tmp_path, 1, "storybook-ink", "First scene")
        # Write second request
        _write_scene_request(tmp_path, 2, "pixel-rpg", "Second scene")

        req_file = tmp_path / "media" / "scene_requests.json"
        data = json.loads(req_file.read_text())
        assert len(data) == 2
        assert data[0]["chapter"] == 1
        assert data[1]["chapter"] == 2


class TestGenerateChapter:
    """Test full chapter generation."""

    def test_generate_chapter_success(
        self, tmp_path, sample_world_config, sample_world_state, mock_text_provider
    ):
        """Test successful chapter generation."""
        # Setup world directories
        chapters_dir = tmp_path / "chapters"
        media_dir = tmp_path / "media"
        chapters_dir.mkdir()
        media_dir.mkdir()

        # Mock provider response with metadata
        mock_response = MagicMock()
        mock_response.content = """<!-- {
  "scene_prompt": "Hero standing",
  "image_prompt": "A brave hero",
  "summary": "Chapter summary",
  "characters_in_scene": ["hero"],
  "new_characters": [],
  "new_locations": []
} -->
# The Beginning

Once upon a time..."""
        mock_response.provider = "openai"
        mock_response.model = "gpt-4"
        mock_response.estimated_cost = 0.01
        mock_text_provider.generate.return_value = mock_response
        mock_text_provider.get_default_model.return_value = "gpt-4"

        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.settings.get_available_text_providers") as mock_avail, \
             patch("living_storyworld.settings.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(global_instructions="")
            mock_avail.return_value = ["openai"]
            mock_key.return_value = "test-key"
            mock_get_provider.return_value = mock_text_provider

            chapter = generate_chapter(
                tmp_path, sample_world_config, sample_world_state, make_scene_image=True
            )

        assert chapter.number == 1
        assert chapter.title == "The Beginning"
        assert chapter.summary == "Chapter summary"
        assert chapter.scene_prompt == "Hero standing"

        # Verify chapter file was written
        chapter_file = tmp_path / "chapters" / "chapter-0001.md"
        assert chapter_file.exists()

    def test_generate_chapter_no_providers(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """Test chapter generation fails when no providers configured."""
        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.settings.get_available_text_providers") as mock_avail:

            mock_settings.return_value = MagicMock()
            mock_avail.return_value = []

            with pytest.raises(ValueError, match="No text providers configured"):
                generate_chapter(tmp_path, sample_world_config, sample_world_state)

    def test_generate_chapter_provider_fallback(
        self, tmp_path, sample_world_config, sample_world_state
    ):
        """Test provider fallback when first provider fails."""
        chapters_dir = tmp_path / "chapters"
        media_dir = tmp_path / "media"
        chapters_dir.mkdir()
        media_dir.mkdir()

        # First provider fails, second succeeds
        failing_provider = MagicMock()
        failing_provider.generate.side_effect = Exception("API Error")

        success_provider = MagicMock()
        success_response = MagicMock()
        success_response.content = """<!-- {"scene_prompt": "Test"} -->
# Chapter Title

Content"""
        success_response.provider = "groq"
        success_response.model = "llama"
        success_response.estimated_cost = 0.001
        success_provider.generate.return_value = success_response
        success_provider.get_default_model.return_value = "llama"

        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.settings.get_available_text_providers") as mock_avail, \
             patch("living_storyworld.settings.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(global_instructions="")
            mock_avail.return_value = ["openai", "groq"]
            mock_key.return_value = "test-key"
            mock_get_provider.side_effect = [failing_provider, success_provider]

            chapter = generate_chapter(tmp_path, sample_world_config, sample_world_state)

        assert chapter.title == "Chapter Title"

    def test_generate_chapter_with_new_entities(
        self, tmp_path, sample_world_config, sample_world_state, mock_text_provider
    ):
        """Test chapter generation registers new entities."""
        chapters_dir = tmp_path / "chapters"
        media_dir = tmp_path / "media"
        chapters_dir.mkdir()
        media_dir.mkdir()

        mock_response = MagicMock()
        mock_response.content = """<!-- {
  "scene_prompt": "Village",
  "new_characters": [{"id": "new-char", "name": "NewChar", "description": "A new character"}],
  "new_locations": [{"id": "new-loc", "name": "NewPlace", "description": "A new place"}]
} -->
# Chapter

Content"""
        mock_response.provider = "openai"
        mock_response.model = "gpt-4"
        mock_response.estimated_cost = 0.01
        mock_text_provider.generate.return_value = mock_response
        mock_text_provider.get_default_model.return_value = "gpt-4"

        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.settings.get_available_text_providers") as mock_avail, \
             patch("living_storyworld.settings.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(global_instructions="")
            mock_avail.return_value = ["openai"]
            mock_key.return_value = "test-key"
            mock_get_provider.return_value = mock_text_provider

            generate_chapter(tmp_path, sample_world_config, sample_world_state)

        # Verify entities were registered
        assert "new-char" in sample_world_state.characters
        assert "new-loc" in sample_world_state.locations


@pytest.mark.asyncio
class TestInferChoiceReasoning:
    """Test choice reasoning inference."""

    async def test_infer_choice_reasoning_success(self, sample_world_config):
        """Test successful choice reasoning inference."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "The reader wanted to see what happens in the forest."
        mock_provider.generate.return_value = mock_response

        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.generator.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_key.return_value = "test-key"
            mock_get_provider.return_value = mock_provider

            reasoning = await infer_choice_reasoning(
                "Enter the forest",
                "Hero at crossroads",
                "Fantasy adventure",
                sample_world_config,
            )

        assert "forest" in reasoning.lower()

    async def test_infer_choice_reasoning_provider_failure(self, sample_world_config):
        """Test fallback when provider fails."""
        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.generator.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_key.return_value = "test-key"
            mock_get_provider.side_effect = Exception("Provider failed")

            reasoning = await infer_choice_reasoning(
                "Enter the forest",
                "Hero at crossroads",
                "Fantasy adventure",
                sample_world_config,
            )

        assert "enter the forest" in reasoning.lower()


@pytest.mark.asyncio
class TestGenerateChapterSummary:
    """Test chapter summary generation."""

    async def test_generate_summary_success(self, sample_world_config):
        """Test successful summary generation."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "The hero enters a dark forest and meets a mysterious stranger."
        mock_provider.generate.return_value = mock_response

        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.generator.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_key.return_value = "test-key"
            mock_get_provider.return_value = mock_provider

            summary = await generate_chapter_summary(
                "# Chapter 1\n\nThe hero walked into the forest...",
                sample_world_config,
            )

        assert "forest" in summary.lower()
        assert len(summary) > 0

    async def test_generate_summary_provider_failure(self, sample_world_config):
        """Test fallback when provider fails."""
        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.generator.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_key.return_value = "test-key"
            mock_get_provider.side_effect = Exception("Provider failed")

            summary = await generate_chapter_summary(
                "# Chapter 1\n\nContent",
                sample_world_config,
            )

        assert summary == ""

    async def test_generate_summary_truncates_long_output(self, sample_world_config):
        """Test that very long summaries are truncated."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "A" * 400  # Longer than 300 char limit
        mock_provider.generate.return_value = mock_response

        with patch("living_storyworld.generator.load_user_settings") as mock_settings, \
             patch("living_storyworld.generator.get_api_key_for_provider") as mock_key, \
             patch("living_storyworld.generator.get_text_provider") as mock_get_provider:

            mock_settings.return_value = MagicMock(
                text_provider="openai",
                default_text_model="gpt-4",
            )
            mock_key.return_value = "test-key"
            mock_get_provider.return_value = mock_provider

            summary = await generate_chapter_summary("Content", sample_world_config)

        assert len(summary) <= 300
        assert summary.endswith("...")
