import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import LlmModelSelect from "../components/LlmModelSelect";

function Field({ label, hint, children }) {
  return (
    <div className="form-group">
      <label>{label}</label>
      {children}
      {hint && <div style={{ fontSize: 11.5, color: "var(--text-dim)", marginTop: 4 }}>{hint}</div>}
    </div>
  );
}

export default function AddPodcast() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    rss_url: "",
    name: "",
    transcription_backend: "local",
    whisper_model: "small",
    llm_backend: "local",
    llm_model: "llama3",
    ad_confidence_threshold: 0.7,
    review_mode: "none",
    ad_handling: "chapters",
    max_episodes: 10,
    keep_original_audio: true,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    if (!form.rss_url.trim()) { setError("RSS URL is required."); return; }
    setSubmitting(true);
    setError(null);
    try {
      const payload = { ...form };
      if (!payload.name.trim()) delete payload.name;
      const podcast = await api.post("/podcasts", payload);
      navigate(`/podcasts/${podcast.id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: 700 }}>
      <div className="alert alert-info mb-16" style={{ fontSize: 13 }}>
        Only the most recent episode will be processed on first add. All older episodes are recorded as skipped.
      </div>

      {error && <div className="alert alert-error mb-16">{error}</div>}

      <form onSubmit={submit}>
        <div className="card mb-16">
          <div className="card-title">Feed</div>

          <Field label="RSS Feed URL" hint="The podcast RSS feed URL">
            <input
              type="url"
              value={form.rss_url}
              onChange={(e) => set("rss_url", e.target.value)}
              placeholder="https://feeds.example.com/podcast.rss"
              required
              autoFocus
            />
          </Field>

          <Field label="Name (optional)" hint="Leave blank to auto-detect from feed metadata">
            <input
              type="text"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Auto-detected from feed"
            />
          </Field>
        </div>

        <div className="card mb-16">
          <div className="card-title">Transcription</div>
          <div className="grid-2">
            <Field label="Backend">
              <select value={form.transcription_backend} onChange={(e) => set("transcription_backend", e.target.value)}>
                <option value="local">Local (Whisper)</option>
                <option value="cloud">Cloud (not implemented in v1)</option>
              </select>
            </Field>
            <Field label="Whisper Model">
              <select value={form.whisper_model} onChange={(e) => set("whisper_model", e.target.value)}>
                <option value="tiny">Tiny (~0.1× realtime on CPU)</option>
                <option value="small">Small (~0.3× realtime on CPU)</option>
                <option value="medium">Medium (~0.7× realtime on CPU)</option>
                <option value="large">Large (~1.5× realtime on CPU)</option>
              </select>
            </Field>
          </div>
        </div>

        <div className="card mb-16">
          <div className="card-title">Ad Classification</div>
          <div className="grid-2">
            <Field label="LLM Backend">
              <select value={form.llm_backend} onChange={(e) => set("llm_backend", e.target.value)}>
                <option value="local">Local (Ollama)</option>
                <option value="cloud">Cloud (Anthropic)</option>
              </select>
            </Field>
            <Field label="LLM Model">
              <LlmModelSelect
                backend={form.llm_backend}
                value={form.llm_model}
                onChange={(v) => set("llm_model", v)}
              />
            </Field>
            <Field label="Confidence Threshold" hint="Segments below this are discarded (0.0–1.0)">
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={form.ad_confidence_threshold}
                onChange={(e) => set("ad_confidence_threshold", parseFloat(e.target.value))}
              />
            </Field>
            <Field label="Review Mode">
              <select value={form.review_mode} onChange={(e) => set("review_mode", e.target.value)}>
                <option value="none">None (fully automatic)</option>
                <option value="before_audio">Before Audio (pause for review)</option>
                <option value="after_processing">After Processing</option>
              </select>
            </Field>
          </div>
        </div>

        <div className="card mb-16">
          <div className="card-title">Output</div>
          <div className="grid-2">
            <Field label="Ad Handling">
              <select value={form.ad_handling} onChange={(e) => set("ad_handling", e.target.value)}>
                <option value="chapters">Chapters (mark with metadata, no re-encode)</option>
                <option value="splice">Splice (physically remove ad audio)</option>
              </select>
            </Field>
            <Field label="Max Episodes" hint="0 = unlimited">
              <input
                type="number"
                min="0"
                value={form.max_episodes}
                onChange={(e) => set("max_episodes", parseInt(e.target.value, 10))}
              />
            </Field>
          </div>
          <div className="form-group">
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", textTransform: "none", letterSpacing: 0 }}>
              <input
                type="checkbox"
                checked={form.keep_original_audio}
                onChange={(e) => set("keep_original_audio", e.target.checked)}
              />
              Keep original audio after processing
            </label>
          </div>
        </div>

        <div className="flex gap-12">
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Adding…" : "Add Podcast"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => navigate("/podcasts")}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
