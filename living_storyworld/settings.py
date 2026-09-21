from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configuration mapping: settings_attr -> env_var
ENV_VAR_MAPPING = {
    "openai_api_key": "OPENAI_API_KEY",
    "together_api_key": "TOGETHER_API_KEY",
    "huggingface_api_key": "HUGGINGFACE_API_KEY",
    "groq_api_key": "GROQ_API_KEY",
    "gemini_api_key": "GEMINI_API_KEY",
    "openrouter_api_key": "OPENROUTER_API_KEY",
    "replicate_api_token": "REPLICATE_API_TOKEN",
    "fal_api_key": "FAL_KEY",
    "pollinations_api_key": "POLLINATIONS_API_KEY",
    "local_api_key": "LOCAL_API_KEY",
    "horde_api_key": "HORDE_API_KEY",
}


def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "living_storyworld"
    return Path.home() / ".config" / "living_storyworld"


CONFIG_PATH = _config_dir() / "config.json"


@dataclass
class UserSettings:
    text_provider: str = "ollama"
    image_provider: str = "none"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    local_base_url: str = "http://127.0.0.1:1234/v1"
    local_api_key: Optional[str] = None
    local_reasoning_effort: str = "none"
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_workflow: str = ""
    comfyui_prompt_node: str = ""

    # API keys for various providers
    openai_api_key: Optional[str] = None
    together_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    fal_api_key: Optional[str] = None
    pollinations_api_key: Optional[str] = None
    horde_api_key: Optional[str] = None

    # Global instructions (apply to all worlds)
    global_instructions: Optional[str] = None

    # Default preferences
    default_style_pack: str = "storybook-ink"
    default_preset: str = "cozy-adventure"
    default_text_model: str = ""
    default_image_model: str = ""
    default_maturity_level: str = "general"

    # Reader preferences
    reader_font_family: str = "Georgia"  # serif, sans-serif, or Georgia
    reader_font_size: str = "medium"  # small, medium, large, xl


def load_user_settings() -> UserSettings:
    """Load user settings from config file.

    Returns default settings if file doesn't exist or is corrupted.
    """
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Filter out unknown fields to support forward compatibility
            valid_fields = {f.name for f in UserSettings.__dataclass_fields__.values()}
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            return UserSettings(**filtered_data)
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse settings file {CONFIG_PATH}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error loading settings: {e}")

    return UserSettings()


def save_user_settings(s: UserSettings) -> None:
    """Save user settings to config file.

    SECURITY WARNING: API keys stored in plain text. Attempts to set
    file permissions to 0o600 (user read/write only) but logs warning if fails.
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Using 0o600 for security but this doesn't work great on Windows
        # TODO: investigate better cross-platform solution
        if not CONFIG_PATH.exists():
            CONFIG_PATH.touch(mode=0o600)
        CONFIG_PATH.chmod(0o600)
    except Exception as e:
        logging.warning(
            f"Failed to set restrictive permissions (0o600) on {CONFIG_PATH}: {e}. "
            "API keys may be readable by other users on this system!"
        )

    CONFIG_PATH.write_text(json.dumps(asdict(s), indent=2), encoding="utf-8")


def ensure_api_key_from_settings(settings: Optional[UserSettings] = None) -> bool:
    """Ensure OPENAI_API_KEY is available in env; hydrate from settings if present.
    Returns True if a key is present after this call.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return True
    s = settings or load_user_settings()
    if s.openai_api_key:
        os.environ["OPENAI_API_KEY"] = s.openai_api_key
        return True
    return False


def ensure_provider_api_keys(settings: Optional[UserSettings] = None) -> None:
    """Ensure all provider API keys are loaded into environment from settings."""
    s = settings or load_user_settings()

    # Set API keys from settings if not already in environment
    for settings_attr, env_var in ENV_VAR_MAPPING.items():
        key_value = getattr(s, settings_attr, None)
        if key_value and not os.environ.get(env_var):
            os.environ[env_var] = key_value


def get_api_key_for_provider(
    provider: str, settings: Optional[UserSettings] = None
) -> Optional[str]:
    """Get API key for a specific provider from settings or environment.

    Args:
        provider: Provider name (e.g., "openai", "together", "replicate", "openrouter")
        settings: Optional UserSettings instance (loads if not provided)

    Returns:
        API key string or None if not found
    """
    s = settings or load_user_settings()

    # Check environment first, then settings
    key_map = {
        "horde": (os.environ.get("HORDE_API_KEY"), s.horde_api_key),
        "openai": (os.environ.get("OPENAI_API_KEY"), s.openai_api_key),
        "together": (os.environ.get("TOGETHER_API_KEY"), s.together_api_key),
        "huggingface": (os.environ.get("HUGGINGFACE_API_KEY"), s.huggingface_api_key),
        "groq": (os.environ.get("GROQ_API_KEY"), s.groq_api_key),
        "openrouter": (os.environ.get("OPENROUTER_API_KEY"), s.openrouter_api_key),
        "gemini": (os.environ.get("GEMINI_API_KEY"), s.gemini_api_key),
        "replicate": (os.environ.get("REPLICATE_API_TOKEN"), s.replicate_api_token),
        "fal": (os.environ.get("FAL_KEY"), s.fal_api_key),
        "pollinations": (os.environ.get("POLLINATIONS_API_KEY"), s.pollinations_api_key),
        "local": (os.environ.get("LOCAL_API_KEY"), s.local_api_key),
    }

    env_key, settings_key = key_map.get(provider, (None, None))
    return env_key or settings_key


def get_available_text_providers(settings: Optional[UserSettings] = None) -> list[str]:
    """Get list of text providers that have API keys configured.

    Returns providers in preferred order for fallback:
    1. Primary provider (from settings)
    2. Other free/cheap providers (groq, gemini)
    3. Paid providers (openai, together, openrouter, huggingface)

    Args:
        settings: Optional UserSettings instance (loads if not provided)

    Returns:
        List of provider names that have API keys configured
    """
    s = settings or load_user_settings()

    # A saved key is not permission to switch providers or start billing.
    if s.text_provider in {"ollama", "local"} or get_api_key_for_provider(s.text_provider, s):
        return [s.text_provider]
    return []
