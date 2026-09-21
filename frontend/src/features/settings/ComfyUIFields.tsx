import { useState } from "react";
import { api } from "../../api/client";
import type { SettingsUpdateRequest } from "../../api/types";

type WorkflowNode = {
  class_type: string;
  inputs: Record<string, unknown>;
  _meta?: { title?: string };
};
function promptNodes(workflow: string) {
  try {
    const nodes = JSON.parse(workflow) as Record<string, WorkflowNode>;
    return Object.entries(nodes).filter(
      ([, node]) => typeof node.inputs?.text === "string",
    );
  } catch {
    return [];
  }
}

export function ComfyUIFields({
  address,
  workflow,
  promptNode,
  onChange,
}: {
  address: string;
  workflow: string;
  promptNode: string;
  onChange: (key: keyof SettingsUpdateRequest, value: string) => void;
}) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const nodes = promptNodes(workflow);
  return (
    <div className="local-connection field-stack">
      <label>
        ComfyUI server address
        <input
          type="url"
          value={address}
          onChange={(e) => {
            onChange("comfyui_base_url", e.target.value);
            setMessage("");
          }}
        />
      </label>
      <button
        type="button"
        className="button button--ghost"
        disabled={checking}
        onClick={async () => {
          setChecking(true);
          setError("");
          setMessage("");
          try {
            const result = await api.checkComfyUI(address);
            setMessage(result.message);
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setChecking(false);
          }
        }}
      >
        {checking ? "Checking…" : "Check ComfyUI connection"}
      </button>
      {message && (
        <p role="status" className="field-note">
          {message}
        </p>
      )}
      <label>
        Import image workflow
        <input
          type="file"
          accept=".json,application/json"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            setError("");
            try {
              if (file.size > 1000000)
                throw new Error("Choose a workflow smaller than 1 MB.");
              const text = await file.text();
              const options = promptNodes(text);
              if (!options.length)
                throw new Error(
                  "Use Export (API) in ComfyUI and include a text prompt node.",
                );
              onChange("comfyui_workflow", text);
              // The positive prompt is selected explicitly when a workflow has several text nodes.
              onChange(
                "comfyui_prompt_node",
                options.length === 1 ? options[0][0] : "",
              );
              setMessage(`Imported ${file.name}`);
            } catch (e) {
              setError((e as Error).message);
            }
            e.target.value = "";
          }}
        />
        <small>
          Export a working local workflow in API format from ComfyUI. Its model,
          dimensions, and sampler settings are preserved.
        </small>
      </label>
      {!!nodes.length && (
        <label>
          Scene prompt node
          <select
            required
            value={promptNode}
            onChange={(e) => onChange("comfyui_prompt_node", e.target.value)}
          >
            <option value="">Choose the positive prompt</option>
            {nodes.map(([id, node]) => (
              <option key={id} value={id}>
                {node._meta?.title ?? node.class_type} · {id} ·{" "}
                {String(node.inputs.text).slice(0, 50)}
              </option>
            ))}
          </select>
          <small>
            Each chapter replaces this text with its scene description. Negative
            prompts stay unchanged.
          </small>
        </label>
      )}
      {workflow && (
        <button
          type="button"
          className="text-button"
          onClick={() => {
            onChange("comfyui_workflow", "");
            onChange("comfyui_prompt_node", "");
            setMessage("");
          }}
        >
          Remove workflow
        </button>
      )}
      {error && (
        <p role="alert" className="inline-error">
          {error}
        </p>
      )}
    </div>
  );
}
