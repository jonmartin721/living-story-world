import { useId, useState } from "react";
import type { ProviderOption } from "../../api/types";

export function ProviderFields({
  options,
  provider,
  model,
  onChange,
  label,
  hasKey,
  onConnections,
}: {
  options: Record<string, ProviderOption>;
  provider: string;
  model: string;
  label: string;
  hasKey: boolean;
  onChange: (provider: string, model: string) => void;
  onConnections: () => void;
}) {
  const id = useId();
  const [custom, setCustom] = useState(false);
  const selected = options[provider];
  const selectedModel = selected?.models.find((item) => item.id === model);
  const local =
    provider === "local" || provider === "ollama" || provider === "comfyui";
  return (
    <div className="provider-fields">
      <label>
        {label} provider
        <select
          value={provider}
          onChange={(event) => {
            setCustom(false);
            const next = event.target.value;
            onChange(next, options[next].models[0].id);
          }}
        >
          {!selected && (
            <option value={provider}>{provider || "Choose a provider"}</option>
          )}
          {Object.entries(options).map(([id, entry]) => (
            <option key={id} value={id}>
              {entry.name}
              {entry.billing === "free_tier"
                ? " · free tier"
                : entry.billing === "paid"
                  ? " · paid"
                  : entry.billing === "free"
                    ? " · free"
                    : ""}
            </option>
          ))}
        </select>
      </label>
      {provider !== "none" && (
        <div className="connection-hint">
          <span
            className={`status-dot ${hasKey || local ? "status-dot--ready" : ""}`}
          />
          {provider === "comfyui"
            ? "Local workflow"
            : local
              ? "Local · no API charges"
              : hasKey
                ? "Key saved"
                : "API key needed"}
          {!hasKey && !local && (
            <button
              type="button"
              className="text-button"
              onClick={onConnections}
            >
              Add a key
            </button>
          )}
        </div>
      )}
      {provider !== "none" && provider !== "comfyui" && (
        <>
          <label htmlFor={id}>{label} model</label>
          <select
            id={id}
            value={custom || !selectedModel ? "custom" : model}
            onChange={(event) => {
              if (event.target.value === "custom") setCustom(true);
              else {
                setCustom(false);
                onChange(provider, event.target.value);
              }
            }}
          >
            {selected?.models.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
            <option value="custom">Custom / saved model</option>
          </select>
          {(custom || !selectedModel) && (
            <label>
              Model ID
              <input
                value={model}
                required
                maxLength={100}
                spellCheck={false}
                onChange={(event) => onChange(provider, event.target.value)}
              />
              <small>
                Use a model supported by {selected?.name ?? provider}. Existing
                IDs are kept.
              </small>
            </label>
          )}
        </>
      )}
      {selectedModel && (
        <p className="field-note">
          {selectedModel.note}
          {selectedModel.input_price !== null && !local && (
            <>
              <br />${selectedModel.input_price} input / $
              {selectedModel.output_price} output per million tokens.
            </>
          )}
        </p>
      )}
      {!!selected?.url && (
        <a
          className="provider-link"
          href={selected.url}
          target="_blank"
          rel="noreferrer"
        >
          {local ? "Setup guide" : "Models & pricing"} ↗
        </a>
      )}
    </div>
  );
}
