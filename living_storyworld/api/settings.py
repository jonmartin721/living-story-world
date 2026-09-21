from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..providers.catalog import (
    IMAGE_PROVIDERS,
    REVIEWED_ON,
    TEXT_PROVIDERS,
    default_model,
)
from ..settings import UserSettings, load_user_settings, save_user_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Configuration for API keys: (settings_attr, env_var, display_name, prefix)
API_KEY_CONFIG = {
    "openai": ("openai_api_key", "OPENAI_API_KEY", "OpenAI", "sk-"),
    "together": ("together_api_key", "TOGETHER_API_KEY", "Together AI", None),
    "huggingface": ("huggingface_api_key", "HUGGINGFACE_API_KEY", "HuggingFace", "hf_"),
    "groq": ("groq_api_key", "GROQ_API_KEY", "Groq", "gsk_"),
    "openrouter": ("openrouter_api_key", "OPENROUTER_API_KEY", "OpenRouter", "sk-or-"),
    "gemini": ("gemini_api_key", "GEMINI_API_KEY", "Gemini", None),
    "replicate": ("replicate_api_token", "REPLICATE_API_TOKEN", "Replicate", "r8_"),
    "fal": ("fal_api_key", "FAL_KEY", "FAL", None),
    "pollinations": (
        "pollinations_api_key",
        "POLLINATIONS_API_KEY",
        "Pollinations",
        None,
    ),
    "local": ("local_api_key", "LOCAL_API_KEY", "Local server", None),
    "horde": ("horde_api_key", "HORDE_API_KEY", "AI Horde", None),
}


def validate_api_key(
    key: str,
    provider: str,
    prefix: Optional[str] = None,
    min_length: int = 20,
    max_length: int = 200,
) -> str:
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
        raise HTTPException(
            status_code=400, detail=f"{provider} API key cannot be empty"
        )

    if len(key) < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"{provider} API key too short (minimum {min_length} characters)",
        )

    if len(key) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"{provider} API key too long (maximum {max_length} characters)",
        )

    if prefix and not key.startswith(prefix):
        raise HTTPException(
            status_code=400, detail=f"{provider} API key must start with '{prefix}'"
        )

    return key


def check_api_key_exists(
    settings: UserSettings, settings_attr: str, env_var: str
) -> bool:
    """Check if an API key exists in settings or environment."""
    return bool(getattr(settings, settings_attr, None) or os.environ.get(env_var))


def set_api_key(
    settings: UserSettings,
    request_value: Optional[str],
    settings_attr: str,
    env_var: str,
    display_name: str,
    prefix: Optional[str],
) -> None:
    """Update API key in settings and environment if value is provided."""
    if request_value is not None and request_value.strip():
        validated_key = validate_api_key(
            request_value,
            display_name,
            prefix=prefix,
            min_length=1 if display_name == "Local server" else 20,
        )
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
    has_pollinations_key: bool
    has_local_key: bool
    has_horde_key: bool
    comfyui_base_url: str
    comfyui_workflow: str
    comfyui_prompt_node: str
    ollama_base_url: str
    local_base_url: str
    local_reasoning_effort: str

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
    pollinations_api_key: Optional[str] = Field(None, max_length=200)
    local_api_key: Optional[str] = Field(None, max_length=200)
    horde_api_key: Optional[str] = Field(None, max_length=200)
    comfyui_base_url: Optional[str] = Field(None, max_length=500)
    comfyui_workflow: Optional[str] = Field(None, max_length=1000000)
    comfyui_prompt_node: Optional[str] = Field(None, max_length=100)
    ollama_base_url: Optional[str] = Field(None, max_length=500)
    local_base_url: Optional[str] = Field(None, max_length=500)
    local_reasoning_effort: Optional[str] = Field(None, max_length=20)

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
        field_name = (
            f"has_{key_id}_key" if key_id != "replicate" else "has_replicate_token"
        )
        key_status[field_name] = has_key

    return SettingsResponse(
        text_provider=settings.text_provider,
        image_provider=settings.image_provider,
        ollama_base_url=settings.ollama_base_url,
        local_base_url=settings.local_base_url,
        local_reasoning_effort=settings.local_reasoning_effort,
        comfyui_base_url=settings.comfyui_base_url,
        comfyui_workflow=settings.comfyui_workflow,
        comfyui_prompt_node=settings.comfyui_prompt_node,
        **key_status,
        global_instructions=settings.global_instructions,
        default_style_pack=settings.default_style_pack,
        default_preset=settings.default_preset,
        default_text_model=settings.default_text_model,
        default_image_model=settings.default_image_model,
        reader_font_family=settings.reader_font_family,
        reader_font_size=settings.reader_font_size,
    )


