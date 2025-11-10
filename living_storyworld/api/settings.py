from __future__ import annotations

import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..settings import load_user_settings, save_user_settings, UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    # Provider selections
    text_provider: str
    image_provider: str

    # API key status (masked)
    has_openai_key: bool
    has_together_key: bool
    has_huggingface_key: bool
    has_groq_key: bool
    has_replicate_token: bool
    has_fal_key: bool

    # Global instructions and defaults
    global_instructions: Optional[str]
    default_style_pack: str
    default_preset: str
    default_text_model: str
    default_image_model: str


class SettingsUpdateRequest(BaseModel):
    # Provider selections
    text_provider: Optional[str] = None
    image_provider: Optional[str] = None

    # API keys
    openai_api_key: Optional[str] = None
    together_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    fal_api_key: Optional[str] = None

    # Global instructions and defaults
    global_instructions: Optional[str] = None
    default_style_pack: Optional[str] = None
    default_preset: Optional[str] = None
    default_text_model: Optional[str] = None
    default_image_model: Optional[str] = None


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current settings (API keys are masked)"""
    settings = load_user_settings()

    # Check environment variables and settings for API key status
    has_openai = bool(settings.openai_api_key or os.environ.get("OPENAI_API_KEY"))
    has_together = bool(settings.together_api_key or os.environ.get("TOGETHER_API_KEY"))
    has_huggingface = bool(settings.huggingface_api_key or os.environ.get("HUGGINGFACE_API_KEY"))
    has_groq = bool(settings.groq_api_key or os.environ.get("GROQ_API_KEY"))
    has_replicate = bool(settings.replicate_api_token or os.environ.get("REPLICATE_API_TOKEN"))
    has_fal = bool(settings.fal_api_key or os.environ.get("FAL_KEY"))

    return SettingsResponse(
        text_provider=settings.text_provider,
        image_provider=settings.image_provider,
        has_openai_key=has_openai,
        has_together_key=has_together,
        has_huggingface_key=has_huggingface,
        has_groq_key=has_groq,
        has_replicate_token=has_replicate,
        has_fal_key=has_fal,
        global_instructions=settings.global_instructions,
        default_style_pack=settings.default_style_pack,
        default_preset=settings.default_preset,
        default_text_model=settings.default_text_model,
        default_image_model=settings.default_image_model
    )


@router.put("")
async def update_settings(request: SettingsUpdateRequest):
    """Update user settings"""
    settings = load_user_settings()

    # Update provider selections
    if request.text_provider is not None:
        settings.text_provider = request.text_provider

    if request.image_provider is not None:
        settings.image_provider = request.image_provider

    # Update API keys
    if request.openai_api_key is not None:
        settings.openai_api_key = request.openai_api_key
        os.environ["OPENAI_API_KEY"] = request.openai_api_key

    if request.together_api_key is not None:
        settings.together_api_key = request.together_api_key
        os.environ["TOGETHER_API_KEY"] = request.together_api_key

    if request.huggingface_api_key is not None:
        settings.huggingface_api_key = request.huggingface_api_key
        os.environ["HUGGINGFACE_API_KEY"] = request.huggingface_api_key

    if request.groq_api_key is not None:
        settings.groq_api_key = request.groq_api_key
        os.environ["GROQ_API_KEY"] = request.groq_api_key

    if request.replicate_api_token is not None:
        settings.replicate_api_token = request.replicate_api_token
        os.environ["REPLICATE_API_TOKEN"] = request.replicate_api_token

    if request.fal_api_key is not None:
        settings.fal_api_key = request.fal_api_key
        os.environ["FAL_KEY"] = request.fal_api_key

    # Update global instructions
    if request.global_instructions is not None:
        settings.global_instructions = request.global_instructions

    # Update defaults
    if request.default_style_pack is not None:
        settings.default_style_pack = request.default_style_pack

    if request.default_preset is not None:
        settings.default_preset = request.default_preset

    if request.default_text_model is not None:
        settings.default_text_model = request.default_text_model

    if request.default_image_model is not None:
        settings.default_image_model = request.default_image_model

    save_user_settings(settings)

    return {"message": "Settings updated"}
