import { useEffect, useState } from "react";
import type {
  RandomWorldResponse,
  SettingsResponse,
  WorldDetail,
  WorldInput,
} from "../../api/types";

import { Workspace } from "../../components/Workspace";
import { useUnsavedChanges } from "../../hooks/useUnsavedChanges";
import { styles, presets, displayName } from "./options";

const defaults: WorldInput = {
  title: "",
  theme: "",
  style_pack: "storybook-ink",
  maturity_level: "general",
  preset: "cozy-adventure",
  enable_choices: false,
  memory: "",
  authors_note: "",
  world_instructions: "",
};

type Props = {
  mode: "create" | "edit";
  world: WorldDetail | null;
  randomWorld: RandomWorldResponse | null;
  busy: boolean;
  onCancel: () => void;
  onSubmit: (value: WorldInput) => Promise<void> | void;
  settings?: Pick<
    SettingsResponse,
    "default_style_pack" | "default_preset"
  > | null;
};

function initialValue({
  mode,
  world,
  randomWorld,
  settings,
}: Props): WorldInput {
  const source = mode === "edit" ? world?.config : randomWorld;
  if (!source)
    return {
      ...defaults,
      style_pack: settings?.default_style_pack ?? defaults.style_pack,
      preset: settings?.default_preset ?? defaults.preset,
    };
  return {
    ...(mode === "edit" && world
      ? {
          text_model: world.config.text_model,
          image_model: world.config.image_model,
        }
      : {}),
    title: source.title,
    theme: source.theme,
    style_pack: source.style_pack,
    maturity_level: source.maturity_level,
    preset: source.preset,
    enable_choices: "enable_choices" in source ? source.enable_choices : false,
    memory: source.memory ?? "",
    authors_note: "authors_note" in source ? (source.authors_note ?? "") : "",
    world_instructions:
      "world_instructions" in source ? (source.world_instructions ?? "") : "",
  };
}

export function WorldEditor(props: Props) {
  const [value, setValue] = useState<WorldInput>(() => initialValue(props));
  const [baseline, setBaseline] = useState(() =>
    JSON.stringify(initialValue(props)),
  );
  const [error, setError] = useState("");
  useEffect(() => {
    const next = initialValue(props);
    setValue(next);
    setBaseline(JSON.stringify(next));
  }, [props.mode, props.world, props.randomWorld]);
  const dirty = JSON.stringify(value) !== baseline;
  const guard = useUnsavedChanges(dirty, () => {
    if (!props.busy) props.onCancel();
  });
  const set = (key: keyof WorldInput, text: string | boolean) =>
    setValue((previous) => ({ ...previous, [key]: text }));
  return (
    <Workspace
      title={props.mode === "edit" ? "Edit world" : "New world"}
      backLabel="Back to library"
      onBack={guard.close}
    >
      <form
        className="world-editor"
        onSubmit={async (event) => {
          event.preventDefault();
          setError("");
          if (!value.title.trim() || !value.theme.trim()) return;
          try {
            await props.onSubmit({
              ...value,
              title: value.title.trim(),
              theme: value.theme.trim(),
            });
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      >
        <fieldset className="field-stack" disabled={props.busy}>
          <label>
            World title
            <input
              aria-label="World title"
              required
              maxLength={200}
              value={value.title}
              onChange={(e) => set("title", e.target.value)}
            />
          </label>
          <label>
            Premise
            <textarea
              aria-label="Premise"
              required
              maxLength={1000}
              rows={4}
              value={value.theme}
              onChange={(e) => set("theme", e.target.value)}
              placeholder="Describe the setting and starting situation."
            />
          </label>
          <div className="field-pair">
            <label>
              Story tone
              <select
                value={value.preset}
                onChange={(e) => set("preset", e.target.value)}
              >
                {presets.map((preset) => (
                  <option key={preset} value={preset}>
                    {displayName(preset)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Art style
              <select
                value={value.style_pack}
                onChange={(e) => set("style_pack", e.target.value)}
              >
                {styles.map((style) => (
                  <option key={style} value={style}>
                    {displayName(style)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="switch-row">
            <span>
              <strong>Branching choices</strong>
              <small>
                Choose what happens next at the end of each chapter.
              </small>
            </span>
            <input
              type="checkbox"
              role="switch"
              aria-label="Branching choices"
              checked={value.enable_choices}
              onChange={(e) => set("enable_choices", e.target.checked)}
            />
          </label>
          <fieldset className="audience-field">
            <legend>Audience</legend>
            <div className="segmented-control">
              {["general", "teen", "mature", "explicit"].map((level) => (
                <label key={level}>
                  <input
                    type="radio"
                    name="audience"
                    value={level}
                    checked={value.maturity_level === level}
                    onChange={() => set("maturity_level", level)}
                  />
                  <span>{displayName(level)}</span>
                </label>
              ))}
            </div>
            <p className="field-note">
              Sets the tone and content boundaries for your story. Provider
              restrictions still apply.
            </p>
          </fieldset>
          <details className="advanced-fields">
            <summary>
              Additional details <span>Optional</span>
            </summary>
            <div className="field-stack">
              <label>
                Memory and lore
                <textarea
                  rows={4}
                  maxLength={10000}
                  value={value.memory}
                  onChange={(e) => set("memory", e.target.value)}
                />
              </label>
              <label>
                Author's note
                <textarea
                  rows={2}
                  maxLength={5000}
                  value={value.authors_note}
                  onChange={(e) => set("authors_note", e.target.value)}
                />
              </label>
              <label>
                World instructions
                <textarea
                  rows={3}
                  maxLength={5000}
                  value={value.world_instructions}
                  onChange={(e) => set("world_instructions", e.target.value)}
                />
              </label>
              {props.mode === "edit" && (
                <>
                  <p className="field-note">
                    Saved models are preserved. Clear a model ID to follow the
                    current default in Settings. IDs must belong to the provider
                    selected there.
                  </p>
                  <label>
                    Writing model override
                    <input
                      value={value.text_model ?? ""}
                      maxLength={100}
                      onChange={(e) => set("text_model", e.target.value)}
                      placeholder="Use app default"
                    />
                  </label>
                  <label>
                    Illustration model override
                    <input
                      value={value.image_model ?? ""}
                      maxLength={100}
                      onChange={(e) => set("image_model", e.target.value)}
                      placeholder="Use app default"
                    />
                  </label>
                </>
              )}
            </div>
          </details>
        </fieldset>
        <footer className="save-bar">
          <div>
            {error ? (
              <p className="inline-error" role="alert">
                {error}
              </p>
            ) : dirty ? (
              <span>Unsaved changes</span>
            ) : null}
          </div>
          <div className="save-bar__actions">
            <button
              type="button"
              className="button button--ghost"
              onClick={guard.close}
              disabled={props.busy}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="button"
              disabled={
                props.busy || !value.title.trim() || !value.theme.trim()
              }
            >
              {props.busy
                ? "Saving…"
                : props.mode === "edit"
                  ? "Save world"
                  : "Create world"}
            </button>
          </div>
        </footer>
      </form>
      {guard.confirmation}
    </Workspace>
  );
}
