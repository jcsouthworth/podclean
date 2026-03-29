import { useState, useRef, useEffect } from "react";

function msToHMS(ms) {
  const totalSecs = Math.floor(ms / 1000);
  return {
    h: Math.floor(totalSecs / 3600),
    m: Math.floor((totalSecs % 3600) / 60),
    s: totalSecs % 60,
  };
}

function hmsToMs(h, m, s) {
  return (h * 3600 + m * 60 + s) * 1000;
}

function msToLabel(ms) {
  const { h, m, s } = msToHMS(ms);
  return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

function segmentsOverlap(segStart, segEnd, adStart, adEnd) {
  return segStart < adEnd && segEnd > adStart;
}

function TimeInput({ ms, onChange }) {
  const { h, m, s } = msToHMS(ms);
  function update(nh, nm, ns) {
    onChange(hmsToMs(
      Math.max(0, nh),
      Math.min(59, Math.max(0, nm)),
      Math.min(59, Math.max(0, ns)),
    ));
  }
  const inp = { type: "number", style: { width: 52, textAlign: "center", padding: "4px 6px" } };
  return (
    <div className="flex items-center gap-8" style={{ fontVariantNumeric: "tabular-nums" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 10, color: "var(--text-dim)", marginBottom: 2 }}>HH</div>
        <input {...inp} min="0" value={h} onChange={(e) => update(+e.target.value, m, s)} />
      </div>
      <span style={{ color: "var(--text-dim)", marginTop: 14 }}>:</span>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 10, color: "var(--text-dim)", marginBottom: 2 }}>MM</div>
        <input {...inp} min="0" max="59" value={m} onChange={(e) => update(h, +e.target.value, s)} />
      </div>
      <span style={{ color: "var(--text-dim)", marginTop: 14 }}>:</span>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 10, color: "var(--text-dim)", marginBottom: 2 }}>SS</div>
        <input {...inp} min="0" max="59" value={s} onChange={(e) => update(h, m, +e.target.value)} />
      </div>
    </div>
  );
}

