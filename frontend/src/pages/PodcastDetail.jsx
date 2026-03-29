import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api";
import EpisodeTable from "../components/EpisodeTable";
import FeedUrlDisplay from "../components/FeedUrlDisplay";
import TimeSavedStat from "../components/TimeSavedStat";
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

function fmtDate(iso) {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function PodcastDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [podcast, setPodcast] = useState(null);
  const [episodes, setEpisodes] = useState([]);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [purging, setPurging] = useState(false);
  const formInitialized = useRef(false);

  async function load() {
    try {
      const [p, eps] = await Promise.all([
        api.get(`/podcasts/${id}`),
        api.get(`/episodes?podcast_id=${id}&per_page=100`),
      ]);
      setPodcast(p);
      setEpisodes(eps);
      if (!formInitialized.current) {
        formInitialized.current = true;
        setForm({
          name: p.name,
          rss_url: p.rss_url,
          enabled: p.enabled,
          transcription_backend: p.transcription_backend,
          whisper_model: p.whisper_model,
          llm_backend: p.llm_backend,
          llm_model: p.llm_model,
          ad_confidence_threshold: p.ad_confidence_threshold,
          review_mode: p.review_mode,
          ad_handling: p.ad_handling,
          max_episodes: p.max_episodes,
          keep_original_audio: p.keep_original_audio,
        });
      }
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 8000);
    return () => clearInterval(timer);
  }, [id]);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleBackendChange(newBackend) {
    let newModel;
    if (newBackend === "cloud") {
      newModel = "claude-haiku-4-5-20251001";
    } else {
      try {
        const data = await api.get("/settings/ollama-models");
        newModel = data.models && data.models.length > 0 ? data.models[0] : "";
      } catch {
        newModel = "";
      }
    }
    setForm((f) => ({ ...f, llm_backend: newBackend, llm_model: newModel }));
  }

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.patch(`/podcasts/${id}`, form);
      setPodcast(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function deletePodcast() {
    if (!confirm(`Delete "${podcast.name}" and all its data?`)) return;
    try {
      await api.delete(`/podcasts/${id}`);
      navigate("/podcasts");
    } catch (e) {
      alert(e.message);
    }
  }

  async function refreshMetadata() {
    try {
      const updated = await api.post(`/podcasts/${id}/refresh-metadata`);
      setPodcast(updated);
      setForm((f) => f); // keep form edits, just update the displayed artwork
    } catch (e) {
      alert(e.message);
    }
  }

  async function purgeTranscripts() {
    if (!confirm("Delete all transcript files for this podcast from disk?")) return;
    setPurging(true);
    try {
      const result = await api.post(`/podcasts/${id}/purge-transcripts`);
      alert(`Purged ${result.purged} transcript file${result.purged !== 1 ? "s" : ""}.`);
    } catch (e) {
      alert(e.message);
    } finally {
      setPurging(false);
    }
  }

  if (!podcast || !form) {
    return (
      <div className="loading-center">
        <div className="spinner" />
        {error && <div className="alert alert-error mt-16">{error}</div>}
      </div>
    );
  }

  const reviewEpisodes = episodes.filter((e) => e.status === "awaiting_review");

  return (
    <div style={{ maxWidth: 900 }}>
      {error && <div className="alert alert-error mb-16">{error}</div>}
      {saved && <div className="alert alert-success mb-16">Saved.</div>}

      {reviewEpisodes.length > 0 && (
        <div className="alert alert-warning mb-16">
          ★ {reviewEpisodes.length} episode{reviewEpisodes.length !== 1 ? "s" : ""} awaiting review
        </div>
      )}

      {/* Header: name + stat */}
      <div className="flex items-center justify-between mb-16" style={{ flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>{podcast.name}</h2>
          <div className="text-dim" style={{ fontSize: 12, marginTop: 2 }}>
            Last checked: {fmtDate(podcast.last_checked_at)}
          </div>
        </div>
        <div className="card" style={{ padding: "12px 20px" }}>
          <TimeSavedStat podcastId={id} label="Ad Time Removed" />
        </div>
      </div>

      {/* Feed URL */}
      <div className="card mb-16">
        <div className="flex items-center justify-between mb-8">
          <div className="card-title" style={{ marginBottom: 0 }}>Generated Feed URL</div>
          <div className="flex items-center gap-12">
            {podcast.artwork_url && (
              <img
                src={podcast.artwork_url}
                alt="Podcast artwork"
                style={{ width: 48, height: 48, borderRadius: 6, objectFit: "cover" }}
              />
            )}
            <button className="btn btn-ghost btn-sm" onClick={refreshMetadata}>
              Refresh Metadata
            </button>
          </div>
        </div>
        <FeedUrlDisplay url={podcast.feed_url} />
        <div className="text-dim mt-8" style={{ fontSize: 12 }}>
          Subscribe to this URL in your podcast app for ad-cleaned episodes.
        </div>

        {podcast.rss_url_history && podcast.rss_url_history.length > 0 && (
          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontSize: 12, color: "var(--text-muted)" }}>
              RSS URL history ({podcast.rss_url_history.length})
            </summary>
            <div style={{ marginTop: 8 }}>
              {[...podcast.rss_url_history].reverse().map((h, i) => (
                <div key={i} style={{ fontSize: 11.5, color: "var(--text-dim)", padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
                  <code style={{ marginRight: 8 }}>{h.url}</code>
                  <span>{fmtDate(h.replaced_at)}</span>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>

      {/* Settings form */}
      <form onSubmit={save}>
        <div className="card mb-16">
          <div className="flex items-center justify-between mb-12">
            <div className="card-title" style={{ marginBottom: 0 }}>Settings</div>
            <label className="toggle" title={form.enabled ? "Enabled" : "Disabled"}>
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => set("enabled", e.target.checked)}
              />
              <span className="toggle-slider" />
            </label>
          </div>

          <div className="grid-2">
            <Field label="Name">
              <input type="text" value={form.name} onChange={(e) => set("name", e.target.value)} />
            </Field>
            <Field label="RSS Feed URL">
              <input type="url" value={form.rss_url} onChange={(e) => set("rss_url", e.target.value)} />
            </Field>
            <Field label="Transcription Backend">
              <select value={form.transcription_backend} onChange={(e) => set("transcription_backend", e.target.value)}>
                <option value="local">Local (Whisper)</option>
                <option value="cloud">Cloud (not implemented in v1)</option>
              </select>
            </Field>
            <Field label="Whisper Model">
              <select value={form.whisper_model} onChange={(e) => set("whisper_model", e.target.value)}>
                <option value="tiny">Tiny</option>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
              </select>
            </Field>
            <Field label="LLM Backend">
              <select value={form.llm_backend} onChange={(e) => handleBackendChange(e.target.value)}>
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
            <Field label="Ad Confidence Threshold">
              <input
                type="number" min="0" max="1" step="0.05"
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
            <Field label="Ad Handling">
              <select value={form.ad_handling} onChange={(e) => set("ad_handling", e.target.value)}>
                <option value="chapters">Chapters</option>
                <option value="splice">Splice</option>
              </select>
            </Field>
            <Field label="Max Episodes" hint="0 = unlimited">
              <input
                type="number" min="0"
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

          <div className="flex gap-12 mt-8">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>
      </form>

      {/* Episodes */}
      <div className="card mb-16" style={{ padding: 0 }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
          <div className="card-title" style={{ marginBottom: 0 }}>Episodes</div>
        </div>
        <EpisodeTable
          episodes={episodes}
          onRefresh={load}
        />
      </div>

      {/* Danger zone */}
      <div className="card" style={{ borderColor: "rgba(239,68,68,0.3)" }}>
        <div className="card-title" style={{ color: "var(--danger)" }}>Danger Zone</div>
        <div className="flex gap-12" style={{ flexWrap: "wrap" }}>
          <button className="btn btn-ghost btn-sm" onClick={purgeTranscripts} disabled={purging}>
            {purging ? "Purging…" : "Purge Transcript Files"}
          </button>
          <button
            className="btn btn-ghost btn-sm"
            style={{ color: "var(--danger)", borderColor: "rgba(239,68,68,0.4)" }}
            onClick={deletePodcast}
          >
            Delete Podcast
          </button>
        </div>
        <div className="text-dim mt-8" style={{ fontSize: 12 }}>
          Purging transcripts frees disk space. Episode records and word counts are retained. Deleting removes all data.
        </div>
      </div>
    </div>
  );
}
