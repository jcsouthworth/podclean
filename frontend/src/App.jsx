import React from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import Layout from "./components/Layout";

const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const PodcastList = React.lazy(() => import("./pages/PodcastList"));
const PodcastDetail = React.lazy(() => import("./pages/PodcastDetail"));
const AddPodcast = React.lazy(() => import("./pages/AddPodcast"));
const TranscriptReview = React.lazy(() => import("./pages/TranscriptReview"));
const ProcessingHistory = React.lazy(() => import("./pages/ProcessingHistory"));
const Settings = React.lazy(() => import("./pages/Settings"));

const TITLES = {
  "/": "Dashboard",
  "/podcasts": "Podcasts",
  "/podcasts/new": "Add Podcast",
  "/history": "Processing History",
  "/settings": "Settings",
};

function AppRoutes() {
  const location = useLocation();
  const path = location.pathname;
  const title =
    TITLES[path] ||
    (path.startsWith("/podcasts/") && path.endsWith("/") === false && !path.includes("/review")
      ? "Podcast Detail"
      : path.includes("/review")
      ? "Transcript Review"
      : "PodClean");

  return (
    <Layout title={title}>
      <React.Suspense
        fallback={
          <div className="loading-center">
            <div className="spinner" />
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/podcasts" element={<PodcastList />} />
          <Route path="/podcasts/new" element={<AddPodcast />} />
          <Route path="/podcasts/:id" element={<PodcastDetail />} />
          <Route path="/episodes/:id/review" element={<TranscriptReview />} />
          <Route path="/history" element={<ProcessingHistory />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </React.Suspense>
    </Layout>
  );
}

export default function App() {
  return <AppRoutes />;
}
