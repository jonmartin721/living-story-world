from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..settings import load_user_settings, save_user_settings, UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def validate_api_key(key: str, provider: str, prefix: Optional[str] = None, min_length: int = 20, max_length: int = 200) -> str:
    """Validate API key format.

    Args:
        key: The API key to validate
        provider: Provider name (for error messages)
        prefix: Expected key prefix (e.g., "sk-" for OpenAI)
        min_length: Minimum acceptable key length
        max_length: Maximum acceptable key length

    Returns:
        The validated key (stripped of whitespace)

    Raises:
        HTTPException: If key format is invalid
    """
    key = key.strip()

    if not key:
        raise HTTPException(status_code=400, detail=f"{provider} API key cannot be empty")

    if len(key) < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"{provider} API key too short (minimum {min_length} characters)"
        )

    if len(key) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"{provider} API key too long (maximum {max_length} characters)"
        )

    if prefix and not key.startswith(prefix):
        raise HTTPException(
            status_code=400,
            detail=f"{provider} API key must start with '{prefix}'"
        )

    return key


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
    text_provider: Optional[str] = Field(None, max_length=50)
    image_provider: Optional[str] = Field(None, max_length=50)

    # API keys
    openai_api_key: Optional[str] = Field(None, max_length=200)
    together_api_key: Optional[str] = Field(None, max_length=200)
    huggingface_api_key: Optional[str] = Field(None, max_length=200)
    groq_api_key: Optional[str] = Field(None, max_length=200)
    replicate_api_token: Optional[str] = Field(None, max_length=200)
    fal_api_key: Optional[str] = Field(None, max_length=200)

    # Global instructions and defaults
    global_instructions: Optional[str] = Field(None, max_length=10000)
    default_style_pack: Optional[str] = Field(None, max_length=100)
    default_preset: Optional[str] = Field(None, max_length=100)
    default_text_model: Optional[str] = Field(None, max_length=100)
    default_image_model: Optional[str] = Field(None, max_length=100)


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

    # Update API keys (with validation)
    if request.openai_api_key is not None:
        validated_key = validate_api_key(request.openai_api_key, "OpenAI", prefix="sk-")
        settings.openai_api_key = validated_key
        os.environ["OPENAI_API_KEY"] = validated_key

    if request.together_api_key is not None:
        validated_key = validate_api_key(request.together_api_key, "Together AI")
        settings.together_api_key = validated_key
        os.environ["TOGETHER_API_KEY"] = validated_key

    if request.huggingface_api_key is not None:
        validated_key = validate_api_key(request.huggingface_api_key, "HuggingFace", prefix="hf_")
        settings.huggingface_api_key = validated_key
        os.environ["HUGGINGFACE_API_KEY"] = validated_key

    if request.groq_api_key is not None:
        validated_key = validate_api_key(request.groq_api_key, "Groq", prefix="gsk_")
        settings.groq_api_key = validated_key
        os.environ["GROQ_API_KEY"] = validated_key

    if request.replicate_api_token is not None:
        validated_key = validate_api_key(request.replicate_api_token, "Replicate", prefix="r8_")
        settings.replicate_api_token = validated_key
        os.environ["REPLICATE_API_TOKEN"] = validated_key

    if request.fal_api_key is not None:
        validated_key = validate_api_key(request.fal_api_key, "FAL")
        settings.fal_api_key = validated_key
        os.environ["FAL_KEY"] = validated_key

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