@router.get("/providers")
async def get_provider_catalog():
    return {
        "text": TEXT_PROVIDERS,
        "image": IMAGE_PROVIDERS,
        "reviewed_on": REVIEWED_ON,
    }


@router.put("")
async def update_settings(request: SettingsUpdateRequest):
    """Update user settings"""
    settings = load_user_settings()

    from ..providers.local import validate_local_url
    from ..providers.local_image import validate_workflow

    if request.comfyui_base_url is not None:
        try:
            settings.comfyui_base_url = validate_local_url(
                request.comfyui_base_url, default_path=""
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if request.comfyui_workflow is not None or request.comfyui_prompt_node is not None:
        workflow = (
            request.comfyui_workflow
            if request.comfyui_workflow is not None
            else settings.comfyui_workflow
        )
        node = (
            request.comfyui_prompt_node
            if request.comfyui_prompt_node is not None
            else settings.comfyui_prompt_node
        )
        if workflow:
            try:
                validate_workflow(workflow, node)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        settings.comfyui_workflow, settings.comfyui_prompt_node = workflow, node
    for field in ("ollama_base_url", "local_base_url"):
        value = getattr(request, field)
        if value is not None:
            try:
                setattr(settings, field, validate_local_url(value))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    for kind, catalog in (("text", TEXT_PROVIDERS), ("image", IMAGE_PROVIDERS)):
        selected = getattr(request, f"{kind}_provider")
        if selected is not None and selected not in catalog:
            raise HTTPException(status_code=400, detail=f"Unknown {kind} provider")
        if (
            selected is not None
            and selected != getattr(settings, f"{kind}_provider")
            and getattr(request, f"default_{kind}_model") is None
        ):
            setattr(request, f"default_{kind}_model", default_model(selected, kind))
    for field, allowed in (
        ("local_reasoning_effort", {"default", "none", "low", "medium", "high"}),
        ("reader_font_family", {"Georgia", "serif", "sans-serif", "monospace"}),
        ("reader_font_size", {"small", "medium", "large", "xl"}),
    ):
        value = getattr(request, field)
        if value is not None and value not in allowed:
            raise HTTPException(
                status_code=400, detail=f"Invalid {field.replace('_', ' ')}"
            )
        if value is not None:
            setattr(settings, field, value)
    # Validate the entire key update before changing any environment variables.
    for attr, _, name, prefix in API_KEY_CONFIG.values():
        value = getattr(request, attr)
        if value and value.strip():
            validate_api_key(
                value, name, prefix, min_length=1 if name == "Local server" else 20
            )

    if request.text_provider is not None:
        settings.text_provider = request.text_provider

    if request.image_provider is not None:
        settings.image_provider = request.image_provider

    for key_id, (
        settings_attr,
        env_var,
        display_name,
        prefix,
    ) in API_KEY_CONFIG.items():
        request_value = getattr(request, settings_attr, None)
        set_api_key(
            settings, request_value, settings_attr, env_var, display_name, prefix
        )

    if request.global_instructions is not None:
        settings.global_instructions = request.global_instructions

    if request.default_style_pack is not None:
        settings.default_style_pack = request.default_style_pack

    if request.default_preset is not None:
        settings.default_preset = request.default_preset

    if request.default_text_model is not None:
        settings.default_text_model = request.default_text_model

    if request.default_image_model is not None:
        settings.default_image_model = request.default_image_model

    if request.reader_font_family is not None:
        settings.reader_font_family = request.reader_font_family

    if request.reader_font_size is not None:
        settings.reader_font_size = request.reader_font_size

    save_user_settings(settings)

    return {"message": "Settings updated"}


class LocalConnectionRequest(BaseModel):
    provider: str
    base_url: str = Field(max_length=500)


@router.post("/comfyui")
def check_comfyui(request: LocalConnectionRequest):
    import requests

    from ..providers.local import validate_local_url

    try:
        url = validate_local_url(request.base_url, default_path="")
        response = requests.get(f"{url}/system_stats", timeout=8, allow_redirects=False)
        response.raise_for_status()
        if "system" not in response.json():
            raise ValueError("Not a ComfyUI server")
    except (ValueError, requests.RequestException) as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not reach ComfyUI. Start it and check the server address.",
        ) from exc
    return {"message": "Connected to ComfyUI"}


@router.post("/local-models")
def check_local_models(request: LocalConnectionRequest):
    from ..providers.local import LocalProvider, validate_local_url

    if request.provider not in {"ollama", "local"}:
        raise HTTPException(status_code=400, detail="Choose Ollama or a local server.")
    try:
        url = validate_local_url(request.base_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        models = LocalProvider(provider=request.provider, base_url=url).list_models()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not reach the local server. Start it, enable its API, and check the address.",
        ) from exc
    return {"models": models}


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
