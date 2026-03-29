import { useState } from "react";
import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", icon: "⊞", exact: true },
  { to: "/podcasts", label: "Podcasts", icon: "◎" },
  { to: "/history", label: "History", icon: "⧗" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

function ThemeToggle() {
  const [theme, setTheme] = useState(
    () => document.documentElement.getAttribute("data-theme") || "dark"
  );

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    setTheme(next);
  }

  return (
    <button
      className="btn btn-ghost btn-sm"
      onClick={toggle}
      title="Toggle theme"
      style={{ fontSize: 16, padding: "4px 8px" }}
    >
      {theme === "dark" ? "☀" : "☽"}
    </button>
  );
}

export default function Layout({ title, children }) {
  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="sidebar-brand">
          Pod<span>Clean</span>
        </div>
        <div className="sidebar-nav">
          {NAV.map(({ to, label, icon, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
            >
              <span className="nav-icon">{icon}</span>
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="main-area">
        <div className="top-bar">
          <h1>{title}</h1>
          <ThemeToggle />
        </div>
        <div className="page-content">{children}</div>
      </div>
    </div>
  );
}
