import { useState, useEffect } from "react";
import { api } from "../api";

export default function TimeSavedStat({ podcastId, label }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    const path = podcastId ? `/podcasts/${podcastId}/stats` : "/stats/time-saved";
    api.get(path).then(setData).catch(() => {});
  }, [podcastId]);

  if (!data) return null;

  return (
    <div>
      <div className="stat-big">{data.formatted || "0m"}</div>
      <div className="stat-label">{label || "Total Ad Time Removed"}</div>
    </div>
  );
}
