"""Tests for API error handling and user-friendly error messages."""

import pytest
from unittest.mock import Mock, patch
from living_storyworld.exceptions import (
    RateLimitError,
    AuthenticationError,
    QuotaExceededError,
    ContentPolicyError,
    ServerError,
    TimeoutError,
    NetworkError,
    InvalidModelError,
    handle_api_error
)


class TestExceptionMessages:
    """Test that exceptions have helpful user messages."""

    def test_rate_limit_error_message(self):
        """Test rate limit error has helpful message."""
        error = RateLimitError("OpenAI", retry_after=60)
        assert "Rate limit reached" in error.user_message
        assert error.help_text is not None
        assert "60" in error.help_text or "different provider" in error.help_text

    def test_authentication_error_message(self):
        """Test authentication error has helpful message."""
        error = AuthenticationError("OpenAI")
        assert "API key" in error.user_message
        assert "Settings" in error.help_text

    def test_quota_exceeded_error_message(self):
        """Test quota error has helpful message."""
        error = QuotaExceededError("OpenAI")
        assert "credits" in error.user_message or "quota" in error.user_message
        assert "free tier" in error.help_text or "different provider" in error.help_text

    def test_content_policy_error_message(self):
        """Test content policy error has helpful message."""
        error = ContentPolicyError("OpenAI")
        assert "policy" in error.user_message
        assert "adjust" in error.help_text or "stricter" in error.help_text

    def test_server_error_message(self):
        """Test server error has helpful message."""
        error = ServerError("OpenAI", 503)
        assert "503" in error.user_message
        assert "Try again" in error.help_text or "different provider" in error.help_text

    def test_timeout_error_message(self):
        """Test timeout error has helpful message."""
        error = TimeoutError("OpenAI", timeout=30)
        assert ("timed out" in error.user_message or "timeout" in error.user_message)
        assert ("Try again" in error.help_text or "try again" in error.help_text)

    def test_network_error_message(self):
        """Test network error has helpful message."""
        error = NetworkError("OpenAI")
        assert "connect" in error.user_message or "network" in error.user_message.lower()
        assert "internet" in error.help_text or "connection" in error.help_text

    def test_invalid_model_error_message(self):
        """Test invalid model error has helpful message."""
        error = InvalidModelError("OpenAI", "gpt-99", ["gpt-4", "gpt-3.5"])
        assert "gpt-99" in error.user_message
        assert "not available" in error.user_message
        assert error.help_text is not None


class TestRequestsErrorHandling:
    """Test conversion of requests library errors."""

    def test_handle_http_429_rate_limit(self):
        """Test 429 status code converts to RateLimitError."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {}

        error = requests.exceptions.HTTPError(response=mock_response)
        converted = handle_api_error(error, "TestProvider")

        assert isinstance(converted, RateLimitError)
        assert converted.provider == "TestProvider"

    def test_handle_http_401_authentication(self):
        """Test 401 status code converts to AuthenticationError."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}

        error = requests.exceptions.HTTPError(response=mock_response)
        converted = handle_api_error(error, "TestProvider")

        assert isinstance(converted, AuthenticationError)

    def test_handle_http_402_quota(self):
        """Test 402 status code converts to QuotaExceededError."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 402
        mock_response.json.return_value = {}

        error = requests.exceptions.HTTPError(response=mock_response)
        converted = handle_api_error(error, "TestProvider")

        assert isinstance(converted, QuotaExceededError)

    def test_handle_http_500_server_error(self):
        """Test 5xx status codes convert to ServerError."""
        import requests

        for status in [500, 502, 503, 504]:
            mock_response = Mock()
            mock_response.status_code = status
            mock_response.json.return_value = {}

            error = requests.exceptions.HTTPError(response=mock_response)
            converted = handle_api_error(error, "TestProvider")

            assert isinstance(converted, ServerError)
            assert converted.status_code == status

    def test_handle_timeout_error(self):
        """Test timeout errors."""
        import requests

        error = requests.exceptions.Timeout()
        converted = handle_api_error(error, "TestProvider")

        assert isinstance(converted, TimeoutError)

    def test_handle_connection_error(self):
        """Test connection errors."""
        import requests

        error = requests.exceptions.ConnectionError()
        converted = handle_api_error(error, "TestProvider")

        assert isinstance(converted, NetworkError)

    def test_handle_retry_after_header(self):
        """Test rate limit with Retry-After header."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}

        error = requests.exceptions.HTTPError(response=mock_response)
        converted = handle_api_error(error, "TestProvider")

        assert isinstance(converted, RateLimitError)
        assert converted.retry_after == 120


