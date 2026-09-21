"""Curated starting points, with custom model IDs supported by each service."""

REVIEWED_ON = "2026-09-21"


def model(id, name, note, input_price=None, output_price=None):
    return dict(
        id=id, name=name, note=note, input_price=input_price, output_price=output_price
    )


TEXT_PROVIDERS = {
    "ollama": dict(
        name="Ollama · local",
        url="https://docs.ollama.com/quickstart",
        models=[
            model(
                "",
                "First installed local model",
                "No API bill. Runs on your computer; install a model in Ollama first.",
                0,
                0,
            ),
        ],
    ),
    "local": dict(
        name="Local OpenAI-compatible server",
        url="https://lmstudio.ai/docs/developer/openai-compat",
        models=[
            model(
                "",
                "First available local model",
                "LM Studio, vLLM, llama.cpp, NInfer, and compatible servers. No API bill.",
                0,
                0,
            ),
        ],
    ),
    "openai": dict(
        name="OpenAI",
        url="https://developers.openai.com/api/docs/models",
        models=[
            model("gpt-5.6-luna", "GPT-5.6 Luna", "Low-cost writing", 0.20, 1.20),
            model(
                "gpt-5.4-mini", "GPT-5.4 Mini", "More capable, higher cost", 0.75, 4.50
            ),
            model("gpt-5-mini", "GPT-5 Mini", "Previous generation", 0.25, 2.00),
        ],
    ),
    "gemini": dict(
        name="Google Gemini",
        url="https://ai.google.dev/gemini-api/docs/pricing",
        models=[
            model(
                "gemini-3.5-flash-lite",
                "Gemini 3.5 Flash-Lite",
                "Fast, with a limited free tier",
                0.30,
                2.50,
            ),
            model(
                "gemini-3.1-flash-lite",
                "Gemini 3.1 Flash-Lite",
                "Lower-cost alternative",
                0.25,
                1.50,
            ),
            model(
                "gemini-2.5-flash-lite",
                "Gemini 2.5 Flash-Lite",
                "Previous generation",
                0.10,
                0.40,
            ),
            model(
                "gemini-2.5-flash",
                "Gemini 2.5 Flash",
                "Previous generation",
                0.30,
                2.50,
            ),
        ],
    ),
    "groq": dict(
        name="Groq",
        url="https://console.groq.com/docs/models",
        models=[
            model(
                "openai/gpt-oss-120b",
                "GPT-OSS 120B",
                "Free tier available with rate limits; paid rates below",
                0.15,
                0.60,
            ),
            model(
                "openai/gpt-oss-20b", "GPT-OSS 20B", "Lowest-cost option", 0.075, 0.30
            ),
        ],
    ),
    "together": dict(
        name="Together AI",
        url="https://docs.together.ai/docs/serverless/models",
        models=[
            model(
                "openai/gpt-oss-120b",
                "GPT-OSS 120B",
                "Affordable open-weight model",
                0.15,
                0.60,
            ),
            model(
                "zai-org/GLM-5.3-Flash",
                "GLM-5.3 Flash",
                "Recent, low-cost alternative",
                0.15,
                0.50,
            ),
        ],
    ),
    "openrouter": dict(
        name="OpenRouter",
        url="https://openrouter.ai/models",
        models=[
            model(
                "openrouter/free",
                "Free models router",
                "Uses available free models. Rate limits and model availability vary.",
                0,
                0,
            ),
            model(
                "openai/gpt-oss-120b", "GPT-OSS 120B", "Price varies by routed provider"
            ),
        ],
    ),
    "huggingface": dict(
        name="Hugging Face",
        url="https://huggingface.co/docs/inference-providers/index",
        models=[
            model(
                "openai/gpt-oss-120b:cheapest",
                "GPT-OSS 120B · cheapest route",
                "Usage billed by the selected provider",
            ),
            model(
                "openai/gpt-oss-120b:fastest",
                "GPT-OSS 120B · fastest route",
                "Usage billed by the selected provider",
            ),
        ],
    ),
}

IMAGE_PROVIDERS = {
    "none": dict(
        name="No illustrations",
        url="",
        models=[
            model(
                "",
                "Text only",
                "No image service, account, or charge. Illustrations can be enabled later.",
            ),
        ],
    ),
    "comfyui": dict(
        name="ComfyUI · local",
        billing="local",
        url="https://docs.comfy.org",
        models=[
            model(
                "workflow",
                "Your local workflow",
                "Use Z-Image, FLUX, Qwen Image, or another installed model. Import a workflow using local model nodes; cloud API nodes can incur charges.",
            ),
        ],
    ),
    "horde": dict(
        name="AI Horde",
        billing="free",
        url="https://aihorde.net",
        models=[
            model(
                "",
                "Any available model",
                "Free community image generation. Requires a free account key; queues and availability vary. Prompts are sent to volunteer workers.",
            ),
        ],
    ),
    "openai": dict(
        name="OpenAI",
        url="https://developers.openai.com/api/docs/models/gpt-image-1-mini",
        models=[
            model(
                "gpt-image-1-mini",
                "GPT Image Mini",
                "Low quality · about $0.006 per landscape image, plus prompt tokens",
            ),
        ],
    ),
    "replicate": dict(
        name="Replicate",
        url="https://replicate.com/black-forest-labs/flux-schnell",
        models=[
            model(
                "flux-schnell",
                "FLUX Schnell",
                "Fast illustrations · check current provider pricing",
            ),
            model("flux-dev", "FLUX Dev", "More detail · higher cost"),
        ],
    ),
    "fal": dict(
        name="fal.ai",
        url="https://fal.ai/models/fal-ai/flux/schnell",
        models=[
            model(
                "flux/schnell",
                "FLUX Schnell",
                "Fast illustrations · billed by resolution",
            ),
            model("flux/dev", "FLUX Dev", "More detail · higher cost"),
        ],
    ),
    "pollinations": dict(
        name="Pollinations",
        url="https://enter.pollinations.ai",
        models=[
            model(
                "black-forest-labs/flux.1-schnell",
                "FLUX Schnell",
                "Requires a Pollinations key and credits",
            ),
        ],
    ),
    "huggingface": dict(
        name="Hugging Face",
        url="https://huggingface.co/docs/inference-providers/tasks/text-to-image",
        models=[
            model(
                "black-forest-labs/FLUX.1-schnell",
                "FLUX Schnell",
                "Requires a token with Inference Providers permission",
            ),
        ],
    ),
}


for provider_id, provider in TEXT_PROVIDERS.items():
    provider["billing"] = (
        "local"
        if provider_id in {"ollama", "local"}
        else "free_tier" if provider_id in {"gemini", "groq", "openrouter"} else "paid"
    )

for provider_id, provider in IMAGE_PROVIDERS.items():
    provider.setdefault("billing", "disabled" if provider_id == "none" else "paid")


def default_model(provider: str, kind: str = "text") -> str:
    catalog = TEXT_PROVIDERS if kind == "text" else IMAGE_PROVIDERS
    return catalog[provider]["models"][0]["id"]


def text_cost(provider: str, model_id: str, input_tokens: int, output_tokens: int):
    """Estimate at published uncached standard rates; unknown is not free."""
    options = TEXT_PROVIDERS.get(provider, {}).get("models", [])
    option = next((item for item in options if item["id"] == model_id), None)
    if not option or option["input_price"] is None:
        return None
    return (
        input_tokens * option["input_price"] + output_tokens * option["output_price"]
    ) / 1_000_000
