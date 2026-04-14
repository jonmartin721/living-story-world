import type {
  GenerationRequest,
  RandomWorldResponse,
  SettingsResponse,
  SettingsUpdateRequest,
  WorldDetail,
  WorldInput,
  WorldSummary,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      detail = await response.text();
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
    request<{ message: string; config: WorldDetail["config"] }>(`/api/worlds/${slug}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  deleteWorld: (slug: string) =>
    request<{ message: string }>(`/api/worlds/${slug}`, { method: "DELETE" }),
  setCurrentWorld: (slug: string) =>
    request<{ message: string }>(`/api/worlds/${slug}/current`, { method: "PUT" }),
  getSettings: () => request<SettingsResponse>("/api/settings"),
  updateSettings: (input: SettingsUpdateRequest) =>
    request<{ message: string }>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  clearKeys: () =>
    request<{ message: string }>("/api/settings/clear-keys", { method: "POST" }),
  getRandomWorld: () => request<RandomWorldResponse>("/api/generate/world"),
  getChapterContent: (slug: string, chapterNumber: number) =>
    request<{ content: string }>(`/api/worlds/${slug}/chapters/${chapterNumber}/content`),
  startChapterGeneration: (slug: string, input: GenerationRequest) =>
    request<{ job_id: string }>(`/api/worlds/${slug}/chapters`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  rerollChapter: (slug: string, chapterNumber: number, input: GenerationRequest) =>
    request<{ job_id: string }>(`/api/worlds/${slug}/chapters/${chapterNumber}/reroll`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  selectChoice: (slug: string, chapterNumber: number, choiceId: string) =>
    request<{ success: boolean }>(`/api/worlds/${slug}/chapters/${chapterNumber}/select-choice`, {
      method: "POST",
      body: JSON.stringify({ choice_id: choiceId }),
    }),
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
