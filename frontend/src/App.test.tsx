import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";
import { api } from "./api/client";
import { useEventStream } from "./hooks/useEventStream";

vi.mock("./api/client", () => ({ api: {
  getCurrentChapterJob: vi.fn().mockResolvedValue(null), listWorlds: vi.fn(), getSettings: vi.fn(), getWorld: vi.fn(), getChapterContent: vi.fn(), setCurrentWorld: vi.fn(),
} }));
vi.mock("./hooks/useEventStream", () => ({ useEventStream: vi.fn(() => ({ status: "idle", progress: null, error: null })) }));

it.each(["idle", "discovered", "restored"])("keeps chapter caches isolated with a %s job", async (mode) => {
  sessionStorage.clear();
  vi.mocked(useEventStream).mockClear();
  if (mode === "restored") sessionStorage.setItem("activeChapterJob", JSON.stringify({ slug: "Harbor", jobId: "saved-job" }));
  vi.mocked(api.getCurrentChapterJob).mockResolvedValue(mode === "discovered" ? { job_id: "saved-job", status: "running", progress: null, chapter: null, error: null } : null);
  const world = (slug: string) => ({
    title: slug, slug, theme: `${slug} setting`, style_pack: "storybook-ink", text_model: "test", image_model: "test",
    maturity_level: "general", preset: "cozy-adventure", enable_choices: false, tick: 0, chapter_count: 1, is_current: slug === "Harbor",
  });
  vi.mocked(api.listWorlds).mockResolvedValue([world("Harbor"), world("Forest")]);
  vi.mocked(api.getSettings).mockResolvedValue({} as Awaited<ReturnType<typeof api.getSettings>>);
  vi.mocked(api.setCurrentWorld).mockResolvedValue({ message: "Selected" });
  vi.mocked(api.getWorld).mockImplementation(async (slug) => ({
    config: world(slug), state: { tick: 0, next_chapter: 2, characters: {}, locations: {} }, is_current: true,
    chapters: [{ number: 1, title: "Opening", filename: "chapter-0001.md", characters_in_scene: [], choices: [] }],
  }));
  vi.mocked(api.getChapterContent).mockImplementation(async (slug) => ({ content: `Only the ${slug} story.` }));
  render(<App />);
  await screen.findByText("Only the Harbor story.");
  if (mode !== "idle") await waitFor(() => expect(useEventStream).toHaveBeenCalledWith("/api/worlds/Harbor/chapters/stream/saved-job", expect.any(Object)));
  fireEvent.click(screen.getByRole("button", { name: /Forest.*1 chapters/ }));
  await screen.findByText("Only the Forest story.");
  expect(screen.queryByText("Only the Harbor story.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Harbor.*1 chapters/ }));
  await screen.findByText("Only the Harbor story.");
  await waitFor(() => expect(api.getChapterContent).toHaveBeenCalledWith("Forest", 1));
});