export default function TranscriptSegmentEditor({ transcript, segments, onChange, readOnly = false }) {
  const [threshold, setThreshold] = useState(0);
  const [selected, setSelected] = useState(null);
  // clickMode: null | 'start' | 'end'
  const [clickMode, setClickMode] = useState(null);
  const scrollRef = useRef(null);

  const visible = segments.filter((s) => s.confidence >= threshold);

  function updateSegmentMs(idx, field, ms) {
    if (readOnly) return;
    onChange(segments.map((s, i) => i === idx ? { ...s, [field]: ms } : s));
  }

  function deleteSegment(idx) {
    if (readOnly) return;
    onChange(segments.filter((_, i) => i !== idx));
    setSelected(null);
    setClickMode(null);
  }

  function addSegment() {
    if (readOnly) return;
    const last = segments[segments.length - 1];
    const start = last ? last.end_ms + 1000 : 0;
    onChange([...segments, { start_ms: start, end_ms: start + 30000, confidence: 1.0, reason: "Manual" }]);
    setSelected(segments.length);
    setClickMode("start");
  }

  function handleTranscriptClick(startMs) {
    if (readOnly || selected === null || !clickMode) return;
    const seg = segments[selected];
    if (clickMode === "start") {
      const newEnd = startMs >= seg.end_ms ? startMs + 30000 : seg.end_ms;
      onChange(segments.map((s, i) => i === selected ? { ...s, start_ms: startMs, end_ms: newEnd } : s));
      setClickMode("end"); // advance to set end next
    } else {
      if (startMs <= seg.start_ms) return; // end must be after start
      onChange(segments.map((s, i) => i === selected ? { ...s, end_ms: startMs } : s));
      setClickMode(null);
    }
  }

  // Scroll transcript to selected segment's start
  useEffect(() => {
    if (selected !== null && scrollRef.current) {
      const seg = segments[selected];
      if (!seg) return;
      const nearest = [...scrollRef.current.querySelectorAll("[data-ms]")]
        .map((el) => ({ el, diff: Math.abs(parseInt(el.dataset.ms) - seg.start_ms) }))
        .sort((a, b) => a.diff - b.diff)[0];
      if (nearest) nearest.el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [selected]);

  const isClickActive = selected !== null && clickMode !== null;
  const cursorStyle = isClickActive ? "pointer" : "default";

  return (
    <div className="transcript-layout">
      {/* Left: transcript */}
      <div
        className="transcript-scroll"
        ref={scrollRef}
        style={{ cursor: cursorStyle }}
        title={
          isClickActive
            ? clickMode === "start"
              ? "Click a line to set the ad start time"
              : "Click a line to set the ad end time"
            : undefined
        }
      >
        {isClickActive && (
          <div style={{
            position: "sticky", top: 0, zIndex: 1,
            background: clickMode === "start" ? "rgba(99,102,241,0.15)" : "rgba(245,158,11,0.15)",
            border: `1px solid ${clickMode === "start" ? "var(--accent)" : "var(--warning)"}`,
            borderRadius: 6, padding: "6px 12px", marginBottom: 10,
            fontSize: 12, fontWeight: 500,
            color: clickMode === "start" ? "var(--accent)" : "var(--warning)",
          }}>
            {clickMode === "start"
              ? "▶ Click a line to set the ad START time"
              : "⏹ Click a line to set the ad END time"}
            <button
              className="btn btn-ghost btn-sm"
              style={{ marginLeft: 12, fontSize: 11 }}
              onClick={() => setClickMode(null)}
            >
              Cancel
            </button>
          </div>
        )}

        {transcript.length === 0 && (
          <div className="text-dim">No transcript content.</div>
        )}

        {transcript.map((seg, i) => {
          const startMs = Math.round(seg.start * 1000);
          const endMs = Math.round(seg.end * 1000);
          const isAd = visible.some((a) => segmentsOverlap(startMs, endMs, a.start_ms, a.end_ms));
          const isSelectedAd = selected !== null && segments[selected] &&
            segmentsOverlap(startMs, endMs, segments[selected].start_ms, segments[selected].end_ms);

          return (
            <div
              key={i}
              data-ms={startMs}
              className={`segment-block${isAd ? " is-ad" : ""}`}
              style={{
                outline: isSelectedAd ? "1px solid var(--accent)" : undefined,
                borderRadius: isSelectedAd ? 3 : undefined,
              }}
              onClick={() => handleTranscriptClick(startMs)}
            >
              <span className="timestamp">[{msToLabel(startMs)}]</span>
              {seg.text}
            </div>
          );
        })}
      </div>

      {/* Right: segments panel */}
      <div className="segments-panel">
        <div className="segments-panel-header">
          <div className="flex items-center justify-between">
            <span>Ad Segments ({segments.length})</span>
            {!readOnly && <button className="btn btn-ghost btn-sm" onClick={addSegment}>+ Add</button>}
          </div>
          <div style={{ marginTop: 10 }}>
            <label style={{ fontSize: 11, color: "var(--text-dim)", display: "block", marginBottom: 4 }}>
              Min confidence: {(threshold * 100).toFixed(0)}%
            </label>
            <input
              type="range" min="0" max="1" step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              disabled={readOnly}
            />
          </div>
        </div>

        <div className="segments-panel-body">
          {segments.length === 0 && (
            <div className="text-dim" style={{ fontSize: 12, textAlign: "center", padding: 20 }}>
              No ad segments detected.
            </div>
          )}

          {segments.map((seg, idx) => {
            const hidden = seg.confidence < threshold;
            const isSelected = selected === idx;

            return (
              <div
                key={idx}
                className={`segment-item${isSelected ? " selected" : ""}`}
                style={{ opacity: hidden ? 0.4 : 1 }}
                onClick={() => {
                  setSelected(isSelected ? null : idx);
                  setClickMode(null);
                }}
              >
                <div className="flex items-center justify-between mb-4">
                  <span style={{ fontSize: 12, fontWeight: 500 }}>
                    {msToLabel(seg.start_ms)} → {msToLabel(seg.end_ms)}
                  </span>
                  {!readOnly && (
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ padding: "2px 6px", color: "var(--danger)" }}
                      onClick={(e) => { e.stopPropagation(); deleteSegment(idx); }}
                    >
                      ✕
                    </button>
                  )}
                </div>

                <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 6 }}>
                  {seg.reason}
                </div>

                <div className="flex items-center gap-8" style={{ marginBottom: isSelected ? 10 : 0 }}>
                  <span style={{ fontSize: 11, color: "var(--text-dim)" }}>
                    {(seg.confidence * 100).toFixed(0)}% confidence
                  </span>
                  <div className="confidence-bar" style={{ flex: 1 }}>
                    <div className="confidence-bar-fill" style={{ width: `${seg.confidence * 100}%` }} />
                  </div>
                </div>

                {isSelected && !readOnly && (
                  <div onClick={(e) => e.stopPropagation()}>
                    {/* Click-to-set buttons */}
                    <div className="flex gap-8 mb-8">
                      <button
                        className="btn btn-sm"
                        style={{
                          flex: 1,
                          background: clickMode === "start" ? "var(--accent)" : "var(--bg-surface)",
                          color: clickMode === "start" ? "#fff" : "var(--text-muted)",
                          border: "1px solid var(--border)",
                        }}
                        onClick={() => setClickMode(clickMode === "start" ? null : "start")}
                      >
                        ▶ Set Start from transcript
                      </button>
                      <button
                        className="btn btn-sm"
                        style={{
                          flex: 1,
                          background: clickMode === "end" ? "var(--warning)" : "var(--bg-surface)",
                          color: clickMode === "end" ? "#000" : "var(--text-muted)",
                          border: "1px solid var(--border)",
                        }}
                        onClick={() => setClickMode(clickMode === "end" ? null : "end")}
                      >
                        ⏹ Set End from transcript
                      </button>
                    </div>

                    {/* Time inputs */}
                    <div style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 4 }}>Start</div>
                      <TimeInput
                        ms={seg.start_ms}
                        onChange={(ms) => updateSegmentMs(idx, "start_ms", ms)}
                      />
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 4 }}>End</div>
                      <TimeInput
                        ms={seg.end_ms}
                        onChange={(ms) => updateSegmentMs(idx, "end_ms", ms)}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
