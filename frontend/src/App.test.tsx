import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";
import { api } from "./api/client";
import { useEventStream } from "./hooks/useEventStream";

vi.mock("./api/client", () => ({
  api: {
    getProviders: vi
      .fn()
      .mockResolvedValue({ text: {}, image: {}, reviewed_on: "2026-09-21" }),
    startChapterGeneration: vi.fn(),
    selectChoice: vi.fn(),
    getCurrentChapterJob: vi.fn().mockResolvedValue(null),
    listWorlds: vi.fn(),
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
    getWorld: vi.fn(),
    getChapterContent: vi.fn(),
    setCurrentWorld: vi.fn(),
  },
}));
vi.mock("./hooks/useEventStream", () => ({
  useEventStream: vi.fn(() => ({
    status: "idle",
    progress: null,
    error: null,
  })),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getCurrentChapterJob).mockResolvedValue(null);
  window.localStorage.clear();
  sessionStorage.clear();
  const world = (slug: string) => ({
    title: slug,
    slug,
    theme: `${slug} setting`,
    style_pack: "storybook-ink",
    text_model: "test",
    image_model: "test",
    maturity_level: "general",
    preset: "cozy-adventure",
    enable_choices: false,
    tick: 0,
    chapter_count: 1,
    is_current: slug === "Harbor",
  });
  vi.mocked(api.listWorlds).mockResolvedValue([
    world("Harbor"),
    world("Forest"),
  ]);
  vi.mocked(api.getSettings).mockResolvedValue(
    {} as Awaited<ReturnType<typeof api.getSettings>>,
  );
  vi.mocked(api.setCurrentWorld).mockResolvedValue({ message: "Selected" });
  vi.mocked(api.getWorld).mockImplementation(async (slug) => ({
    config: world(slug),
    state: { tick: 0, next_chapter: 2, characters: {}, locations: {} },
    is_current: true,
    chapters: [
      {
        number: 1,
        title: "Opening",
        filename: "chapter-0001.md",
        characters_in_scene: [],
        choices: [],
      },
    ],
  }));
  vi.mocked(api.getChapterContent).mockImplementation(async (slug) => ({
    content: `Only the ${slug} story.`,
  }));
});

