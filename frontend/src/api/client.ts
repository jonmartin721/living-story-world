import type {
  ChapterJobStatus,
  ProviderCatalog,
  GenerationRequest,
  RandomWorldResponse,
  SettingsResponse,
  SettingsUpdateRequest,
  WorldDetail,
  WorldInput,
  WorldSummary,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch {
    throw new Error(
      "Could not reach the app. Check the connection and try again.",
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as {
        detail?: string | { error?: string } | unknown[];
      };
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (payload.detail && !Array.isArray(payload.detail))
        detail = payload.detail.error ?? detail;
      else if (Array.isArray(payload.detail))
        detail = "Please check the form values and try again.";
    } catch {
      // The response body has already been consumed by json(). Keep the status message.
    }
    throw new Error(detail || "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  listWorlds: () => request<WorldSummary[]>("/api/worlds"),
  getWorld: (slug: string) => request<WorldDetail>(`/api/worlds/${slug}`),
  createWorld: (input: WorldInput) =>
    request<WorldSummary>("/api/worlds", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateWorld: (slug: string, input: Partial<WorldInput>) =>
    request<{ message: string; config: WorldDetail["config"] }>(
      `/api/worlds/${slug}`,
      {
        method: "PUT",
        body: JSON.stringify(input),
      },
    ),
  deleteWorld: (slug: string) =>
    request<{ message: string }>(`/api/worlds/${slug}`, { method: "DELETE" }),
  setCurrentWorld: (slug: string) =>
    request<{ message: string }>(`/api/worlds/${slug}/current`, {
      method: "PUT",
    }),
  getSettings: () => request<SettingsResponse>("/api/settings"),
  getProviders: () => request<ProviderCatalog>("/api/settings/providers"),
  checkComfyUI: (base_url: string) =>
    request<{ message: string }>("/api/settings/comfyui", {
      method: "POST",
      body: JSON.stringify({ provider: "comfyui", base_url }),
    }),
  checkLocalModels: (provider: string, base_url: string) =>
    request<{ models: string[] }>("/api/settings/local-models", {
      method: "POST",
      body: JSON.stringify({ provider, base_url }),
    }),
  updateSettings: (input: SettingsUpdateRequest) =>
    request<{ message: string }>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  clearKeys: () =>
    request<{ message: string }>("/api/settings/clear-keys", {
      method: "POST",
    }),
  getRandomWorld: () => request<RandomWorldResponse>("/api/generate/world"),
  getChapterContent: (slug: string, chapterNumber: number) =>
    request<{ content: string }>(
      `/api/worlds/${slug}/chapters/${chapterNumber}/content`,
    ),
  getCurrentChapterJob: (slug: string) =>
    request<ChapterJobStatus | null>(
      `/api/worlds/${slug}/chapters/jobs/current`,
    ),
  startChapterGeneration: (slug: string, input: GenerationRequest) =>
    request<{ job_id: string }>(`/api/worlds/${slug}/chapters`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  rerollChapter: (
    slug: string,
    chapterNumber: number,
    input: GenerationRequest,
  ) =>
    request<{ job_id: string }>(
      `/api/worlds/${slug}/chapters/${chapterNumber}/reroll`,
      {
        method: "PUT",
        body: JSON.stringify(input),
      },
    ),
  selectChoice: (slug: string, chapterNumber: number, choiceId: string) =>
    request<{ success: boolean }>(
      `/api/worlds/${slug}/chapters/${chapterNumber}/select-choice`,
      {
        method: "POST",
        body: JSON.stringify({ choice_id: choiceId }),
      },
    ),
  regenerateImage: (slug: string, chapterNumber: number) =>
    request<{ scene: string; chapter: number }>(`/api/worlds/${slug}/images`, {
      method: "POST",
      body: JSON.stringify({ chapter: chapterNumber }),
    }),
  deleteChapter: (slug: string, chapterNumber: number) =>
    request<{ success: boolean; message: string }>(
      `/api/worlds/${slug}/chapters/${chapterNumber}`,
      { method: "DELETE" },
    ),
};
