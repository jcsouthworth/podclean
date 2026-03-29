import { useState, useEffect } from "react";
import { api } from "../api";

function fmtElapsed(secs) {
  if (!secs) return null;
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

export default function EpisodeProgress({ episodeId, status }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    let id;
    function poll() {
      api.get(`/episodes/${episodeId}/progress`)
        .then(setProgress)
        .catch(() => {});
    }
    poll();
    id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, [episodeId]);

  if (!progress) return null;

  const { pct, elapsed } = progress;
  const isTranscribing = status === "transcribing";
  const isClassifying = status === "classifying";

  if (!isTranscribing && !isClassifying) return null;

  return (
    <div style={{ marginTop: 5 }}>
      <div style={{
        height: 3,
        background: "var(--border)",
        borderRadius: 2,
        overflow: "hidden",
        width: "100%",
      }}>
        {pct != null ? (
          <div style={{
            height: "100%",
            width: `${pct}%`,
            background: "var(--accent)",
            borderRadius: 2,
            transition: "width 1s linear",
          }} />
        ) : (
          // Indeterminate bar for classifying
          <div style={{
            height: "100%",
            width: "40%",
            background: "var(--accent)",
            borderRadius: 2,
            animation: "progress-slide 1.5s ease-in-out infinite",
          }} />
        )}
      </div>
      <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 3 }}>
        {isTranscribing && pct != null && `Transcribing… ${pct}%`}
        {isTranscribing && pct == null && "Transcribing…"}
        {isClassifying && "Classifying ads…"}
        {elapsed != null && ` (${fmtElapsed(elapsed)})`}
      </div>
    </div>
  );
}
