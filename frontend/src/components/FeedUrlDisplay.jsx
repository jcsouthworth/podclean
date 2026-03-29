import { useState } from "react";

export default function FeedUrlDisplay({ url }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="flex items-center gap-8" style={{ flexWrap: "wrap" }}>
      <code
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "4px 10px",
          fontSize: 12.5,
          color: "var(--text-muted)",
          wordBreak: "break-all",
          flex: 1,
        }}
      >
        {url}
      </code>
      <button className="btn btn-ghost btn-sm" onClick={copy} style={{ flexShrink: 0 }}>
        {copied ? "✓ Copied" : "Copy"}
      </button>
    </div>
  );
}
