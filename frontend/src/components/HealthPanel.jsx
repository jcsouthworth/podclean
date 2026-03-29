import { useState, useEffect } from "react";
import { api } from "../api";

const SERVICE_LABELS = {
  database: "Database",
  redis: "Redis",
  celery_worker: "Celery Worker",
  ollama: "Ollama",
  gpu: "GPU",
};

function ServiceRow({ name, status }) {
  const [expanded, setExpanded] = useState(false);
  const label = SERVICE_LABELS[name] || name;
  const dotCls =
    status === "ok" ? "dot-green" : status === "degraded" ? "dot-amber" : "dot-red";

  return (
    <div
      className="flex items-center justify-between"
      style={{
        padding: "8px 0",
        borderBottom: "1px solid var(--border)",
        cursor: status !== "ok" ? "pointer" : "default",
      }}
      onClick={() => status !== "ok" && setExpanded((e) => !e)}
    >
      <div className="flex items-center gap-8">
        <div className={`dot ${dotCls}`} />
        <span style={{ fontSize: 13 }}>{label}</span>
      </div>
      <span
        style={{
          fontSize: 12,
          color:
            status === "ok"
              ? "var(--success)"
              : status === "degraded"
              ? "var(--warning)"
              : "var(--danger)",
        }}
      >
        {status}
      </span>
    </div>
  );
}

export default function HealthPanel() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    function fetch() {
      api
        .get("/health")
        .then((d) => { setHealth(d); setError(null); })
        .catch((e) => setError(e.message));
    }
    fetch();
    const id = setInterval(fetch, 30000);
    return () => clearInterval(id);
  }, []);

  if (error) {
    return (
      <div className="card">
        <div className="card-title">Service Health</div>
        <div className="alert alert-error">{error}</div>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="card">
        <div className="card-title">Service Health</div>
        <div className="text-dim" style={{ fontSize: 13 }}>Loading…</div>
      </div>
    );
  }

  const overallColor =
    health.status === "ok"
      ? "var(--success)"
      : health.status === "degraded"
      ? "var(--warning)"
      : "var(--danger)";

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-12">
        <div className="card-title" style={{ marginBottom: 0 }}>Service Health</div>
        <span style={{ fontSize: 12, color: overallColor, fontWeight: 600 }}>
          {health.status.toUpperCase()}
        </span>
      </div>
      {Object.entries(health.services).map(([name, status]) => (
        <ServiceRow key={name} name={name} status={status} />
      ))}
      <div className="text-dim" style={{ fontSize: 11, marginTop: 8 }}>
        v{health.version} — polled every 30s
      </div>
    </div>
  );
}
