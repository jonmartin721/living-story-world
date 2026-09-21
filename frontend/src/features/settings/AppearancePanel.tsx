import { useState, type CSSProperties } from "react";
import type { SettingsResponse, SettingsUpdateRequest } from "../../api/types";
import { themes, type Theme } from "./themes";

type Props = {
  theme: Theme;
  onThemeChange: (theme: Theme) => void;
  settings: SettingsResponse | null;
  onReaderChange: (value: SettingsUpdateRequest) => Promise<void>;
};

export function AppearancePanel({
  theme,
  onThemeChange,
  settings,
  onReaderChange,
}: Props) {
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const save = async (value: SettingsUpdateRequest) => {
    setError("");
    setSaving(true);
    try {
      await onReaderChange(value);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="appearance-panel">
      <fieldset className="theme-picker">
        <legend className="eyebrow">Theme</legend>
        <div className="theme-grid">
          {themes.map((option) => (
            <label className="theme-option" key={option.id}>
              <input
                type="radio"
                name="theme"
                value={option.id}
                checked={theme === option.id}
                onChange={() => onThemeChange(option.id)}
              />
              <span
                className="theme-preview"
                aria-hidden="true"
                style={
                  {
                    "--preview-bg": option.background,
                    "--preview-ink": option.ink,
                    "--preview-accent": option.accent,
                  } as CSSProperties
                }
              >
                <span className="theme-preview__margin" />
                <span className="theme-preview__page">
                  <span>Aa</span>
                  <i />
                  <i />
                  <i />
                  <b />
                </span>
              </span>
              <span className="theme-option__name">{option.name}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="reading-preference" disabled={saving || !settings}>
        <legend>Typeface</legend>
        <div className="segmented-control">
          {[
            ["Georgia", "Serif"],
            ["sans-serif", "Sans"],
            ["monospace", "Mono"],
          ].map(([id, label]) => (
            <label key={id}>
              <input
                type="radio"
                name="font"
                checked={
                  (settings?.reader_font_family === "serif"
                    ? "Georgia"
                    : settings?.reader_font_family) === id
                }
                onChange={() => void save({ reader_font_family: id })}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="reading-preference" disabled={saving || !settings}>
        <legend>Text size</legend>
        <div className="segmented-control">
          {[
            ["small", "Small"],
            ["medium", "Medium"],
            ["large", "Large"],
            ["xl", "Extra large"],
          ].map(([id, label], i) => (
            <label key={id}>
              <input
                type="radio"
                name="font-size"
                aria-label={label}
                checked={settings?.reader_font_size === id}
                onChange={() => void save({ reader_font_size: id })}
              />
              <span>{["S", "M", "L", "XL"][i]}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <div className="appearance-panel__footer">
        <span className="muted" role="status">
          {saving ? "Saving…" : error ? "Not saved" : "Saved automatically"}
        </span>
      </div>
    </div>
  );
}
