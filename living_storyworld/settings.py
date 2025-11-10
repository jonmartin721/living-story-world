from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "living_storyworld"
    return Path.home() / ".config" / "living_storyworld"


CONFIG_PATH = _config_dir() / "config.json"


@dataclass
class UserSettings:
    # API provider selections
    text_provider: str = "openai"
    image_provider: str = "replicate"

    # API keys for various providers
    openai_api_key: Optional[str] = None
    together_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    fal_api_key: Optional[str] = None

    # Global instructions (apply to all worlds)
    global_instructions: Optional[str] = None

    # Default preferences
    default_style_pack: str = "storybook-ink"
    default_preset: str = "cozy-adventure"
    default_text_model: str = "gpt-4o-mini"
    default_image_model: str = "flux-dev"


def load_user_settings() -> UserSettings:
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return UserSettings(**data)
    except Exception:
        pass
    return UserSettings()


def save_user_settings(s: UserSettings) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # best-effort permissions
    try:
        # create with 0o600 if not exists
        if not CONFIG_PATH.exists():
            CONFIG_PATH.touch(mode=0o600)
        CONFIG_PATH.chmod(0o600)
    except Exception:
        pass
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
    if s.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = s.openai_api_key

    if s.together_api_key and not os.environ.get("TOGETHER_API_KEY"):
        os.environ["TOGETHER_API_KEY"] = s.together_api_key

    if s.huggingface_api_key and not os.environ.get("HUGGINGFACE_API_KEY"):
        os.environ["HUGGINGFACE_API_KEY"] = s.huggingface_api_key

    if s.groq_api_key and not os.environ.get("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = s.groq_api_key

    if s.replicate_api_token and not os.environ.get("REPLICATE_API_TOKEN"):
        os.environ["REPLICATE_API_TOKEN"] = s.replicate_api_token

    if s.fal_api_key and not os.environ.get("FAL_KEY"):
        os.environ["FAL_KEY"] = s.fal_api_key


def get_api_key_for_provider(provider: str, settings: Optional[UserSettings] = None) -> Optional[str]:
    """Get API key for a specific provider from settings or environment.

    Args:
        provider: Provider name (e.g., "openai", "together", "replicate")
        settings: Optional UserSettings instance (loads if not provided)

    Returns:
        API key string or None if not found
    """
    s = settings or load_user_settings()

    # Check environment first, then settings
    key_map = {
        "openai": (os.environ.get("OPENAI_API_KEY"), s.openai_api_key),
        "together": (os.environ.get("TOGETHER_API_KEY"), s.together_api_key),
        "huggingface": (os.environ.get("HUGGINGFACE_API_KEY"), s.huggingface_api_key),
        "groq": (os.environ.get("GROQ_API_KEY"), s.groq_api_key),
        "replicate": (os.environ.get("REPLICATE_API_TOKEN"), s.replicate_api_token),
        "fal": (os.environ.get("FAL_KEY"), s.fal_api_key),
    }

    env_key, settings_key = key_map.get(provider, (None, None))
    return env_key or settings_key

