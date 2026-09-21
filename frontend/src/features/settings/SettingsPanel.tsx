import { useEffect, useState } from "react";
import type { SettingsResponse, SettingsUpdateRequest } from "../../api/types";

type SettingsPanelProps = {
  settings: SettingsResponse | null;
  busy: boolean;
  onClose: () => void;
  onSave: (value: SettingsUpdateRequest) => void;
  onClearKeys: () => void;
};

export function SettingsPanel({
  settings,
  busy,
  onClose,
  onSave,
  onClearKeys,
}: SettingsPanelProps) {
  const [form, setForm] = useState<SettingsUpdateRequest>({});

  useEffect(() => {
    if (!settings) {
      return;
    }
    setForm({
      text_provider: settings.text_provider,
      image_provider: settings.image_provider,
      global_instructions: settings.global_instructions ?? "",
      default_style_pack: settings.default_style_pack,
      default_preset: settings.default_preset,
      default_text_model: settings.default_text_model,
      default_image_model: settings.default_image_model,
      reader_font_family: settings.reader_font_family,
      reader_font_size: settings.reader_font_size,
    });
  }, [settings]);

  return (
    <section className="panel settings-panel">
      <div className="settings-panel__header">
        <div>
          <div className="panel__eyebrow">Settings</div>
          <h2>Providers & Reader</h2>
        </div>
        <button type="button" className="button button--ghost" onClick={onClose}>
          Close
        </button>
      </div>

      <div className="form-grid">
        <label>
          Text Provider
          <input
            value={form.text_provider ?? ""}
            onChange={(event) =>
              setForm({ ...form, text_provider: event.target.value })
            }
          />
        </label>
        <label>
          Image Provider
          <input
            value={form.image_provider ?? ""}
            onChange={(event) =>
              setForm({ ...form, image_provider: event.target.value })
            }
          />
        </label>
        <label>
          Default Text Model
          <input
            value={form.default_text_model ?? ""}
            onChange={(event) =>
              setForm({ ...form, default_text_model: event.target.value })
            }
          />
        </label>
        <label>
          Default Image Model
          <input
            value={form.default_image_model ?? ""}
            onChange={(event) =>
              setForm({ ...form, default_image_model: event.target.value })
            }
          />
        </label>
        <label>
          Default Style
          <input
            value={form.default_style_pack ?? ""}
            onChange={(event) =>
              setForm({ ...form, default_style_pack: event.target.value })
            }
          />
        </label>
        <label>
          Default Preset
          <input
            value={form.default_preset ?? ""}
            onChange={(event) =>
              setForm({ ...form, default_preset: event.target.value })
            }
          />
        </label>
        <label>
          Reader Font
          <input
            value={form.reader_font_family ?? ""}
            onChange={(event) =>
              setForm({ ...form, reader_font_family: event.target.value })
            }
          />
        </label>
        <label>
          Reader Size
          <input
            value={form.reader_font_size ?? ""}
            onChange={(event) =>
              setForm({ ...form, reader_font_size: event.target.value })
            }
          />
        </label>
        <label>
          Global Instructions
          <textarea
            rows={4}
            value={form.global_instructions ?? ""}
            onChange={(event) =>
              setForm({ ...form, global_instructions: event.target.value })
            }
          />
        </label>
        <label>
          Gemini API Key
          <input
            type="password"
            placeholder="Paste to replace"
            value={form.gemini_api_key ?? ""}
            onChange={(event) =>
              setForm({ ...form, gemini_api_key: event.target.value })
            }
          />
        </label>
        <label>
          OpenAI API Key
          <input
            type="password"
            placeholder="Paste to replace"
            value={form.openai_api_key ?? ""}
            onChange={(event) =>
              setForm({ ...form, openai_api_key: event.target.value })
            }
          />
        </label>
        <label>
          Replicate Token
          <input
            type="password"
            placeholder="Paste to replace"
            value={form.replicate_api_token ?? ""}
            onChange={(event) =>
              setForm({ ...form, replicate_api_token: event.target.value })
            }
          />
        </label>
      </div>

      <div className="settings-status">
        <span className={settings?.has_gemini_key ? "pill" : "pill pill--muted"}>
          Gemini {settings?.has_gemini_key ? "ready" : "missing"}
        </span>
        <span className={settings?.has_openai_key ? "pill" : "pill pill--muted"}>
          OpenAI {settings?.has_openai_key ? "ready" : "missing"}
        </span>
        <span className={settings?.has_replicate_token ? "pill" : "pill pill--muted"}>
          Replicate {settings?.has_replicate_token ? "ready" : "missing"}
        </span>
      </div>

      <div className="editor__actions">
        <button type="button" className="button button--ghost" onClick={onClearKeys}>
          Clear API Keys
        </button>
        <button type="button" className="button" disabled={busy} onClick={() => onSave(form)}>
          {busy ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </section>
  );
}
