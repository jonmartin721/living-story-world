import { api } from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("keeps the world response shape intact", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          config: {
            title: "World",
            slug: "world",
            theme: "Theme",
            style_pack: "storybook-ink",
            text_model: "gpt-4o-mini",
            image_model: "flux-schnell",
            maturity_level: "general",
            preset: "cozy-adventure",
            enable_choices: true,
          },
          state: {
            tick: 2,
            next_chapter: 3,
            characters: {},
            locations: {},
          },
          chapters: [
            {
              number: 1,
              title: "Harbor",
              filename: "chapter-0001.md",
              summary: "Summary",
              scene_prompt: "A harbor",
              image_prompt: "A harbor at dusk",
              characters_in_scene: [],
              choices: [],
              selected_choice_id: null,
              choice_reasoning: null,
              generated_at: null,
              text_model_used: "gpt-4o-mini",
              image_model_used: "flux-schnell",
              scene: "/worlds/world/media/scenes/scene.png",
              ai_summary: "Short summary",
            },
          ],
          is_current: true,
        }),
        { status: 200 },
      ),
    );

    const world = await api.getWorld("world");

    expect(world.config.image_model).toBe("flux-schnell");
    expect(world.chapters[0].scene).toContain("/worlds/world/media/scenes/");
    expect(world.chapters[0].ai_summary).toBe("Short summary");
  });
});
