import { useEffect, useState } from "react";
import type { RandomWorldResponse, SettingsResponse, WorldDetail, WorldInput } from "../../api/types";

const styles = ["storybook-ink", "watercolor-dream", "pixel-rpg", "comic-book", "noir-sketch", "art-nouveau", "oil-painting", "lowpoly-iso"];
const presets = ["cozy-adventure", "noir-mystery", "epic-fantasy", "solarpunk-explorer", "gothic-horror", "space-opera", "slice-of-life", "cosmic-horror", "cyberpunk-noir", "whimsical-fairy-tale", "post-apocalyptic", "historical-intrigue"];
const defaults: WorldInput = {
  title: "", theme: "", style_pack: "storybook-ink", maturity_level: "general",
  preset: "cozy-adventure", enable_choices: false, memory: "", authors_note: "", world_instructions: "",
};

type Props = {
  mode: "create" | "edit";
  world: WorldDetail | null;
  randomWorld: RandomWorldResponse | null;
  busy: boolean;
  onCancel: () => void;
  onSubmit: (value: WorldInput) => void;
  settings?: Pick<SettingsResponse, "default_style_pack" | "default_preset"> | null;
};

function initialValue({ mode, world, randomWorld, settings }: Props): WorldInput {
  const source = mode === "edit" ? world?.config : randomWorld;
  if (!source) return {
    ...defaults,
    style_pack: settings?.default_style_pack ?? defaults.style_pack,
    preset: settings?.default_preset ?? defaults.preset,
  };
  return {
    title: source.title, theme: source.theme, style_pack: source.style_pack,
    maturity_level: source.maturity_level, preset: source.preset,
    enable_choices: "enable_choices" in source ? source.enable_choices : false,
    memory: source.memory ?? "",
    authors_note: "authors_note" in source ? source.authors_note ?? "" : "",
    world_instructions: "world_instructions" in source ? source.world_instructions ?? "" : "",
  };
}

export function WorldEditor(props: Props) {
  const [value, setValue] = useState<WorldInput>(() => initialValue(props));
  useEffect(() => setValue(initialValue(props)), [props.mode, props.world, props.randomWorld]);
  const set = (key: keyof WorldInput, text: string | boolean) => setValue((previous) => ({ ...previous, [key]: text }));
  return (
    <section className="panel editor">
      <div className="panel__eyebrow">World details</div>
      <h2>{props.mode === "edit" ? "Edit world" : "New world"}</h2>
      <form className="form-grid" onSubmit={(event) => {
        event.preventDefault();
        if (value.title.trim() && value.theme.trim()) props.onSubmit({ ...value, title: value.title.trim(), theme: value.theme.trim() });
      }}>
        <label>Title<input required maxLength={200} value={value.title} onChange={(event) => set("title", event.target.value)} /></label>
        <label>Theme<textarea required maxLength={1000} rows={3} value={value.theme} onChange={(event) => set("theme", event.target.value)} /></label>
        <label>Art style<select value={value.style_pack} onChange={(event) => set("style_pack", event.target.value)}>{styles.map((style) => <option key={style}>{style}</option>)}</select></label>
        <label>Story preset<select value={value.preset} onChange={(event) => set("preset", event.target.value)}>{presets.map((preset) => <option key={preset}>{preset}</option>)}</select></label>
        <label>Audience<select value={value.maturity_level} onChange={(event) => set("maturity_level", event.target.value)}>{["general", "teen", "mature", "explicit"].map((level) => <option key={level}>{level}</option>)}</select></label>
        <label className="checkbox-row"><input type="checkbox" checked={value.enable_choices} onChange={(event) => set("enable_choices", event.target.checked)} />Offer choices after chapters</label>
        <label>Memory and lore<textarea rows={4} maxLength={10000} value={value.memory} onChange={(event) => set("memory", event.target.value)} /></label>
        <label>Author's note<textarea rows={2} maxLength={5000} value={value.authors_note} onChange={(event) => set("authors_note", event.target.value)} /></label>
        <label>World instructions<textarea rows={3} maxLength={5000} value={value.world_instructions} onChange={(event) => set("world_instructions", event.target.value)} /></label>
        <div className="editor__actions">
          <button type="submit" className="button" disabled={props.busy || !value.title.trim() || !value.theme.trim()}>{props.mode === "edit" ? "Save world" : "Create world"}</button>
          <button type="button" className="button button--ghost" onClick={props.onCancel} disabled={props.busy}>Cancel</button>
        </div>
      </form>
    </section>
  );
}
