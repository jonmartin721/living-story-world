import pytest
from living_storyworld.storage import slugify, validate_slug


class TestSlugify:
    """Test slug generation from arbitrary strings."""

    def test_basic_conversion(self):
        assert slugify("My World") == "my-world"
        assert slugify("Test 123") == "test-123"
        assert slugify("Hello  World") == "hello-world"

    def test_single_character(self):
        assert slugify("a") == "a"
        assert slugify("A") == "a"
        assert slugify("5") == "5"

    def test_special_characters_stripped(self):
        assert slugify("hello@world!") == "helloworld"
        assert slugify("test_name") == "testname"
        assert slugify("my.world") == "myworld"

    def test_consecutive_hyphens_collapsed(self):
        assert slugify("hello---world") == "hello-world"
        assert slugify("test - - name") == "test-name"

    def test_leading_trailing_hyphens_removed(self):
        assert slugify("-hello-") == "hello"
        assert slugify("---test---") == "test"

    def test_empty_string_fallback(self):
        assert slugify("") == "world"
        assert slugify("   ") == "world"
        assert slugify("!!!") == "world"

    def test_path_traversal_sanitization(self):
        # slugify sanitizes dangerous input rather than rejecting it
        assert slugify("../parent") == "parent"
        assert slugify("foo/../bar") == "foobar"
        assert slugify("test/path") == "testpath"
        assert slugify("test\\path") == "testpath"

    def test_dot_prefix_sanitization(self):
        # slugify strips leading dots during sanitization
        assert slugify(".hidden") == "hidden"
        assert slugify("..secret") == "secret"

    def test_length_limits(self):
        valid = "a" * 100
        assert slugify(valid) == valid

        too_long = "a" * 101
        with pytest.raises(ValueError, match="too long"):
            slugify(too_long)


class TestValidateSlug:
    """Test validation of pre-existing slugs from API/URL."""

    def test_valid_slugs(self):
        assert validate_slug("my-world") == "my-world"
        assert validate_slug("test-123") == "test-123"
        assert validate_slug("a") == "a"
        assert validate_slug("world") == "world"

    def test_path_traversal_prevention(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_slug("../parent")
        with pytest.raises(ValueError, match="path traversal"):
            validate_slug("/absolute")
        with pytest.raises(ValueError, match="path traversal"):
            validate_slug("foo/../bar")
        with pytest.raises(ValueError, match="path traversal"):
            validate_slug("test\\path")

    def test_invalid_prefixes(self):
        with pytest.raises(ValueError, match="cannot start with dot or dash"):
            validate_slug(".hidden")
        with pytest.raises(ValueError, match="cannot start with dot or dash"):
            validate_slug("-test")

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="lowercase letters, numbers, and hyphens"):
            validate_slug("Test")
        with pytest.raises(ValueError, match="lowercase letters, numbers, and hyphens"):
            validate_slug("my_world")
        with pytest.raises(ValueError, match="lowercase letters, numbers, and hyphens"):
            validate_slug("my world")
        with pytest.raises(ValueError, match="lowercase letters, numbers, and hyphens"):
            validate_slug("test!")

    def test_empty_slug(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_slug("")

    def test_length_limits(self):
        valid = "a" * 100
        assert validate_slug(valid) == valid

        too_long = "a" * 101
        with pytest.raises(ValueError, match="too long"):
            validate_slug(too_long)

    def test_hyphens_allowed_in_middle(self):
        assert validate_slug("my-long-world-name") == "my-long-world-name"
        assert validate_slug("test-123-abc") == "test-123-abc"
