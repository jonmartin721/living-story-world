import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SettingsPanel } from "./SettingsPanel";
import { api } from "../../api/client";
import type { SettingsResponse } from "../../api/types";

vi.mock("../../api/client", () => ({
  api: { getProviders: vi.fn(), checkLocalModels: vi.fn() },
}));
const settings: SettingsResponse = {
  text_provider: "gemini",
  image_provider: "none",
  default_text_model: "saved-model",
  default_image_model: "",
  default_style_pack: "storybook-ink",
  default_preset: "cozy-adventure",
  reader_font_family: "Georgia",
  reader_font_size: "medium",
  has_openai_key: false,
  has_together_key: false,
  has_huggingface_key: false,
  has_groq_key: false,
  has_openrouter_key: false,
  has_gemini_key: true,
  has_replicate_token: false,
  has_fal_key: false,
};
beforeEach(() => {
  vi.mocked(api.getProviders).mockResolvedValue({
    text: {
      gemini: {
        name: "Google Gemini",
        url: "",
        models: [
          {
            id: "gemini-current",
            name: "Current Gemini",
            note: "",
            input_price: 0.3,
            output_price: 2.5,
          },
        ],
      },
      ollama: {
        name: "Ollama",
        url: "",
        models: [
          {
            id: "",
            name: "First installed model",
            note: "Local",
            input_price: 0,
            output_price: 0,
          },
        ],
      },
    },
    image: {
      none: {
        name: "No illustrations",
        url: "",
        models: [
          {
            id: "",
            name: "Text only",
            note: "No cost",
            input_price: null,
            output_price: null,
          },
        ],
      },
    },
    reviewed_on: "2026-09-21",
  });
});

it("preserves a saved model and only submits changed fields", async () => {
  const onSave = vi.fn();
  render(
    <SettingsPanel
      settings={settings}
      busy={false}
      onSave={onSave}
      onClearKeys={vi.fn()}
    />,
  );
  await screen.findByRole("combobox", { name: "Writing provider" });
  expect(screen.getByRole("textbox", { name: /Model ID/ })).toHaveValue(
    "saved-model",
  );
  fireEvent.change(screen.getByRole("combobox", { name: "Writing provider" }), {
    target: { value: "ollama" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() =>
    expect(onSave).toHaveBeenCalledWith({
      text_provider: "ollama",
      default_text_model: "",
    }),
  );
});

it("keeps an unsuccessful draft and offers a guarded exit", async () => {
  const onClose = vi.fn();
  render(
    <SettingsPanel
      settings={settings}
      busy={false}
      onSave={vi.fn().mockRejectedValue(new Error("Offline"))}
      onClearKeys={vi.fn()}
      onClose={onClose}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "New worlds" }));
  fireEvent.change(screen.getByLabelText("Default story tone"), {
    target: { value: "noir-mystery" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Offline");
  expect(screen.getByLabelText("Default story tone")).toHaveValue(
    "noir-mystery",
  );
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(onClose).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Discard changes" }));
  expect(onClose).toHaveBeenCalledOnce();
});

it("requires confirmation before clearing connections", async () => {
  const clear = vi.fn();
  render(
    <SettingsPanel
      settings={settings}
      busy={false}
      onSave={vi.fn()}
      onClearKeys={clear}
    />,
  );
  await screen.findByRole("combobox", { name: "Writing provider" });
  fireEvent.click(screen.getByRole("button", { name: "Connections" }));
  fireEvent.click(screen.getByRole("button", { name: /Clear all API keys/ }));
  expect(clear).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Keep keys" }));
  expect(clear).not.toHaveBeenCalled();
});
