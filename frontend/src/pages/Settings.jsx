import { useState, useEffect } from "react";
import { api } from "../api";
import HealthPanel from "../components/HealthPanel";
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

function SelectField({ label, hint, value, onChange, options }) {
  return (
    <Field label={label} hint={hint}>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
    </Field>
  );
}

const POLL_PRESETS = [
  ["*/15 * * * *", "Every 15 minutes"],
  ["*/30 * * * *", "Every 30 minutes"],
  ["0 * * * *",   "Every hour"],
  ["0 */2 * * *", "Every 2 hours"],
  ["0 */6 * * *", "Every 6 hours"],
  ["0 */12 * * *","Every 12 hours"],
  ["0 0 * * *",   "Once a day (midnight)"],
];

function PollScheduleField({ value, onChange }) {
  const isPreset = POLL_PRESETS.some(([v]) => v === value);

  return (
    <Field label="Feed Poll Schedule">
      <select
        value={isPreset ? value : "__custom__"}
        onChange={(e) => {
          if (e.target.value !== "__custom__") onChange(e.target.value);
        }}
      >
        {POLL_PRESETS.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
        {!isPreset && <option value="__custom__">Custom: {value}</option>}
      </select>
    </Field>
  );
}

export default function Settings() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [restoring, setRestoring] = useState(false);
  const [restoreMsg, setRestoreMsg] = useState(null);

  useEffect(() => {
    api.get("/settings").then((s) => {
      setForm({ ...s, anthropic_api_key: s.anthropic_api_key || "" });
    }).catch((e) => setError(e.message));
  }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = { ...form };
      if (!payload.anthropic_api_key) delete payload.anthropic_api_key;
      await api.patch("/settings", payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function restore(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!confirm("Restore from backup? This will replace the current database and .env.")) {
      e.target.value = "";
      return;
    }
    setRestoring(true);
    setRestoreMsg(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const result = await api.upload("/settings/restore", fd);
      setRestoreMsg({ type: "success", text: result.message });
    } catch (err) {
      setRestoreMsg({ type: "error", text: err.message });
    } finally {
      setRestoring(false);
      e.target.value = "";
    }
  }

  if (!form) {
    return (
      <div className="loading-center">
        <div className="spinner" />
        {error && <div className="alert alert-error mt-16">{error}</div>}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 800 }}>
      {error && <div className="alert alert-error mb-16">{error}</div>}
      {saved && <div className="alert alert-success mb-16">Settings saved.</div>}

      <form onSubmit={save}>
        <div className="card mb-16">
          <div className="card-title">Global Configuration</div>

          <SelectField
            label="Device Mode"
            value={form.device_mode}
            onChange={(v) => set("device_mode", v)}
            options={[
              ["auto", "Auto — use GPU if available, fall back to CPU"],
              ["gpu_required", "GPU Required — fail if GPU unavailable"],
              ["cpu_only", "CPU Only — never use GPU"],
            ]}
            hint="Applies to all local AI processing (Whisper + Ollama)"
          />

          <Field label="Application Base URL" hint="Used to generate RSS feed URLs">
            <input
              type="url"
              value={form.app_base_url}
              onChange={(e) => set("app_base_url", e.target.value)}
            />
          </Field>

          <PollScheduleField
            value={form.feed_poll_schedule}
            onChange={(v) => set("feed_poll_schedule", v)}
          />
        </div>

        <div className="card mb-16">
          <div className="card-title">External Services</div>

          <Field label="Ollama Base URL">
            <input
              type="url"
              value={form.ollama_base_url}
              onChange={(e) => set("ollama_base_url", e.target.value)}
            />
          </Field>

          <Field label="Anthropic API Key" hint="Required for cloud LLM. Leave blank to keep existing key.">
            <input
              type="password"
              value={form.anthropic_api_key}
              onChange={(e) => set("anthropic_api_key", e.target.value)}
              placeholder="sk-ant-…"
              autoComplete="off"
            />
          </Field>
        </div>

        <div className="card mb-16">
          <div className="card-title">Default Settings for New Podcasts</div>

          <div className="grid-2">
            <SelectField
              label="Transcription Backend"
              value={form.default_transcription_backend}
              onChange={(v) => set("default_transcription_backend", v)}
              options={[["local", "Local (Whisper)"], ["cloud", "Cloud (not implemented in v1)"]]}
            />
            <SelectField
              label="Whisper Model"
              value={form.default_whisper_model}
              onChange={(v) => set("default_whisper_model", v)}
              options={[
                ["tiny", "Tiny (~0.1× realtime on CPU)"],
                ["small", "Small (~0.3× realtime on CPU)"],
                ["medium", "Medium (~0.7× realtime on CPU)"],
                ["large", "Large (~1.5× realtime on CPU)"],
              ]}
            />
            <SelectField
              label="LLM Backend"
              value={form.default_llm_backend}
              onChange={(v) => set("default_llm_backend", v)}
              options={[["local", "Local (Ollama)"], ["cloud", "Cloud (Anthropic)"]]}
            />
            <Field label="LLM Model">
              <LlmModelSelect
                backend={form.default_llm_backend}
                value={form.default_llm_model}
                onChange={(v) => set("default_llm_model", v)}
              />
            </Field>
            <SelectField
              label="Ad Handling"
              value={form.default_ad_handling}
              onChange={(v) => set("default_ad_handling", v)}
              options={[["chapters", "Chapters (no re-encode)"], ["splice", "Splice (remove audio)"]]}
            />
            <SelectField
              label="Review Mode"
              value={form.default_review_mode}
              onChange={(v) => set("default_review_mode", v)}
              options={[
                ["none", "None (fully automatic)"],
                ["before_audio", "Before Audio (pause for review)"],
                ["after_processing", "After Processing"],
              ]}
            />
            <Field label="Ad Confidence Threshold" hint="Segments below this are discarded (0.0–1.0)">
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={form.default_ad_confidence_threshold}
                onChange={(e) => set("default_ad_confidence_threshold", parseFloat(e.target.value))}
              />
            </Field>
            <Field label="Max Episodes per Podcast" hint="0 = unlimited">
              <input
                type="number"
                min="0"
                value={form.default_max_episodes}
                onChange={(e) => set("default_max_episodes", parseInt(e.target.value, 10))}
              />
            </Field>
          </div>

          <div className="form-group" style={{ marginTop: 8 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", textTransform: "none", letterSpacing: 0 }}>
              <input
                type="checkbox"
                checked={form.default_keep_original_audio}
                onChange={(e) => set("default_keep_original_audio", e.target.checked)}
              />
              Keep original audio after processing
            </label>
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save Settings"}
        </button>
      </form>

      <hr className="divider" />

      <div className="card mb-16">
        <div className="card-title">Backup & Restore</div>
        <div className="flex gap-12" style={{ flexWrap: "wrap" }}>
          <a
            href="/api/settings/backup"
            download="podclean-backup.zip"
            className="btn btn-ghost"
          >
            ↓ Download Backup
          </a>
          <label className="btn btn-ghost" style={{ cursor: "pointer", opacity: restoring ? 0.5 : 1 }}>
            {restoring ? "Restoring…" : "↑ Restore from Backup"}
            <input
              type="file"
              accept=".zip"
              style={{ display: "none" }}
              onChange={restore}
              disabled={restoring}
            />
          </label>
        </div>
        {restoreMsg && (
          <div className={`alert alert-${restoreMsg.type} mt-8`}>
            {restoreMsg.text}
          </div>
        )}
        <div className="text-dim mt-8" style={{ fontSize: 12 }}>
          Backup contains only the database and .env — no audio files.
        </div>
      </div>

      <hr className="divider" />

      <HealthPanel />
    </div>
  );
}
