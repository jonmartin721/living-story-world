"""Tests for image generation functionality."""
import json
import pytest
from unittest.mock import MagicMock, patch, Mock

from living_storyworld.image import (
    safe_download_image,
    _cache_key,
    generate_scene_image,
    _append_media_index,
)


class TestSafeDownloadImage:
    """Test safe image downloading with security checks."""

    def test_invalid_url_scheme(self, tmp_path):
        """Test rejection of invalid URL schemes."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            safe_download_image("ftp://example.com/image.png", tmp_path / "out.png")

    def test_file_scheme_rejected(self, tmp_path):
        """Test file:// scheme is rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            safe_download_image("file:///etc/passwd", tmp_path / "out.png")

    def test_successful_download(self, tmp_path):
        """Test successful image download."""
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "image/png",
            "Content-Length": "1000",
        }
        mock_response.iter_content = Mock(return_value=[b"fake image data"])

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            output_path = tmp_path / "downloaded.png"
            result = safe_download_image("https://example.com/image.png", output_path)

            assert result == output_path
            assert output_path.exists()
            assert output_path.read_bytes() == b"fake image data"

    def test_download_timeout(self, tmp_path):
        """Test download timeout handling."""
        with patch("requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")

            with pytest.raises(RuntimeError, match="Download timed out"):
                safe_download_image("https://example.com/image.png", tmp_path / "out.png")

    def test_download_request_error(self, tmp_path):
        """Test network error handling."""
        with patch("requests.get") as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.RequestException("Network error")

            with pytest.raises(RuntimeError, match="Download failed"):
                safe_download_image("https://example.com/image.png", tmp_path / "out.png")

    def test_file_too_large_by_header(self, tmp_path):
        """Test rejection of files too large based on Content-Length."""
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "image/png",
            "Content-Length": str(100 * 1024 * 1024),  # 100 MB
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(ValueError, match="File too large"):
                safe_download_image("https://example.com/image.png", tmp_path / "out.png", max_size_mb=50)

    def test_file_too_large_during_download(self, tmp_path):
        """Test rejection when file exceeds size during download."""
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "image/png",
            "Content-Length": "100",  # Lie about size
        }
        # Return chunks that exceed the limit
        mock_response.iter_content = Mock(return_value=[b"x" * (10 * 1024 * 1024) for _ in range(10)])

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            output_path = tmp_path / "out.png"
            with pytest.raises(ValueError, match="exceeded size limit"):
                safe_download_image("https://example.com/image.png", output_path, max_size_mb=1)

            # Verify partial file was cleaned up
            assert not output_path.exists()

    def test_non_image_content_type_warning(self, tmp_path):
        """Test warning for non-image content types."""
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "text/html",
            "Content-Length": "100",
        }
        mock_response.iter_content = Mock(return_value=[b"content"])

        with patch("requests.get") as mock_get, \
             patch("logging.warning") as mock_warn:
            mock_get.return_value = mock_response

            safe_download_image("https://example.com/file.html", tmp_path / "out.png")

            # Should log warning but still download
            mock_warn.assert_called_once()

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directories are created."""
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "image/png",
            "Content-Length": "100",
        }
        mock_response.iter_content = Mock(return_value=[b"data"])

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            output_path = tmp_path / "subdir" / "nested" / "image.png"
            safe_download_image("https://example.com/img.png", output_path)

            assert output_path.exists()
            assert output_path.parent.is_dir()


class TestCacheKey:
    """Test cache key generation."""

    def test_same_inputs_same_key(self):
        """Test same inputs produce same cache key."""
        key1 = _cache_key("scene", "storybook-ink", "A forest", "16:9", "flux-dev")
        key2 = _cache_key("scene", "storybook-ink", "A forest", "16:9", "flux-dev")

        assert key1 == key2

    def test_different_prompts_different_keys(self):
        """Test different prompts produce different keys."""
        key1 = _cache_key("scene", "storybook-ink", "A forest", "16:9", "flux-dev")
        key2 = _cache_key("scene", "storybook-ink", "A desert", "16:9", "flux-dev")

        assert key1 != key2

    def test_different_styles_different_keys(self):
        """Test different styles produce different keys."""
        key1 = _cache_key("scene", "storybook-ink", "A forest", "16:9", "flux-dev")
        key2 = _cache_key("scene", "pixel-rpg", "A forest", "16:9", "flux-dev")

        assert key1 != key2

    def test_different_aspect_ratios_different_keys(self):
        """Test different aspect ratios produce different keys."""
        key1 = _cache_key("scene", "storybook-ink", "A forest", "16:9", "flux-dev")
        key2 = _cache_key("scene", "storybook-ink", "A forest", "1:1", "flux-dev")

        assert key1 != key2

    def test_key_is_hex_string(self):
        """Test cache key is hexadecimal string."""
        key = _cache_key("scene", "storybook-ink", "A forest", "16:9", "flux-dev")

        assert isinstance(key, str)
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)


class TestGenerateSceneImage:
    """Test scene image generation."""

    def test_uses_cached_image(self, tmp_path):
        """Test that existing cached image is reused."""
        scenes_dir = tmp_path / "media" / "scenes"
        scenes_dir.mkdir(parents=True)

        # Create a "cached" image
        cached_file = scenes_dir / "scene-0001-abcd1234.png"
        cached_file.write_bytes(b"cached image")

        with patch("living_storyworld.image._cache_key") as mock_cache_key, \
             patch("living_storyworld.image.load_user_settings") as mock_settings:
            mock_cache_key.return_value = "abcd1234"
            mock_settings.return_value = MagicMock(image_provider="pollinations")

            result = generate_scene_image(
                tmp_path,
                "flux",
                "storybook-ink",
                "A forest scene",
                chapter_num=1,
            )

            # Should return cached file without calling provider
            assert result == cached_file
            assert result.read_bytes() == b"cached image"

    def test_generates_new_image(self, tmp_path):
        """Test generating new image when cache miss."""
        scenes_dir = tmp_path / "media" / "scenes"
        scenes_dir.mkdir(parents=True)
        (tmp_path / "media").mkdir(exist_ok=True)

        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.provider = "pollinations"
        mock_result.model = "flux"
        mock_result.estimated_cost = 0.0
        mock_provider.generate.return_value = mock_result

        with patch("living_storyworld.image._cache_key") as mock_cache_key, \
             patch("living_storyworld.image.load_user_settings") as mock_settings, \
             patch("living_storyworld.image.get_image_provider") as mock_get_provider, \
             patch("living_storyworld.image._append_media_index") as mock_append:
            mock_cache_key.return_value = "newkey123"
            mock_settings.return_value = MagicMock(image_provider="pollinations")
            mock_get_provider.return_value = mock_provider

            generate_scene_image(
                tmp_path,
                "flux",
                "storybook-ink",
                "A castle",
                chapter_num=2,
            )

            # Should generate new image
            mock_provider.generate.assert_called_once()
            mock_append.assert_called_once()

            # Verify prompt includes style
            call_args = mock_provider.generate.call_args
            assert "storybook-ink" in call_args[1]["prompt"] or "storybook" in str(call_args)

    def test_bypass_cache(self, tmp_path):
        """Test bypassing cache with bypass_cache=True."""
        scenes_dir = tmp_path / "media" / "scenes"
        scenes_dir.mkdir(parents=True)
        (tmp_path / "media").mkdir(exist_ok=True)

        # Create cached image
        cached_file = scenes_dir / "scene-0001-testkey.png"
        cached_file.write_bytes(b"old")

        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.provider = "pollinations"
        mock_result.model = "flux"
        mock_result.estimated_cost = 0.0
        mock_provider.generate.return_value = mock_result

        with patch("living_storyworld.image._cache_key") as mock_cache_key, \
             patch("living_storyworld.image.load_user_settings") as mock_settings, \
             patch("living_storyworld.image.get_image_provider") as mock_get_provider, \
             patch("living_storyworld.image._append_media_index"):
            mock_cache_key.return_value = "testkey"
            mock_settings.return_value = MagicMock(image_provider="pollinations")
            mock_get_provider.return_value = mock_provider

            result = generate_scene_image(
                tmp_path,
                "flux",
                "storybook-ink",
                "A scene",
                chapter_num=1,
                bypass_cache=True,
            )

            # Should generate new image despite cached version existing
            mock_provider.generate.assert_called_once()

            # Result should have timestamp suffix, not be the cached file
            assert result != cached_file

    def test_provider_fallback_to_pollinations(self, tmp_path):
        """Test fallback to Pollinations when primary provider fails."""
        scenes_dir = tmp_path / "media" / "scenes"
        scenes_dir.mkdir(parents=True)
        (tmp_path / "media").mkdir(exist_ok=True)

        failing_provider = MagicMock()
        failing_provider.generate.side_effect = Exception("Provider failed")

        fallback_provider = MagicMock()
        fallback_result = MagicMock()
        fallback_result.provider = "pollinations"
        fallback_result.model = "flux"
        fallback_result.estimated_cost = 0.0
        fallback_provider.generate.return_value = fallback_result

        with patch("living_storyworld.image._cache_key") as mock_cache_key, \
             patch("living_storyworld.image.load_user_settings") as mock_settings, \
             patch("living_storyworld.image.get_image_provider") as mock_get_provider, \
             patch("living_storyworld.image._append_media_index"):
            mock_cache_key.return_value = "fallback"
            mock_settings.return_value = MagicMock(image_provider="replicate")
            # First call returns failing provider, second call returns fallback
            mock_get_provider.side_effect = [failing_provider, fallback_provider]

            generate_scene_image(
                tmp_path,
                "flux-dev",
                "storybook-ink",
                "A scene",
                chapter_num=1,
            )

            # Should have called both providers
            assert failing_provider.generate.call_count == 1
            assert fallback_provider.generate.call_count == 1

    def test_pollinations_failure_raises(self, tmp_path):
        """Test that Pollinations failure raises (no further fallback)."""
        scenes_dir = tmp_path / "media" / "scenes"
        scenes_dir.mkdir(parents=True)

        failing_provider = MagicMock()
        failing_provider.generate.side_effect = Exception("Pollinations failed")

        with patch("living_storyworld.image._cache_key") as mock_cache_key, \
             patch("living_storyworld.image.load_user_settings") as mock_settings, \
             patch("living_storyworld.image.get_image_provider") as mock_get_provider:
            mock_cache_key.return_value = "pollfail"
            mock_settings.return_value = MagicMock(image_provider="pollinations")
            mock_get_provider.return_value = failing_provider

            with pytest.raises(Exception, match="Pollinations failed"):
                generate_scene_image(
                    tmp_path,
                    "flux",
                    "storybook-ink",
                    "A scene",
                    chapter_num=1,
                )


class TestAppendMediaIndex:
    """Test media index management."""

    def test_create_new_index(self, tmp_path):
        """Test creating new media index."""
        entry = {
            "type": "scene",
            "chapter": 1,
            "file": "media/scenes/scene-0001.png",
        }

        _append_media_index(tmp_path, entry)

        index_file = tmp_path / "media" / "index.json"
        assert index_file.exists()

        data = json.loads(index_file.read_text())
        assert len(data) == 1
        assert data[0]["type"] == "scene"
        assert data[0]["chapter"] == 1

    def test_append_to_existing_index(self, tmp_path):
        """Test appending to existing index."""
        index_file = tmp_path / "media" / "index.json"
        index_file.parent.mkdir(parents=True)

        # Create existing index
        existing = [{"type": "scene", "chapter": 1}]
        index_file.write_text(json.dumps(existing))

        # Append new entry
        new_entry = {"type": "scene", "chapter": 2}
        _append_media_index(tmp_path, new_entry)

        data = json.loads(index_file.read_text())
        assert len(data) == 2
        assert data[0]["chapter"] == 1
        assert data[1]["chapter"] == 2

    def test_handle_corrupted_index(self, tmp_path):
        """Test handling corrupted index file."""
        index_file = tmp_path / "media" / "index.json"
        index_file.parent.mkdir(parents=True)

        # Create corrupted index
        index_file.write_text("{invalid json")

        # Should handle gracefully and create new index
        entry = {"type": "scene", "chapter": 1}
        _append_media_index(tmp_path, entry)

        data = json.loads(index_file.read_text())
        assert len(data) == 1
        assert data[0]["chapter"] == 1
