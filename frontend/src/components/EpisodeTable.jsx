import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import EpisodeProgress from "./EpisodeProgress";
import { api } from "../api";

function fmtMs(ms) {
  if (!ms) return null;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  if (m < 60) return rem ? `${m}m ${rem}s` : `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function EpisodeTable({ episodes, onRefresh, showPodcast }) {
  async function reprocess(id) {
    if (!confirm("Re-trigger full processing for this episode?")) return;
    try {
      await api.post(`/episodes/${id}/reprocess`);
      onRefresh?.();
    } catch (e) {
      alert(e.message);
    }
  }

  async function cancel(id) {
    if (!confirm("Cancel processing for this episode?")) return;
    try {
      await api.post(`/episodes/${id}/cancel`);
      onRefresh?.();
    } catch (e) {
      alert(e.message);
    }
  }

  if (!episodes || episodes.length === 0) {
    return (
      <div className="empty-state">
        <div>No episodes</div>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Title</th>
            {showPodcast && <th>Podcast</th>}
            <th>Published</th>
            <th>Status</th>
            <th>Ad Time</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {episodes.map((ep) => {
            const isActive = ["downloading", "transcribing", "classifying", "processing_audio"].includes(ep.status);
            const isTerminal = ["complete", "failed", "skipped"].includes(ep.status);
            const isReview = ep.status === "awaiting_review";

            return (
              <tr
                key={ep.id}
                style={isReview ? { background: "rgba(245,158,11,0.06)" } : undefined}
              >
                <td>
                  <div style={{ fontWeight: 500, maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {isReview ? (
                      <Link to={`/episodes/${ep.id}/review`} style={{ color: "var(--warning)" }}>
                        ★ {ep.title}
                      </Link>
                    ) : ep.title}
                  </div>
                  {ep.error_message && (
                    <div
                      title={ep.error_message}
                      style={{ fontSize: 11, color: "var(--danger)", marginTop: 2, maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                    >
                      {ep.error_message}
                    </div>
                  )}
                  {(ep.status === "transcribing" || ep.status === "classifying") && (
                    <EpisodeProgress episodeId={ep.id} status={ep.status} />
                  )}
                </td>
                {showPodcast && <td className="text-muted">{ep.podcast_id}</td>}
                <td className="text-muted" style={{ whiteSpace: "nowrap" }}>{fmtDate(ep.published_at)}</td>
                <td><StatusBadge status={ep.status} /></td>
                <td className="text-muted">
                  {ep.ad_time_removed_ms ? fmtMs(ep.ad_time_removed_ms) : "—"}
                </td>
                <td>
                  <div className="flex gap-8">
                    {isReview && (
                      <Link to={`/episodes/${ep.id}/review`} className="btn btn-ghost btn-sm">
                        Review
                      </Link>
                    )}
                    {!isReview && ep.transcript_word_count && (
                      <Link to={`/episodes/${ep.id}/review`} className="btn btn-ghost btn-sm">
                        Transcript
                      </Link>
                    )}
                    {isActive && (
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ color: "var(--danger)" }}
                        onClick={() => cancel(ep.id)}
                      >
                        Cancel
                      </button>
                    )}
                    {isTerminal && (
                      <button className="btn btn-ghost btn-sm" onClick={() => reprocess(ep.id)}>
                        Reprocess
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
