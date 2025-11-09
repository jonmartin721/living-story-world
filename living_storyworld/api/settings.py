from __future__ import annotations

import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..settings import load_user_settings, save_user_settings, UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    has_openai_key: bool
    has_replicate_token: bool
    default_style_pack: str
    default_preset: str


class SettingsUpdateRequest(BaseModel):
    openai_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    default_style_pack: Optional[str] = None
    default_preset: Optional[str] = None


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current settings (API keys are masked)"""
    settings = load_user_settings()

    # Check environment variables too
    has_openai = bool(settings.openai_api_key or os.environ.get("OPENAI_API_KEY"))
    has_replicate = bool(os.environ.get("REPLICATE_API_TOKEN"))

    return SettingsResponse(
        has_openai_key=has_openai,
        has_replicate_token=has_replicate,
        default_style_pack=settings.default_style_pack,
        default_preset=settings.default_preset
    )


@router.put("")
async def update_settings(request: SettingsUpdateRequest):
    """Update user settings"""
    settings = load_user_settings()

    # Update fields if provided
    if request.openai_api_key is not None:
        settings.openai_api_key = request.openai_api_key
        os.environ["OPENAI_API_KEY"] = request.openai_api_key

    if request.replicate_api_token is not None:
        os.environ["REPLICATE_API_TOKEN"] = request.replicate_api_token

    if request.default_style_pack is not None:
        settings.default_style_pack = request.default_style_pack

    if request.default_preset is not None:
        settings.default_preset = request.default_preset

    save_user_settings(settings)

    return {"message": "Settings updated"}
