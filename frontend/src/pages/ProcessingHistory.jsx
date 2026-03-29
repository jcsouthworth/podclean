import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const JOB_TYPE_LABELS = {
  full: "Full",
  retranscribe: "Retranscribe",
  reclassify: "Reclassify",
  reaudio: "Reaudio",
};

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function fmtDuration(secs) {
  if (!secs) return "—";
  if (secs < 60) return `${secs}s`;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  if (m < 60) return s ? `${m}m ${s}s` : `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export default function ProcessingHistory() {
  const [history, setHistory] = useState(null);
  const [podcasts, setPodcasts] = useState([]);
  const [podcastId, setPodcastId] = useState("");
  const [jobType, setJobType] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState(null);

  function load(p = page) {
    let path = `/history?page=${p}&per_page=50`;
    if (podcastId) path += `&podcast_id=${podcastId}`;
    if (jobType) path += `&job_type=${jobType}`;
    api.get(path)
      .then(setHistory)
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    api.get("/podcasts").then(setPodcasts).catch(() => {});
  }, []);

  useEffect(() => {
    load(1);
    setPage(1);
  }, [podcastId, jobType]);

  useEffect(() => {
    if (page > 1) load(page);
  }, [page]);

  const perPage = 50;
  const totalPages = history ? Math.ceil(history.total / perPage) : 1;

  return (
    <div>
      {/* Filters */}
      <div className="flex gap-12 mb-16" style={{ flexWrap: "wrap" }}>
        <select
          value={podcastId}
          onChange={(e) => setPodcastId(e.target.value)}
          style={{ width: "auto", minWidth: 180 }}
        >
          <option value="">All Podcasts</option>
          {podcasts.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select
          value={jobType}
          onChange={(e) => setJobType(e.target.value)}
          style={{ width: "auto", minWidth: 160 }}
        >
          <option value="">All Job Types</option>
          <option value="full">Full</option>
          <option value="retranscribe">Retranscribe</option>
          <option value="reclassify">Reclassify</option>
          <option value="reaudio">Reaudio</option>
        </select>
        {history && (
          <span className="text-dim" style={{ fontSize: 13, alignSelf: "center" }}>
            {history.total.toLocaleString()} job{history.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {error && <div className="alert alert-error mb-16">{error}</div>}

      {!history ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : history.items.length === 0 ? (
        <div className="empty-state">
          <div>No processing history yet.</div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Episode</th>
                  <th>Job Type</th>
                  <th>Triggered</th>
                  <th>Device</th>
                  <th>Whisper</th>
                  <th>LLM</th>
                  <th>Duration</th>
                  <th>Completed</th>
                </tr>
              </thead>
              <tbody>
                {history.items.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <div style={{ fontWeight: 500, maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {job.episode_title || <span className="text-dim">Unknown</span>}
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-muted" style={{ fontSize: 11 }}>
                        {JOB_TYPE_LABELS[job.job_type] || job.job_type}
                      </span>
                    </td>
                    <td className="text-muted" style={{ fontSize: 12, textTransform: "capitalize" }}>
                      {job.triggered_by}
                    </td>
                    <td>
                      {job.device_used ? (
                        <span className="badge badge-muted" style={{ fontSize: 11 }}>
                          {job.device_used}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="text-muted" style={{ fontSize: 12 }}>
                      {job.whisper_model_used || "—"}
                    </td>
                    <td className="text-muted" style={{ fontSize: 12, maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {job.llm_model_used || "—"}
                    </td>
                    <td className="text-muted" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                      {fmtDuration(job.duration_seconds)}
                    </td>
                    <td className="text-muted" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                      {fmtDate(job.completed_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-ghost btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Prev
              </button>
              <span>Page {page} of {totalPages}</span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