class TestOpenAIErrorHandling:
    """Test conversion of OpenAI SDK errors."""

    @pytest.mark.skipif(True, reason="Requires OpenAI SDK - tested in integration")
    def test_handle_openai_rate_limit(self):
        """Test OpenAI rate limit error."""
        try:
            from openai import RateLimitError as OpenAIRateLimit

            error = OpenAIRateLimit("Rate limit exceeded")
            converted = handle_api_error(error, "OpenAI")

            assert isinstance(converted, RateLimitError)
        except ImportError:
            pytest.skip("OpenAI SDK not installed")

    @pytest.mark.skipif(True, reason="Requires OpenAI SDK - tested in integration")
    def test_handle_openai_auth_error(self):
        """Test OpenAI authentication error."""
        try:
            from openai import AuthenticationError as OpenAIAuthError

            error = OpenAIAuthError("Invalid API key")
            converted = handle_api_error(error, "OpenAI")

            assert isinstance(converted, AuthenticationError)
        except ImportError:
            pytest.skip("OpenAI SDK not installed")


class TestErrorMessageConsoleOutput:
    """Test that errors are logged to console."""

    def test_error_logs_to_console(self, caplog):
        """Test that creating an error logs to console."""
        import logging
        caplog.set_level(logging.ERROR)

        RateLimitError("OpenAI")

        # Check that error was logged
        assert len(caplog.records) > 0
        assert any("Rate limit" in record.message for record in caplog.records)

    def test_error_includes_help_text_in_logs(self, caplog):
        """Test that help text is logged."""
        import logging
        caplog.set_level(logging.INFO)

        AuthenticationError("OpenAI")

        # Should have both ERROR (user message) and INFO (help text) logs
        assert any(record.levelname == "ERROR" for record in caplog.records)
        assert any(record.levelname == "INFO" for record in caplog.records)


class TestProviderErrorPropagation:
    """Test that provider errors are converted properly."""

    def test_openai_provider_invalid_model(self):
        """Test OpenAI provider handles invalid model."""
        from living_storyworld.providers.text import OpenAIProvider
        from living_storyworld.exceptions import InvalidModelError

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = OpenAIProvider()

            with pytest.raises(InvalidModelError) as exc_info:
                provider.generate([{"role": "user", "content": "test"}], model="invalid-model-9999")

            assert "invalid-model-9999" in str(exc_info.value.user_message).lower()
            assert exc_info.value.help_text is not None

    @patch('requests.get')
    def test_pollinations_provider_network_error(self, mock_get):
        """Test Pollinations provider handles network errors."""
        from living_storyworld.providers.image import PollinationsProvider
        from living_storyworld.exceptions import NetworkError
        from pathlib import Path
        import requests

        provider = PollinationsProvider()

        # Simulate connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        with pytest.raises(NetworkError) as exc_info:
            provider.generate("test prompt", Path("/tmp/test.png"))

        assert exc_info.value.provider == "Pollinations"
        assert "connect" in exc_info.value.user_message.lower() or "network" in exc_info.value.user_message.lower()

    @patch('requests.get')
    def test_pollinations_provider_timeout(self, mock_get):
        """Test Pollinations provider handles timeouts."""
        from living_storyworld.providers.image import PollinationsProvider
        from living_storyworld.exceptions import TimeoutError as LSTimeoutError
        from pathlib import Path
        import requests

        provider = PollinationsProvider()

        # Simulate timeout
        mock_get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(LSTimeoutError) as exc_info:
            provider.generate("test prompt", Path("/tmp/test.png"))

        msg = exc_info.value.user_message.lower()
        assert "timed out" in msg or "timeout" in msg


class TestErrorMessageFormatting:
    """Test error message formatting and clarity."""

    def test_user_messages_are_clear(self):
        """Test that user messages are human-readable."""
        errors = [
            RateLimitError("OpenAI"),
            AuthenticationError("OpenAI"),
            QuotaExceededError("OpenAI"),
            ServerError("OpenAI", 503),
            NetworkError("OpenAI"),
        ]

        for error in errors:
            # User messages should be clear, not technical
            assert error.user_message != error.message
            # Should not contain technical jargon
            assert "HTTPError" not in error.user_message
            assert "status_code" not in error.user_message

    def test_help_text_provides_actionable_advice(self):
        """Test that help text gives users actions to take."""
        errors = [
            RateLimitError("OpenAI"),
            AuthenticationError("OpenAI"),
            QuotaExceededError("OpenAI"),
            ServerError("OpenAI", 503),
        ]

        for error in errors:
            assert error.help_text is not None
            # Should suggest an action
            assert any(word in error.help_text.lower() for word in
                      ['try', 'check', 'wait', 'switch', 'add', 'adjust', 'use'])
