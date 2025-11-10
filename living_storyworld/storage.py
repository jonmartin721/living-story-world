from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(os.getcwd())
WORLDS_DIR = ROOT / "worlds"
CURRENT_FILE = ROOT / ".lsw_current"


def ensure_world_dirs(slug: str) -> Dict[str, Path]:
    base = WORLDS_DIR / slug
    (base / "chapters").mkdir(parents=True, exist_ok=True)
    (base / "media" / "scenes").mkdir(parents=True, exist_ok=True)
    (base / "media" / "characters").mkdir(parents=True, exist_ok=True)
    (base / "media" / "items").mkdir(parents=True, exist_ok=True)
    (base / "web").mkdir(parents=True, exist_ok=True)
    return {
        "base": base,
        "chapters": base / "chapters",
        "media": base / "media",
        "web": base / "web",
    }


def write_json(path: Path, data: Any) -> None:
    if is_dataclass(data):
        data = asdict(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_json(path: Path, default: Optional[Any] = None) -> Any:
    """Read JSON from file with error handling.

    Returns default value if file doesn't exist or JSON is invalid.
    """
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from {path}: {e}")
        return default
    except IOError as e:
        logging.error(f"Failed to read file {path}: {e}")
        return default


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(text)


def slugify(value: str) -> str:
    """Convert a string to a safe filesystem slug.

    Security: Prevents path traversal attacks by rejecting dangerous characters.
    """
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-\s]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-") or "world"

    # SECURITY: Prevent path traversal attacks
    if ".." in value or "/" in value or "\\" in value:
        raise ValueError("Invalid slug: contains path traversal characters")
    if value.startswith("."):
        raise ValueError("Invalid slug: cannot start with dot")
    if len(value) > 100:
        raise ValueError("Invalid slug: too long (max 100 characters)")

    return value


def validate_slug(slug: str) -> str:
    """Validate a slug parameter from API/URL to prevent path traversal attacks.

    Security: Strictly validates slugs to ensure they can't escape the worlds directory.

    Args:
        slug: The slug to validate

    Returns:
        The validated slug

    Raises:
        ValueError: If slug is invalid or contains dangerous characters
    """
    if not slug:
        raise ValueError("Slug cannot be empty")

    # SECURITY: Prevent path traversal
    if ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError("Invalid slug: contains path traversal characters")
    if slug.startswith(".") or slug.startswith("-"):
        raise ValueError("Invalid slug: cannot start with dot or dash")
    if not re.match(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[a-z0-9]$", slug):
        raise ValueError("Invalid slug: must contain only lowercase letters, numbers, and hyphens")
    if len(slug) > 100:
        raise ValueError("Invalid slug: too long (max 100 characters)")

    return slug


def set_current_world(slug: str) -> None:
    write_text(CURRENT_FILE, slug)


def get_current_world() -> Optional[str]:
    if CURRENT_FILE.exists():
        return read_text(CURRENT_FILE).strip() or None
    return None

