import type { SettingsResponse, SettingsUpdateRequest } from "../../api/types";

export const connections: {
  id: string;
  name: string;
  key: keyof SettingsUpdateRequest;
  status: keyof SettingsResponse;
}[] = [
  {
    id: "horde",
    name: "AI Horde (free account)",
    key: "horde_api_key",
    status: "has_horde_key",
  },
  {
    id: "local",
    name: "Local server (optional authentication)",
    key: "local_api_key",
    status: "has_local_key",
  },
  {
    id: "openai",
    name: "OpenAI",
    key: "openai_api_key",
    status: "has_openai_key",
  },
  {
    id: "gemini",
    name: "Google Gemini",
    key: "gemini_api_key",
    status: "has_gemini_key",
  },
  { id: "groq", name: "Groq", key: "groq_api_key", status: "has_groq_key" },
  {
    id: "together",
    name: "Together AI",
    key: "together_api_key",
    status: "has_together_key",
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    key: "openrouter_api_key",
    status: "has_openrouter_key",
  },
  {
    id: "huggingface",
    name: "Hugging Face",
    key: "huggingface_api_key",
    status: "has_huggingface_key",
  },
  {
    id: "replicate",
    name: "Replicate",
    key: "replicate_api_token",
    status: "has_replicate_token",
  },
  { id: "fal", name: "fal.ai", key: "fal_api_key", status: "has_fal_key" },
  {
    id: "pollinations",
    name: "Pollinations",
    key: "pollinations_api_key",
    status: "has_pollinations_key",
  },
];
export function hasProviderKey(
  settings: SettingsResponse | null,
  provider: string,
) {
  const connection = connections.find((item) => item.id === provider);
  return !!(settings && connection && settings[connection.status]);
}
