import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../api";
import TranscriptSegmentEditor from "../components/TranscriptSegmentEditor";

export default function TranscriptReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [episode, setEpisode] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [segments, setSegments] = useState([]);
  const [segmentsDirty, setSegmentsDirty] = useState(false);
  const [approving, setApproving] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get(`/episodes/${id}`),
      api.get(`/episodes/${id}/transcript`).catch(() => []),
    ]).then(([ep, tx]) => {
      setEpisode(ep);
      setSegments(ep.ad_segments || []);
      setTranscript(Array.isArray(tx) ? tx : []);
    }).catch((e) => setError(e.message));
  }, [id]);

  function handleSegmentsChange(next) {
    setSegments(next);
    setSegmentsDirty(true);
  }

  async function approve() {
    setApproving(true);
    setError(null);
    try {
      if (segmentsDirty) {
        await api.patch(`/episodes/${id}/segments`, { ad_segments: segments });
      }
      await api.post(`/episodes/${id}/approve`);
      setMsg("Approved! Audio processing has been queued.");
      setTimeout(() => navigate(`/podcasts/${episode.podcast_id}`), 2000);
    } catch (err) {
      setError(err.message);
      setApproving(false);
    }
  }

  async function saveSegments() {
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/episodes/${id}/segments`, { ad_segments: segments });
      setSegmentsDirty(false);
      setMsg("Segments saved.");
      setTimeout(() => setMsg(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!episode || transcript === null) {
    return (
      <div className="loading-center">
        <div className="spinner" />
        {error && <div className="alert alert-error mt-16">{error}</div>}
      </div>
    );
  }

  const readOnly = episode.status !== "awaiting_review";

  const totalAdMs = segments.reduce((a, s) => a + (s.end_ms - s.start_ms), 0);
  const fmtMs = (ms) => {
    const s = Math.round(ms / 1000);
    return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  return (
    <div style={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-12" style={{ flexWrap: "wrap", gap: 10 }}>
        <div>
          <Link to={`/podcasts/${episode.podcast_id}`} className="text-dim" style={{ fontSize: 12 }}>
            ← Back to Podcast
          </Link>
          <div style={{ fontWeight: 600, fontSize: 15, marginTop: 4 }}>{episode.title}</div>
          <div className="text-dim" style={{ fontSize: 12 }}>
            {readOnly && <span style={{ marginRight: 8, color: "var(--text-muted)" }}>[{episode.status}]</span>}
            {segments.length} ad segment{segments.length !== 1 ? "s" : ""} detected
            {totalAdMs > 0 && ` · ${fmtMs(totalAdMs)} total`}
            {episode.transcript_word_count && ` · ${episode.transcript_word_count.toLocaleString()} words`}
          </div>
        </div>
        <div className="flex gap-8 items-center">
          {error && <span style={{ fontSize: 12, color: "var(--danger)" }}>{error}</span>}
          {msg && <span style={{ fontSize: 12, color: "var(--success)" }}>{msg}</span>}
          {!readOnly && segmentsDirty && (
            <button className="btn btn-ghost btn-sm" onClick={saveSegments} disabled={saving}>
              {saving ? "Saving…" : "Save Segments"}
            </button>
          )}
          {!readOnly && (
            <button
              className="btn btn-success"
              onClick={approve}
              disabled={approving}
            >
              {approving ? "Approving…" : "✓ Approve & Process Audio"}
            </button>
          )}
        </div>
      </div>

      {transcript.length === 0 ? (
        <div className="alert alert-info">
          Transcript not available on disk.
          <div style={{ fontSize: 12, marginTop: 8 }}>
            You can still edit ad segments and approve below.
          </div>
          <div style={{ marginTop: 12 }}>
            {segments.map((seg, idx) => (
              <div key={idx} className="card" style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 13 }}>
                  Segment {idx + 1}: {fmtMs(seg.start_ms)} → {fmtMs(seg.end_ms)}{" "}
                  <span className="text-dim">({(seg.confidence * 100).toFixed(0)}%)</span>
                </div>
                <div className="text-dim" style={{ fontSize: 12 }}>{seg.reason}</div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, overflow: "hidden" }}>
          <TranscriptSegmentEditor
            transcript={transcript}
            segments={segments}
            onChange={handleSegmentsChange}
            readOnly={readOnly}
          />
        </div>
      )}
    </div>
  );
}
