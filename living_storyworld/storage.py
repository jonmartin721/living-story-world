from __future__ import annotations

import json
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
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(text)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-\s]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value or "world"


def set_current_world(slug: str) -> None:
    write_text(CURRENT_FILE, slug)


def get_current_world() -> Optional[str]:
    if CURRENT_FILE.exists():
        return read_text(CURRENT_FILE).strip() or None
    return None

