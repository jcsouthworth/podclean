import { useState, useEffect } from "react";
import { api } from "../api";

const ANTHROPIC_MODELS = [
  "claude-opus-4-6",
  "claude-sonnet-4-6",
  "claude-haiku-4-5-20251001",
  "claude-opus-4-5",
  "claude-sonnet-4-5",
  "claude-haiku-4-5",
];

export default function LlmModelSelect({ backend, value, onChange }) {
  const [ollamaModels, setOllamaModels] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (backend !== "local") return;
    setLoading(true);
    setError(null);
    api.get("/settings/ollama-models")
      .then((d) => { setOllamaModels(d.models); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [backend]);

  if (backend === "cloud") {
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {ANTHROPIC_MODELS.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
    );
  }

  // local / Ollama
  if (loading) {
    return <select disabled><option>Loading models…</option></select>;
  }

  if (error || !ollamaModels) {
    // Fallback to text input if Ollama is unreachable
    return (
      <div>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="llama3.2"
        />
        <div style={{ fontSize: 11.5, color: "var(--warning)", marginTop: 4 }}>
          Could not reach Ollama to list models — enter model name manually.
        </div>
      </div>
    );
  }

  if (ollamaModels.length === 0) {
    return (
      <div>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="llama3.2"
        />
        <div style={{ fontSize: 11.5, color: "var(--text-dim)", marginTop: 4 }}>
          No models found in Ollama. Run <code>docker compose exec ollama ollama pull llama3.2</code> first.
        </div>
      </div>
    );
  }

  // If the saved value isn't in the list (e.g. stale config), add it
  const options = ollamaModels.includes(value)
    ? ollamaModels
    : [value, ...ollamaModels];

  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((m) => (
        <option key={m} value={m}>{m}</option>
      ))}
    </select>
  );
}
