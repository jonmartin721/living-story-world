import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import type {
  ProviderCatalog,
  SettingsResponse,
  SettingsUpdateRequest,
} from "../../api/types";
import { Workspace } from "../../components/Workspace";
import { Dialog } from "../../components/Dialog";
import { useUnsavedChanges } from "../../hooks/useUnsavedChanges";
import { displayName, presets, styles } from "../worlds/options";
import { connections, hasProviderKey } from "./connections";
import { ProviderFields } from "./ProviderFields";
import { ComfyUIFields } from "./ComfyUIFields";

type Props = {
  settings: SettingsResponse | null;
  busy: boolean;
  onSave: (value: SettingsUpdateRequest) => Promise<void> | void;
  onClearKeys: () => Promise<void> | void;
  onClose?: () => void;
  onAppearance?: () => void;
};

export function SettingsPanel({
  settings,
  busy,
  onSave,
  onClearKeys,
  onClose = () => {},
  onAppearance,
}: Props) {
  const [changes, setChanges] = useState<SettingsUpdateRequest>({});
  const [section, setSection] = useState("generation");
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [clearConfirm, setClearConfirm] = useState(false);
  const [localModels, setLocalModels] = useState<string[]>([]);
  const [checking, setChecking] = useState(false);
  const [connectionResult, setConnectionResult] = useState("");
  const dirtyCount = Object.keys(changes).length;
  const guard = useUnsavedChanges(dirtyCount > 0, () => {
    if (!busy) onClose();
  });
  const form = { ...settings, ...changes };
  const connectionIdentity = useRef("");
  connectionIdentity.current = `${form.text_provider}|${form.text_provider === "ollama" ? form.ollama_base_url : form.local_base_url}`;
  const textOptions =
    catalog && form.text_provider && localModels.length
      ? {
          ...catalog.text,
          [form.text_provider]: {
            ...catalog.text[form.text_provider],
            models: [
              ...catalog.text[form.text_provider].models,
              ...localModels
                .filter(
                  (id) =>
                    !catalog.text[form.text_provider!].models.some(
                      (model) => model.id === id,
                    ),
                )
                .map((id) => ({
                  id,
                  name: id,
                  note: "Available on your local server",
                  input_price: 0,
                  output_price: 0,
                })),
            ],
          },
        }
      : catalog?.text;

  const loadCatalog = () => {
    setCatalogError("");
    void api
      .getProviders()
      .then(setCatalog)
      .catch((e: Error) => setCatalogError(e.message));
  };
  useEffect(loadCatalog, []);
  const change = (key: keyof SettingsUpdateRequest, value: string) => {
    setSaved(false);
    setChanges((current) => {
      const next = { ...current, [key]: value };
      const original = settings?.[key as keyof SettingsResponse] ?? "";
      if (value === original) delete next[key];
      return next;
    });
  };
  const save = async () => {
    setError("");
    try {
      await onSave(changes);
      setChanges({});
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Workspace wide title="Settings" onBack={guard.close}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <div className="settings-workspace">
          <nav className="settings-nav" aria-label="Settings sections">
            {[
              ["generation", "Story generation"],
              ["worlds", "New worlds"],
              ["connections", "Connections"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-current={section === id ? "page" : undefined}
                onClick={() => {
                  setSection(id);
                  setError("");
                }}
              >
                {label}
              </button>
            ))}
            {onAppearance && (
              <button
                className="settings-nav__secondary"
                type="button"
                onClick={() => {
                  if (!dirtyCount) onAppearance();
                  else
                    setError(
                      "Save your changes or go back before opening reading appearance.",
                    );
                }}
              >
                Reading appearance ↗
              </button>
            )}
          </nav>
          <fieldset disabled={busy} className="settings-content">
            {!settings ? (
              <p role="status">Loading your settings…</p>
            ) : (
              <>
                {section === "generation" && (
                  <>
                    <div className="section-intro">
                      <h2>Story generation</h2>
                      <p>Existing worlds keep their saved model overrides.</p>
                    </div>
                    {catalogError && (
                      <div className="inline-error" role="alert">
                        {catalogError}{" "}
                        <button
                          type="button"
                          className="text-button"
                          onClick={loadCatalog}
                        >
                          Retry model list
                        </button>
                      </div>
                    )}
                    {!catalog && !catalogError && (
                      <p role="status">Loading available services…</p>
                    )}
                    {catalog &&
                      (
                        [
                          ["text", "Writing"],
                          ["image", "Illustrations"],
                        ] as const
                      ).map(([kind, title]) => (
                        <section className="setting-section" key={kind}>
                          <div>
                            <h3>{title}</h3>
                          </div>
                          <div>
                            <ProviderFields
                              label={title}
                              options={
                                kind === "text" ? textOptions! : catalog.image
                              }
                              provider={form[`${kind}_provider`] ?? ""}
                              model={form[`default_${kind}_model`] ?? ""}
                              hasKey={hasProviderKey(
                                settings,
                                form[`${kind}_provider`] ?? "",
                              )}
                              onConnections={() => setSection("connections")}
                              onChange={(provider, model) => {
                                change(`${kind}_provider`, provider);
                                change(`default_${kind}_model`, model);
                                if (
                                  kind === "text" &&
                                  provider !== form.text_provider
                                ) {
                                  setLocalModels([]);
                                  setConnectionResult("");
                                }
                              }}
                            />
                            {kind === "text" &&
                              (form.text_provider === "ollama" ||
                                form.text_provider === "local") && (
                                <div className="local-connection field-stack">
                                  <label>
                                    Server address
                                    <input
                                      type="url"
                                      value={
                                        form.text_provider === "ollama"
                                          ? (form.ollama_base_url ??
                                            "http://127.0.0.1:11434/v1")
                                          : (form.local_base_url ??
                                            "http://127.0.0.1:1234/v1")
                                      }
                                      onChange={(e) => {
                                        change(
                                          form.text_provider === "ollama"
                                            ? "ollama_base_url"
                                            : "local_base_url",
                                          e.target.value,
                                        );
                                        setConnectionResult("");
                                        setLocalModels([]);
                                      }}
                                    />
                                    <small>
                                      The server runs on this computer. No cloud
                                      fallback is used.
                                    </small>
                                  </label>
                                  <button
                                    className="button button--ghost"
                                    type="button"
                                    disabled={checking}
                                    onClick={async () => {
                                      const identity =
                                        connectionIdentity.current;
                                      setChecking(true);
                                      setConnectionResult("");
                                      setLocalModels([]);
                                      try {
                                        const result =
                                          await api.checkLocalModels(
                                            form.text_provider!,
                                            (form.text_provider === "ollama"
                                              ? form.ollama_base_url
                                              : form.local_base_url) ??
                                              (form.text_provider === "ollama"
                                                ? "http://127.0.0.1:11434/v1"
                                                : "http://127.0.0.1:1234/v1"),
                                          );
                                        if (
                                          identity !==
                                          connectionIdentity.current
                                        )
                                          return;
                                        setLocalModels(result.models);
                                        setConnectionResult(
                                          result.models.length
                                            ? `Connected · ${result.models.length} ${result.models.length === 1 ? "model" : "models"} available`
                                            : "Connected, but no models are loaded yet.",
                                        );
                                      } catch (e) {
                                        if (
                                          identity ===
                                          connectionIdentity.current
                                        )
                                          setConnectionResult(
                                            (e as Error).message,
                                          );
                                      } finally {
                                        setChecking(false);
                                      }
                                    }}
                                  >
                                    {checking
                                      ? "Checking…"
                                      : "Check connection"}
                                  </button>
                                  {connectionResult && (
                                    <p className="field-note" role="status">
                                      {connectionResult}
                                    </p>
                                  )}
                                  <label>
                                    Reasoning
                                    <select
                                      value={
                                        form.local_reasoning_effort ?? "none"
                                      }
                                      onChange={(e) =>
                                        change(
                                          "local_reasoning_effort",
                                          e.target.value,
                                        )
                                      }
                                    >
                                      <option value="none">
                                        Off · faster storytelling
                                      </option>
                                      <option value="low">Low</option>
                                      <option value="medium">Medium</option>
                                      <option value="high">
                                        High · slower
                                      </option>
                                      <option value="default">
                                        Use server default
                                      </option>
                                    </select>
                                    <small>
                                      If your server does not support reasoning
                                      controls, choose its default.
                                    </small>
                                  </label>
                                </div>
                              )}
                            {kind === "image" &&
                              form.image_provider === "comfyui" && (
                                <ComfyUIFields
                                  address={
                                    form.comfyui_base_url ??
                                    "http://127.0.0.1:8188"
                                  }
                                  workflow={form.comfyui_workflow ?? ""}
                                  promptNode={form.comfyui_prompt_node ?? ""}
                                  onChange={change}
                                />
                              )}
                          </div>
                        </section>
                      ))}
                    <details className="advanced-fields">
                      <summary>
                        Writing instructions <span>Optional</span>
                      </summary>
                      <label>
                        Instructions for every world
                        <textarea
                          rows={5}
                          maxLength={10000}
                          value={form.global_instructions ?? ""}
                          onChange={(e) =>
                            change("global_instructions", e.target.value)
                          }
                        />
                      </label>
                    </details>
                    {catalog && (
                      <p className="field-note">
                        Standard USD pricing reviewed {catalog.reviewed_on}.
                        Estimates exclude caching and account discounts. Free
                        tiers have limits.
                      </p>
                    )}
                  </>
                )}
                {section === "worlds" && (
                  <>
                    <div className="section-intro">
                      <h2>New worlds</h2>
                      <p>Defaults for newly created worlds.</p>
                    </div>
                    <section className="setting-section">
                      <div>
                        <h3>Story and art</h3>
                      </div>
                      <div className="field-stack">
                        <label>
                          Default story tone
                          <select
                            value={form.default_preset ?? ""}
                            onChange={(e) =>
                              change("default_preset", e.target.value)
                            }
                          >
                            {presets.map((value) => (
                              <option key={value} value={value}>
                                {displayName(value)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Default art style
                          <select
                            value={form.default_style_pack ?? ""}
                            onChange={(e) =>
                              change("default_style_pack", e.target.value)
                            }
                          >
                            {styles.map((value) => (
                              <option key={value} value={value}>
                                {displayName(value)}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                    </section>
                  </>
                )}
                {section === "connections" && (
                  <>
                    <div className="section-intro">
                      <h2>Connections</h2>
                      <p>
                        Add keys only for services you want to use. Keys are
                        stored on this computer and used with the selected
                        service. A saved key has not necessarily been verified.
                      </p>
                    </div>
                    <div className="connections-list">
                      {connections.map((connection) => (
                        <details key={connection.id} className="connection-row">
                          <summary>
                            <span>{connection.name}</span>
                            <span className="connection-hint">
                              <i
                                className={`status-dot ${settings[connection.status] ? "status-dot--ready" : ""}`}
                              />
                              {settings[connection.status]
                                ? "Key saved"
                                : "Not configured"}
                            </span>
                          </summary>
                          <label>
                            {connection.name} API key
                            <input
                              type="password"
                              autoComplete="new-password"
                              spellCheck={false}
                              value={changes[connection.key] ?? ""}
                              placeholder={
                                settings[connection.status]
                                  ? "Paste a replacement key"
                                  : "Paste your API key"
                              }
                              onChange={(e) =>
                                change(connection.key, e.target.value)
                              }
                            />
                            <small>
                              Leave blank to keep the existing key. Stored in
                              your local settings file.
                            </small>
                          </label>
                        </details>
                      ))}
                    </div>
                    <div className="connection-removal">
                      <p>Remove saved keys for all services.</p>
                      <button
                        type="button"
                        className="text-button danger-text"
                        disabled={busy}
                        onClick={() => setClearConfirm(true)}
                      >
                        Clear all API keys…
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </fieldset>
        </div>
        <footer className="save-bar">
          <div aria-live="polite">
            {error ? (
              <p className="inline-error" role="alert">
                {error}
              </p>
            ) : saved ? (
              "Changes saved"
            ) : dirtyCount ? (
              `${dirtyCount} unsaved ${dirtyCount === 1 ? "change" : "changes"}`
            ) : (
              "All changes saved"
            )}
          </div>
          <div className="save-bar__actions">
            <button
              type="button"
              className="button button--ghost"
              disabled={busy}
              onClick={guard.close}
            >
              Cancel
            </button>
            <button
              className="button"
              type="submit"
              disabled={busy || !dirtyCount}
            >
              {busy ? "Saving…" : "Save changes"}
            </button>
          </div>
        </footer>
      </form>
      {guard.confirmation}
      {clearConfirm && (
        <Dialog
          title="Clear all API keys?"
          onClose={() => setClearConfirm(false)}
        >
          <p>
            This removes keys from the app settings and this server session.
            Keys supplied by an environment file may return after a restart.
          </p>
          <div className="editor__actions">
            <button
              type="button"
              className="button button--ghost"
              onClick={() => setClearConfirm(false)}
            >
              Keep keys
            </button>
            <button
              type="button"
              className="button button--danger"
              disabled={busy}
              onClick={async () => {
                try {
                  await onClearKeys();
                  setClearConfirm(false);
                  setChanges((current) =>
                    Object.fromEntries(
                      Object.entries(current).filter(
                        ([key]) => !connections.some((c) => c.key === key),
                      ),
                    ),
                  );
                } catch (e) {
                  setError((e as Error).message);
                  setClearConfirm(false);
                }
              }}
            >
              Clear keys
            </button>
          </div>
        </Dialog>
      )}
    </Workspace>
  );
}
