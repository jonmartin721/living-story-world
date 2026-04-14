import { fireEvent, render, screen } from "@testing-library/react";
import { SettingsPanel } from "./SettingsPanel";

describe("SettingsPanel", () => {
  it("loads settings and saves edited values", () => {
    const onSave = vi.fn();

    render(
      <SettingsPanel
        settings={{
          text_provider: "gemini",
          image_provider: "pollinations",
          has_openai_key: false,
          has_together_key: false,
          has_huggingface_key: false,
          has_groq_key: false,
          has_openrouter_key: false,
          has_gemini_key: true,
          has_replicate_token: false,
          has_fal_key: false,
          global_instructions: "",
          default_style_pack: "storybook-ink",
          default_preset: "cozy-adventure",
          default_text_model: "gemini-2.5-flash",
          default_image_model: "flux",
          reader_font_family: "Georgia",
          reader_font_size: "medium",
        }}
        busy={false}
        onClose={vi.fn()}
        onSave={onSave}
        onClearKeys={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByDisplayValue("gemini"), {
      target: { value: "openai" },
    });
    fireEvent.change(screen.getByLabelText(/gemini api key/i), {
      target: { value: "new-key" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save settings/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        text_provider: "openai",
        gemini_api_key: "new-key",
      }),
    );
  });
});
