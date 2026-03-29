import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

function countBadge(counts, status, cls) {
  const n = counts?.[status] || 0;
  if (!n) return null;
  return <span className={`badge ${cls}`} style={{ fontSize: 11 }}>{n}</span>;
}

export default function PodcastList() {
  const [podcasts, setPodcasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function load() {
    api.get("/podcasts")
      .then((ps) => { setPodcasts(ps); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }

  useEffect(() => { load(); }, []);

  async function toggleEnabled(podcast) {
    try {
      const updated = await api.patch(`/podcasts/${podcast.id}`, { enabled: !podcast.enabled });
      setPodcasts((ps) => ps.map((p) => p.id === updated.id ? updated : p));
    } catch (e) {
      alert(e.message);
    }
  }

  async function deletePodcast(podcast) {
    if (!confirm(`Delete "${podcast.name}" and all its data?`)) return;
    try {
      await api.delete(`/podcasts/${podcast.id}`);
      setPodcasts((ps) => ps.filter((p) => p.id !== podcast.id));
    } catch (e) {
      alert(e.message);
    }
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>;
  if (error)   return <div className="alert alert-error">{error}</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-16">
        <span className="text-muted" style={{ fontSize: 13 }}>
          {podcasts.length} podcast{podcasts.length !== 1 ? "s" : ""}
        </span>
        <Link to="/podcasts/new" className="btn btn-primary">
          + Add Podcast
        </Link>
      </div>

      {podcasts.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: 32 }}>🎙</div>
          <p>No podcasts yet. <Link to="/podcasts/new">Add your first podcast</Link></p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Podcast</th>
                  <th>Status</th>
                  <th>Episodes</th>
                  <th>Last Checked</th>
                  <th>Enabled</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {podcasts.map((p) => {
                  const counts = p.episode_counts || {};
                  const lastChecked = p.last_checked_at
                    ? new Date(p.last_checked_at).toLocaleString(undefined, {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                      })
                    : "Never";

                  return (
                    <tr key={p.id}>
                      <td>
                        <Link
                          to={`/podcasts/${p.id}`}
                          style={{ fontWeight: 600, color: "var(--text)" }}
                        >
                          {p.name}
                        </Link>
                        <div className="text-dim" style={{ fontSize: 11, marginTop: 2 }}>
                          {p.feed_slug}
                        </div>
                      </td>
                      <td>
                        <div className="flex gap-8" style={{ flexWrap: "wrap" }}>
                          {countBadge(counts, "awaiting_review", "badge-warning")}
                          {countBadge(counts, "failed", "badge-danger")}
                          {countBadge(counts, "complete", "badge-success")}
                          {(counts.downloading || counts.transcribing || counts.classifying || counts.processing_audio)
                            ? <span className="badge badge-info" style={{ fontSize: 11 }}>processing</span>
                            : null}
                        </div>
                      </td>
                      <td>
                        <div className="text-muted" style={{ fontSize: 12 }}>
                          {Object.values(counts).reduce((a, b) => a + b, 0)} total
                          {counts.pending ? ` · ${counts.pending} pending` : ""}
                        </div>
                      </td>
                      <td className="text-muted" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                        {lastChecked}
                      </td>
                      <td>
                        <label className="toggle" title={p.enabled ? "Enabled — click to disable" : "Disabled — click to enable"}>
                          <input
                            type="checkbox"
                            checked={p.enabled}
                            onChange={() => toggleEnabled(p)}
                          />
                          <span className="toggle-slider" />
                        </label>
                      </td>
                      <td>
                        <div className="flex gap-8">
                          <Link to={`/podcasts/${p.id}`} className="btn btn-ghost btn-sm">
                            Edit
                          </Link>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ color: "var(--danger)" }}
                            onClick={() => deletePodcast(p)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
