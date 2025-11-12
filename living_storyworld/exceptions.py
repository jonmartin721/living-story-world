"""Custom exceptions for Living Storyworld with user-friendly error messages."""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LivingStoryworldError(Exception):
    """Base exception for all Living Storyworld errors."""

    def __init__(self, message: str, user_message: Optional[str] = None, help_text: Optional[str] = None):
        """Initialize error with technical and user-friendly messages.

        Args:
            message: Technical error message for logs
            user_message: User-friendly message to display
            help_text: Optional help/suggestion text
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.help_text = help_text

        # Log to console with appropriate level
        self._log_error()

    def _log_error(self):
        """Log error to console with user-friendly formatting."""
        logger.error(f"❌ {self.user_message}")
        if self.help_text:
            logger.info(f"💡 {self.help_text}")
        logger.debug(f"Technical details: {self.message}")


class APIError(LivingStoryworldError):
    """Base class for API-related errors."""

    def __init__(self, provider: str, message: str, status_code: Optional[int] = None, **kwargs):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message, **kwargs)


class RateLimitError(APIError):
    """Rate limit exceeded error."""

    def __init__(self, provider: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after

        message = f"{provider} rate limit exceeded"
        if retry_after:
            message += f" (retry after {retry_after}s)"

        user_message = f"Rate limit reached for {provider}"
        help_text = "Try again in a few minutes, or use a different provider in Settings"
        if retry_after:
            help_text = f"Wait {retry_after} seconds and try again, or switch to a different provider"

        super().__init__(
            provider=provider,
            message=message,
            status_code=429,
            user_message=user_message,
            help_text=help_text
        )


class AuthenticationError(APIError):
    """API authentication failed error."""

    def __init__(self, provider: str, details: Optional[str] = None):
        message = f"{provider} authentication failed"
        if details:
            message += f": {details}"

        user_message = f"API key invalid or missing for {provider}"
        help_text = f"Check your {provider} API key in Settings. Make sure it's valid and has the correct permissions."

        super().__init__(
            provider=provider,
            message=message,
            status_code=401,
            user_message=user_message,
            help_text=help_text
        )


class QuotaExceededError(APIError):
    """API quota/credits exceeded error."""

    def __init__(self, provider: str):
        message = f"{provider} quota or credits exceeded"
        user_message = f"You've run out of credits for {provider}"
        help_text = f"Add more credits to your {provider} account, or switch to a different provider (like Gemini which has a free tier)"

        super().__init__(
            provider=provider,
            message=message,
            status_code=402,
            user_message=user_message,
            help_text=help_text
        )


class ContentPolicyError(APIError):
    """Content rejected by API policy/safety filters."""

    def __init__(self, provider: str, details: Optional[str] = None):
        message = f"{provider} rejected content"
        if details:
            message += f": {details}"

        user_message = f"{provider}'s content policy blocked this request"
        help_text = "Try adjusting the story theme or prompt. Some providers have stricter content policies than others."

        super().__init__(
            provider=provider,
            message=message,
            status_code=400,
            user_message=user_message,
            help_text=help_text
        )


class ServerError(APIError):
    """API server error (5xx)."""

    def __init__(self, provider: str, status_code: int, details: Optional[str] = None):
        message = f"{provider} server error ({status_code})"
        if details:
            message += f": {details}"

        user_message = f"{provider} is experiencing issues (error {status_code})"
        help_text = f"Try again in a few minutes, or temporarily use a different provider"

        super().__init__(
            provider=provider,
            message=message,
            status_code=status_code,
            user_message=user_message,
            help_text=help_text
        )


class TimeoutError(APIError):
    """API request timed out."""

    def __init__(self, provider: str, timeout: int):
        message = f"{provider} request timed out after {timeout}s"
        user_message = f"Request to {provider} timed out"
        help_text = f"The provider took too long to respond. Try again, or use a faster model."

        super().__init__(
            provider=provider,
            message=message,
            user_message=user_message,
            help_text=help_text
        )


class NetworkError(APIError):
    """Network connectivity error."""

    def __init__(self, provider: str, details: Optional[str] = None):
        message = f"Network error connecting to {provider}"
        if details:
            message += f": {details}"

        user_message = f"Cannot connect to {provider}"
        help_text = "Check your internet connection and try again"

        super().__init__(
            provider=provider,
            message=message,
            user_message=user_message,
            help_text=help_text
        )


class InvalidModelError(APIError):
    """Requested model not available or invalid."""

    def __init__(self, provider: str, model: str, available_models: Optional[list[str]] = None):
        self.model = model
        self.available_models = available_models

        message = f"Invalid model '{model}' for {provider}"
        user_message = f"Model '{model}' is not available for {provider}"

        help_text = "Check the model name in your world configuration"
        if available_models:
            help_text += f". Available models: {', '.join(available_models[:3])}"

        super().__init__(
            provider=provider,
            message=message,
            status_code=400,
            user_message=user_message,
            help_text=help_text
        )


def handle_api_error(error: Exception, provider: str) -> LivingStoryworldError:
    """Convert generic exceptions to user-friendly errors.

    Args:
        error: The original exception
        provider: Name of the provider (for error messages)

    Returns:
        LivingStoryworldError subclass with helpful messages
    """
    import requests

    # Handle OpenAI SDK errors
    try:
        from openai import APIError as OpenAIAPIError, RateLimitError as OpenAIRateLimit, AuthenticationError as OpenAIAuthError
        from openai import APITimeoutError, APIConnectionError

        if isinstance(error, OpenAIRateLimit):
            return RateLimitError(provider)
        elif isinstance(error, OpenAIAuthError):
            return AuthenticationError(provider, str(error))
        elif isinstance(error, APITimeoutError):
            return TimeoutError(provider, timeout=60)
        elif isinstance(error, APIConnectionError):
            return NetworkError(provider, str(error))
        elif isinstance(error, OpenAIAPIError):
            # Generic OpenAI API error
            status_code = getattr(error, 'status_code', None)
            if status_code:
                if status_code >= 500:
                    return ServerError(provider, status_code, str(error))
                elif status_code == 400:
                    return ContentPolicyError(provider, str(error))
            return APIError(provider, str(error), status_code=status_code,
                          user_message=f"API error from {provider}", help_text="Check your request and try again")
    except ImportError:
        pass  # OpenAI SDK not installed, skip these checks

    # Handle requests library errors
    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code

        # Try to get error details from response
        details = None
        try:
            error_data = error.response.json()
            details = error_data.get('error', {}).get('message') or error_data.get('message')
        except Exception:
            pass

        if status_code == 429:
            # Rate limit
            retry_after = None
            if 'Retry-After' in error.response.headers:
                try:
                    retry_after = int(error.response.headers['Retry-After'])
                except ValueError:
                    pass
            return RateLimitError(provider, retry_after)

        elif status_code in (401, 403):
            # Authentication error
            return AuthenticationError(provider, details)

        elif status_code == 402:
            # Payment/quota error
            return QuotaExceededError(provider)

        elif status_code == 400:
            # Bad request - could be content policy
            if details and any(word in details.lower() for word in ['policy', 'safety', 'inappropriate', 'content']):
                return ContentPolicyError(provider, details)
            return APIError(provider, f"Invalid request: {details or 'Unknown error'}", status_code=400,
                          user_message=f"Invalid request to {provider}", help_text="Check your request parameters")

        elif status_code >= 500:
            # Server error
            return ServerError(provider, status_code, details)

    elif isinstance(error, requests.exceptions.Timeout):
        return TimeoutError(provider, timeout=30)  # Default timeout

    elif isinstance(error, requests.exceptions.ConnectionError):
        return NetworkError(provider, str(error))

    elif isinstance(error, requests.exceptions.RequestException):
        return NetworkError(provider, str(error))

    # For unknown errors, wrap in generic APIError
    return APIError(
        provider=provider,
        message=f"Unexpected error: {str(error)}",
        user_message=f"Unexpected error with {provider}",
        help_text="Try again or use a different provider"
    )