it("keeps a failed initial load recoverable without showing an empty library", async () => {
  vi.mocked(api.listWorlds).mockRejectedValueOnce(new Error("Connection lost"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Connection lost");
  expect(
    screen.queryByRole("button", { name: "Create world" }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("Only the Harbor story.")).toBeInTheDocument();
});

it("rolls back reading preferences if saving fails", async () => {
  vi.mocked(api.getSettings).mockResolvedValue({
    reader_font_family: "Georgia",
    reader_font_size: "medium",
  } as Awaited<ReturnType<typeof api.getSettings>>);
  vi.mocked(api.updateSettings).mockRejectedValueOnce(
    new Error("Could not save"),
  );
  render(<App />);
  await screen.findByText("Only the Harbor story.");
  fireEvent.click(screen.getByRole("button", { name: "Reading appearance" }));
  fireEvent.click(screen.getByRole("radio", { name: "Sans" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not save");
  expect(screen.getByRole("radio", { name: "Serif" })).toBeChecked();
});

it.each(["idle", "discovered", "restored"])(
  "keeps chapter caches isolated with a %s job",
  async (mode) => {
    sessionStorage.clear();
    vi.mocked(useEventStream).mockClear();
    if (mode === "restored")
      sessionStorage.setItem(
        "activeChapterJob",
        JSON.stringify({ slug: "Harbor", jobId: "saved-job" }),
      );
    vi.mocked(api.getCurrentChapterJob).mockResolvedValue(
      mode === "discovered"
        ? {
            job_id: "saved-job",
            status: "running",
            progress: null,
            chapter: null,
            error: null,
          }
        : null,
    );
    render(<App />);
    await screen.findByText("Only the Harbor story.");
    if (mode !== "idle")
      await waitFor(() =>
        expect(useEventStream).toHaveBeenCalledWith(
          "/api/worlds/Harbor/chapters/stream/saved-job",
          expect.any(Object),
        ),
      );
    fireEvent.click(screen.getByRole("button", { name: /^‹ Library$/ }));
    fireEvent.click(screen.getByRole("button", { name: /Forest.*1 chapter/ }));
    await screen.findByText("Only the Forest story.");
    expect(
      screen.queryByText("Only the Harbor story."),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^‹ Library$/ }));
    fireEvent.click(screen.getByRole("button", { name: /Harbor.*1 chapter/ }));
    await screen.findByText("Only the Harbor story.");
    await waitFor(() =>
      expect(api.getChapterContent).toHaveBeenCalledWith("Forest", 1),
    );
  },
);

it("switches all four themes and restores the selected theme after remount", async () => {
  window.localStorage.clear();
  sessionStorage.clear();
  const { unmount } = render(<App />);
  await screen.findByText("Only the Harbor story.");
  expect(document.documentElement.dataset.theme).toBe("literary");
  fireEvent.click(screen.getByRole("button", { name: "Reading appearance" }));
  for (const [name, id, scheme] of [
    ["Charcoal & sage", "sage", "dark"],
    ["Sepia & copper", "sepia", "dark"],
    ["Aubergine & rose", "rose", "dark"],
    ["Warm literary", "literary", "light"],
    ["Charcoal & sage", "sage", "dark"],
  ]) {
    fireEvent.click(screen.getByRole("radio", { name: new RegExp(name) }));
    expect(document.documentElement.dataset.theme).toBe(id);
    expect(document.documentElement.style.colorScheme).toBe(scheme);
    expect(window.localStorage.getItem("storyworld.theme")).toBe(id);
  }
  unmount();
  render(<App />);
  await screen.findByText("Only the Harbor story.");
  expect(document.documentElement.dataset.theme).toBe("sage");
  fireEvent.click(screen.getByRole("button", { name: "Reading appearance" }));
  expect(screen.getByRole("radio", { name: /Charcoal & sage/ })).toBeChecked();
});

it("does not request the old chapter from an empty world during a background job", async () => {
  sessionStorage.setItem(
    "activeChapterJob",
    JSON.stringify({ slug: "Harbor", jobId: "saved-job" }),
  );
  const getWorld = vi.mocked(api.getWorld).getMockImplementation()!;
  vi.mocked(api.getWorld).mockImplementation(async (slug) => {
    const detail = await getWorld(slug);
    return slug === "Forest" ? { ...detail, chapters: [] } : detail;
  });
  render(<App />);
  await screen.findByText("Only the Harbor story.");
  fireEvent.click(screen.getByRole("button", { name: /^‹ Library$/ }));
  fireEvent.click(screen.getByRole("button", { name: /Forest.*1 chapter/ }));
  await screen.findByRole("heading", { name: "Forest", level: 1 });
  expect(api.getChapterContent).not.toHaveBeenCalledWith("Forest", 1);
  expect(
    screen.getByRole("button", { name: /Writing elsewhere/ }),
  ).toBeDisabled();
  expect(
    screen.getByRole("region", { name: "Writing in Harbor" }),
  ).toBeInTheDocument();
});

it("starts the next chapter with the reader's generation options", async () => {
  vi.mocked(api.startChapterGeneration).mockResolvedValue({
    job_id: "next-job",
  });
  render(<App />);
  await screen.findByText("Only the Harbor story.");
  fireEvent.click(screen.getByText("Story options"));
  fireEvent.change(screen.getByLabelText("Chapter length"), {
    target: { value: "short" },
  });
  fireEvent.click(screen.getByLabelText("Include an illustration"));
  fireEvent.click(screen.getByRole("button", { name: /Continue story/ }));
  await waitFor(() =>
    expect(api.startChapterGeneration).toHaveBeenCalledWith("Harbor", {
      chapter_length: "short",
      no_images: true,
    }),
  );
  expect(await screen.findByRole("button", { name: /Writing/ })).toBeDisabled();
  expect(sessionStorage.getItem("activeChapterJob")).toContain("next-job");
});

it("keeps the theme picker usable when browser storage is unavailable", async () => {
  const read = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("Unavailable");
  });
  const save = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("Unavailable");
  });
  try {
    render(<App />);
    await screen.findByText("Only the Harbor story.");
    fireEvent.click(screen.getByRole("button", { name: "Reading appearance" }));
    fireEvent.click(screen.getByRole("radio", { name: /Sepia & copper/ }));
    expect(document.documentElement.dataset.theme).toBe("sepia");
  } finally {
    read.mockRestore();
    save.mockRestore();
  }
});

it("keeps failed settings changes and shows a persistent error", async () => {
  vi.mocked(api.updateSettings).mockRejectedValue(
    new Error("Connection unavailable"),
  );
  render(<App />);
  await screen.findByText("Only the Harbor story.");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(screen.getByText(/Writing instructions/));
  fireEvent.change(
    screen.getByRole("textbox", { name: /Instructions for every world/ }),
    { target: { value: "More dialogue" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Connection unavailable",
  );
  expect(
    screen.getByRole("textbox", { name: /Instructions for every world/ }),
  ).toHaveValue("More dialogue");
  expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(
    screen.getByRole("dialog", { name: "Leave without saving?" }),
  ).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  expect(
    screen.getByRole("textbox", { name: /Instructions for every world/ }),
  ).toHaveValue("More dialogue");
});
