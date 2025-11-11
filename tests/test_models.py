from dataclasses import asdict
from living_storyworld.models import (
    Character, Location, Item, Choice, Chapter, WorldState, WorldConfig
)
from living_storyworld.world import _deserialize_world_state


class TestDataclassSerialization:
    """Test serialization/deserialization of dataclass models."""

    def test_character_roundtrip(self):
        char = Character(
            id="hero",
            name="The Hero",
            epithet="Brave One",
            traits=["courageous", "kind"],
            description="A brave adventurer",
            visual_profile={"hair": "dark", "eyes": "blue"}
        )
        data = asdict(char)
        restored = Character(**data)
        assert restored == char

    def test_location_roundtrip(self):
        loc = Location(
            id="town",
            name="Riverside Town",
            description="A peaceful settlement",
            tags=["safe", "urban"]
        )
        data = asdict(loc)
        restored = Location(**data)
        assert restored == loc

    def test_item_roundtrip(self):
        item = Item(
            id="sword",
            name="Ancient Blade",
            description="A legendary weapon",
            tags=["weapon", "magical"]
        )
        data = asdict(item)
        restored = Item(**data)
        assert restored == item

    def test_choice_roundtrip(self):
        choice = Choice(
            id="choice-1",
            text="Investigate the noise",
            description="A brave decision"
        )
        data = asdict(choice)
        restored = Choice(**data)
        assert restored == choice

    def test_chapter_roundtrip(self):
        chapter = Chapter(
            number=1,
            title="The Beginning",
            filename="chapter-0001.md",
            summary="First chapter",
            ai_summary="Hero meets mentor",
            scene_prompt="A hero in a tavern",
            characters_in_scene=["hero", "mentor"],
            choices=[
                Choice(id="c1", text="Talk to mentor"),
                Choice(id="c2", text="Leave tavern")
            ],
            selected_choice_id="c1",
            choice_reasoning="Seemed interesting",
            generated_at="2024-01-01T00:00:00",
            text_model_used="gpt-4",
            image_model_used="flux-dev"
        )
        data = asdict(chapter)

        # Reconstruct with nested choices
        data["choices"] = [Choice(**c) for c in data["choices"]]
        restored = Chapter(**data)
        assert restored == chapter

    def test_world_state_roundtrip(self):
        state = WorldState(
            tick=5,
            next_chapter=3,
            characters={
                "hero": Character(id="hero", name="Hero"),
                "mentor": Character(id="mentor", name="Mentor")
            },
            locations={
                "town": Location(id="town", name="Town")
            },
            items={
                "sword": Item(id="sword", name="Sword")
            },
            chapters=[
                Chapter(
                    number=1,
                    title="First",
                    filename="chapter-0001.md",
                    choices=[Choice(id="c1", text="Go")]
                )
            ]
        )
        data = asdict(state)
        restored = _deserialize_world_state(data)

        assert restored.tick == state.tick
        assert restored.next_chapter == state.next_chapter
        assert restored.characters == state.characters
        assert restored.locations == state.locations
        assert restored.items == state.items
        assert len(restored.chapters) == len(state.chapters)
        assert restored.chapters[0].number == state.chapters[0].number

    def test_world_state_empty_collections(self):
        state = WorldState()
        data = asdict(state)
        restored = _deserialize_world_state(data)

        assert restored.tick == 0
        assert restored.next_chapter == 1
        assert restored.characters == {}
        assert restored.locations == {}
        assert restored.items == {}
        assert restored.chapters == []

    def test_world_config_serialization(self):
        config = WorldConfig(
            title="Test World",
            slug="test-world",
            theme="A test theme",
            style_pack="storybook-ink",
            text_model="gpt-4",
            maturity_level="general",
            preset="cozy-adventure",
            enable_choices=True,
            memory="Important lore",
            authors_note="Keep it cozy",
            world_instructions="Custom rules"
        )
        data = asdict(config)
        restored = WorldConfig(**data)
        assert restored == config
