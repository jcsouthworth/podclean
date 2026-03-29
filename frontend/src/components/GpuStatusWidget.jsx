import { useState, useEffect } from "react";
import { api } from "../api";

export default function GpuStatusWidget() {
  const [gpu, setGpu] = useState(null);

  useEffect(() => {
    function fetch() {
      api.get("/gpu/status").then(setGpu).catch(() => {});
    }
    fetch();
    const id = setInterval(fetch, 5000);
    return () => clearInterval(id);
  }, []);

  if (!gpu) return null;

  // Only show for auto or gpu_required
  if (gpu.device_mode === "cpu_only") return null;

  const dotCls = gpu.available
    ? gpu.actively_used
      ? "dot-green"
      : "dot-amber"
    : "dot-red";

  const dotTitle = gpu.available
    ? gpu.actively_used
      ? "GPU active"
      : "GPU idle"
    : "GPU not detected";

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="flex items-center justify-between mb-8">
        <span style={{ fontWeight: 600, fontSize: 13 }}>GPU Status</span>
        <div className="flex items-center gap-8">
          <div className={`dot ${dotCls}`} title={dotTitle} />
          <span className="text-dim" style={{ fontSize: 12 }}>{dotTitle}</span>
        </div>
      </div>

      {gpu.available ? (
        <>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>
            {gpu.gpu_name}
          </div>
          <div className="flex gap-16" style={{ flexWrap: "wrap" }}>
            <div>
              <div className="stat-label">VRAM</div>
              <div style={{ fontSize: 13, marginTop: 2 }}>
                {gpu.vram_used_mb.toLocaleString()} / {gpu.vram_total_mb.toLocaleString()} MB
              </div>
              <div
                style={{
                  height: 4,
                  background: "var(--border)",
                  borderRadius: 2,
                  marginTop: 4,
                  width: 120,
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(100, (gpu.vram_used_mb / gpu.vram_total_mb) * 100)}%`,
                    background: "var(--accent)",
                    borderRadius: 2,
                  }}
                />
              </div>
            </div>
            <div>
              <div className="stat-label">Utilization</div>
              <div style={{ fontSize: 13, marginTop: 2 }}>{gpu.utilization_pct}%</div>
            </div>
            <div>
              <div className="stat-label">Mode</div>
              <div style={{ fontSize: 13, marginTop: 2 }}>{gpu.device_mode}</div>
            </div>
          </div>
        </>
      ) : (
        <div className="text-dim" style={{ fontSize: 13 }}>
          No compatible GPU detected (device mode: {gpu.device_mode})
        </div>
      )}
    </div>
  );
}
