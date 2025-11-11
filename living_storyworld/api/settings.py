from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ..settings import load_user_settings, save_user_settings, UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Configuration for API keys: (settings_attr, env_var, display_name, prefix)
API_KEY_CONFIG = {
    'openai': ('openai_api_key', 'OPENAI_API_KEY', 'OpenAI', 'sk-'),
    'together': ('together_api_key', 'TOGETHER_API_KEY', 'Together AI', None),
    'huggingface': ('huggingface_api_key', 'HUGGINGFACE_API_KEY', 'HuggingFace', 'hf_'),
    'groq': ('groq_api_key', 'GROQ_API_KEY', 'Groq', 'gsk_'),
    'openrouter': ('openrouter_api_key', 'OPENROUTER_API_KEY', 'OpenRouter', 'sk-or-'),
    'gemini': ('gemini_api_key', 'GEMINI_API_KEY', 'Gemini', None),
    'replicate': ('replicate_api_token', 'REPLICATE_API_TOKEN', 'Replicate', 'r8_'),
    'fal': ('fal_api_key', 'FAL_KEY', 'FAL', None),
}


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


def check_api_key_exists(settings: UserSettings, settings_attr: str, env_var: str) -> bool:
    """Check if an API key exists in settings or environment."""
    return bool(getattr(settings, settings_attr, None) or os.environ.get(env_var))


def update_api_key_if_provided(
    settings: UserSettings,
    request_value: Optional[str],
    settings_attr: str,
    env_var: str,
    display_name: str,
    prefix: Optional[str]
) -> None:
    """Update API key in settings and environment if value is provided."""
    if request_value is not None and request_value.strip():
        validated_key = validate_api_key(request_value, display_name, prefix=prefix)
        setattr(settings, settings_attr, validated_key)
        os.environ[env_var] = validated_key


class SettingsResponse(BaseModel):
    # Provider selections
    text_provider: str
    image_provider: str

    # API key status (masked)
    has_openai_key: bool
    has_together_key: bool
    has_huggingface_key: bool
    has_groq_key: bool
    has_openrouter_key: bool
    has_gemini_key: bool
    has_replicate_token: bool
    has_fal_key: bool

    # Global instructions and defaults
    global_instructions: Optional[str]
    default_style_pack: str
    default_preset: str
    default_text_model: str
    default_image_model: str

    # Reader preferences
    reader_font_family: str
    reader_font_size: str


class SettingsUpdateRequest(BaseModel):
    # Provider selections
    text_provider: Optional[str] = Field(None, max_length=50)
    image_provider: Optional[str] = Field(None, max_length=50)

    # API keys
    openai_api_key: Optional[str] = Field(None, max_length=200)
    together_api_key: Optional[str] = Field(None, max_length=200)
    huggingface_api_key: Optional[str] = Field(None, max_length=200)
    groq_api_key: Optional[str] = Field(None, max_length=200)
    openrouter_api_key: Optional[str] = Field(None, max_length=200)
    gemini_api_key: Optional[str] = Field(None, max_length=200)
    replicate_api_token: Optional[str] = Field(None, max_length=200)
    fal_api_key: Optional[str] = Field(None, max_length=200)

    # Global instructions and defaults
    global_instructions: Optional[str] = Field(None, max_length=10000)
    default_style_pack: Optional[str] = Field(None, max_length=100)
    default_preset: Optional[str] = Field(None, max_length=100)
    default_text_model: Optional[str] = Field(None, max_length=100)
    default_image_model: Optional[str] = Field(None, max_length=100)

    # Reader preferences
    reader_font_family: Optional[str] = Field(None, max_length=50)
    reader_font_size: Optional[str] = Field(None, max_length=20)


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current settings (API keys are masked)"""
    settings = load_user_settings()

    # Check API key availability using configuration
    key_status = {}
    for key_id, (settings_attr, env_var, _, _) in API_KEY_CONFIG.items():
        has_key = check_api_key_exists(settings, settings_attr, env_var)
        # Map key_id to response field name
        field_name = f"has_{key_id}_key" if key_id != 'replicate' else "has_replicate_token"
        key_status[field_name] = has_key

    return SettingsResponse(
        text_provider=settings.text_provider,
        image_provider=settings.image_provider,
        **key_status,
        global_instructions=settings.global_instructions,
        default_style_pack=settings.default_style_pack,
        default_preset=settings.default_preset,
        default_text_model=settings.default_text_model,
        default_image_model=settings.default_image_model,
        reader_font_family=settings.reader_font_family,
        reader_font_size=settings.reader_font_size
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

    # Update API keys using configuration
    for key_id, (settings_attr, env_var, display_name, prefix) in API_KEY_CONFIG.items():
        request_value = getattr(request, settings_attr, None)
        update_api_key_if_provided(settings, request_value, settings_attr, env_var, display_name, prefix)

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

    # Update reader preferences
    if request.reader_font_family is not None:
        settings.reader_font_family = request.reader_font_family

    if request.reader_font_size is not None:
        settings.reader_font_size = request.reader_font_size

    save_user_settings(settings)

    return {"message": "Settings updated"}


@router.post("/clear-keys")
async def clear_api_keys():
    """Clear all API keys from settings and environment"""
    settings = load_user_settings()

    # Clear all API keys from settings
    for key_id, (settings_attr, env_var, _, _) in API_KEY_CONFIG.items():
        setattr(settings, settings_attr, None)
        # Also clear from environment if set
        if env_var in os.environ:
            del os.environ[env_var]

    save_user_settings(settings)

    return {"message": "All API keys cleared"}
