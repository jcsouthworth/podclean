const STATUS_CONFIG = {
  pending:          { cls: "badge-muted",   label: "Pending" },
  downloading:      { cls: "badge-info",    label: "Downloading" },
  transcribing:     { cls: "badge-info",    label: "Transcribing" },
  classifying:      { cls: "badge-info",    label: "Classifying" },
  awaiting_review:  { cls: "badge-warning", label: "Awaiting Review" },
  processing_audio: { cls: "badge-info",    label: "Processing Audio" },
  complete:         { cls: "badge-success", label: "Complete" },
  failed:           { cls: "badge-danger",  label: "Failed" },
  skipped:          { cls: "badge-muted",   label: "Skipped" },
};

const ACTIVE = new Set(["downloading", "transcribing", "classifying", "processing_audio"]);

export default function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || { cls: "badge-muted", label: status };
  return (
    <span className={`badge ${cfg.cls}`}>
      {ACTIVE.has(status) && (
        <span className="spinner-sm" style={{ display: "inline-block" }} />
      )}
      {cfg.label}
    </span>
  );
}
