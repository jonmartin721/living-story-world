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
    openai_api_key: Optional[str] = None
    default_style_pack: str = "storybook-ink"
    default_preset: str = "cozy-adventure"


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

