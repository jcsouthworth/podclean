import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import GpuStatusWidget from "../components/GpuStatusWidget";
import TimeSavedStat from "../components/TimeSavedStat";
import StatusBadge from "../components/StatusBadge";

const ACTIVE_STATUSES = ["downloading", "transcribing", "classifying", "processing_audio"];

function PodcastCard({ podcast }) {
  const counts = podcast.episode_counts || {};
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const reviewing = counts.awaiting_review || 0;
  const inFlight = ACTIVE_STATUSES.reduce((a, s) => a + (counts[s] || 0), 0);
  const failed = counts.failed || 0;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-8">
        <Link
          to={`/podcasts/${podcast.id}`}
          style={{ fontWeight: 600, fontSize: 15, color: "var(--text)" }}
        >
          {podcast.name}
        </Link>
        {!podcast.enabled && (
          <span className="badge badge-muted" style={{ fontSize: 11 }}>disabled</span>
        )}
      </div>

      <div className="flex gap-16" style={{ flexWrap: "wrap", marginBottom: 12 }}>
        <div>
          <div className="text-dim" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5 }}>Episodes</div>
          <div style={{ fontWeight: 600, marginTop: 2 }}>{total}</div>
        </div>
        <div>
          <div className="text-dim" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5 }}>Complete</div>
          <div style={{ fontWeight: 600, color: "var(--success)", marginTop: 2 }}>{counts.complete || 0}</div>
        </div>
        {reviewing > 0 && (
          <div>
            <div className="text-dim" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5 }}>Review</div>
            <div style={{ fontWeight: 600, color: "var(--warning)", marginTop: 2 }}>{reviewing}</div>
          </div>
        )}
        {failed > 0 && (
          <div>
            <div className="text-dim" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5 }}>Failed</div>
            <div style={{ fontWeight: 600, color: "var(--danger)", marginTop: 2 }}>{failed}</div>
          </div>
        )}
      </div>

      {inFlight > 0 && (
        <div className="flex items-center gap-8" style={{ fontSize: 12, color: "var(--info)" }}>
          <div className="spinner spinner-sm" />
          {inFlight} episode{inFlight !== 1 ? "s" : ""} processing
        </div>
      )}

      {reviewing > 0 && (
        <div style={{ marginTop: 6 }}>
          <Link to={`/podcasts/${podcast.id}`} style={{ fontSize: 12, color: "var(--warning)" }}>
            ★ {reviewing} episode{reviewing !== 1 ? "s" : ""} awaiting review →
          </Link>
        </div>
      )}
    </div>
  );
}

function QueueStatus({ episodes }) {
  const active = episodes.filter((e) => ACTIVE_STATUSES.includes(e.status));
  const pending = episodes.filter((e) => e.status === "pending");

  if (active.length === 0 && pending.length === 0) {
    return (
      <div className="card">
        <div className="card-title">Processing Queue</div>
        <div className="text-dim" style={{ fontSize: 13 }}>Queue is empty — no episodes processing or pending.</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">Processing Queue</div>
      {active.length > 0 && (
        <>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8 }}>
            IN PROGRESS
          </div>
          {active.map((ep) => (
            <div
              key={ep.id}
              className="flex items-center justify-between"
              style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}
            >
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{ep.title}</div>
              </div>
              <StatusBadge status={ep.status} />
            </div>
          ))}
        </>
      )}
      {pending.length > 0 && (
        <>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", margin: "12px 0 8px" }}>
            PENDING ({pending.length})
          </div>
          {pending.slice(0, 5).map((ep) => (
            <div
              key={ep.id}
              className="flex items-center justify-between"
              style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}
            >
              <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{ep.title}</div>
            </div>
          ))}
          {pending.length > 5 && (
            <div className="text-dim" style={{ fontSize: 12, paddingTop: 8 }}>
              +{pending.length - 5} more
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [podcasts, setPodcasts] = useState([]);
  const [episodes, setEpisodes] = useState([]);
  const [polling, setPolling] = useState(false);
  const [pollMsg, setPollMsg] = useState(null);
  const [loading, setLoading] = useState(true);

  function load() {
    Promise.all([
      api.get("/podcasts"),
      api.get("/episodes?per_page=100"),
    ]).then(([ps, eps]) => {
      setPodcasts(ps);
      setEpisodes(eps);
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  async function triggerPoll() {
    setPolling(true);
    setPollMsg(null);
    try {
      await api.post("/podcasts/poll");
      setPollMsg("Feed poll queued.");
      setTimeout(() => setPollMsg(null), 4000);
    } catch (e) {
      setPollMsg(`Error: ${e.message}`);
    } finally {
      setPolling(false);
    }
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>;

  const reviewCount = episodes.filter((e) => e.status === "awaiting_review").length;

  return (
    <div>
      {/* Top row: stats + actions */}
      <div className="flex items-center justify-between mb-16" style={{ flexWrap: "wrap", gap: 12 }}>
        <div className="card" style={{ padding: "16px 24px", flex: "0 0 auto" }}>
          <TimeSavedStat label="Total Ad Time Removed" />
        </div>
        <div className="flex gap-12 items-center">
          {pollMsg && <span style={{ fontSize: 13, color: "var(--text-muted)" }}>{pollMsg}</span>}
          <button className="btn btn-ghost" onClick={triggerPoll} disabled={polling}>
            {polling ? "Polling…" : "↻ Poll Feeds Now"}
          </button>
          <Link to="/podcasts/new" className="btn btn-primary">
            + Add Podcast
          </Link>
        </div>
      </div>

      {reviewCount > 0 && (
        <div className="alert alert-warning mb-16">
          ★ {reviewCount} episode{reviewCount !== 1 ? "s" : ""} awaiting review
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 20, alignItems: "start" }}>
        <div>
          {/* GPU widget */}
          <GpuStatusWidget />

          {/* Podcast cards */}
          {podcasts.length === 0 ? (
            <div className="empty-state card">
              <div style={{ fontSize: 32 }}>🎙</div>
              <p>No podcasts yet. <Link to="/podcasts/new">Add your first podcast</Link></p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
              {podcasts.map((p) => (
                <PodcastCard key={p.id} podcast={p} />
              ))}
            </div>
          )}
        </div>

        {/* Right sidebar: queue */}
        <div>
          <QueueStatus episodes={episodes} />
        </div>
      </div>
    </div>
  );
}
