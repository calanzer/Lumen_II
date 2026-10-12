import { useLiveQuery } from "dexie-react-hooks";
import type { ReactNode } from "react";
import { DataBanners, DataFileBar } from "./components/DataFile";
import { Toasts } from "./components/Toasts";
import { getSettings } from "./db/repo";
import { href, useRoute } from "./lib/router";
import { FirstRun } from "./pages/FirstRun";
import { SettingsPage } from "./pages/SettingsPage";

const NAV: { path: string; label: string }[] = [
  { path: "week", label: "This Week" },
  { path: "caseload", label: "Caseload" },
  { path: "staff", label: "Staff and Supervision" },
  { path: "deadlines", label: "Deadlines" },
  { path: "cancellations", label: "Cancellations" },
  { path: "reports", label: "Reports" },
  { path: "import", label: "Import" },
  { path: "settings", label: "Settings" },
];

function NotBuiltYet({ title }: { title: string }) {
  return (
    <>
      <div className="page-header">
        <h1>{title}</h1>
      </div>
      <div className="card">
        <p className="muted">This screen is not built yet.</p>
      </div>
    </>
  );
}

function Page({ path }: { path: string }): ReactNode {
  switch (path) {
    case "settings":
      return <SettingsPage />;
    default: {
      const item = NAV.find((n) => n.path === path) ?? NAV[0];
      return <NotBuiltYet title={item.label} />;
    }
  }
}

export function App() {
  const settings = useLiveQuery(() => getSettings(), []);
  const route = useRoute();

  if (!settings) return null;
  if (!settings.firstRunComplete) {
    return (
      <>
        <FirstRun />
        <Toasts />
      </>
    );
  }

  const path = route.path || "week";
  const active = path === "client" ? "caseload" : path;

  return (
    <div className="app">
      <a className="skip-link" href="#main-content" onClick={(e) => {
        e.preventDefault();
        document.getElementById("main-content")?.focus();
      }}>
        Skip to content
      </a>
      <nav className="sidebar" aria-label="Main">
        <div className="brand">Caseload Tracker</div>
        {NAV.map((n) => (
          <a key={n.path} className="nav-link" href={href(n.path)} aria-current={active === n.path ? "page" : undefined}>
            {n.label}
          </a>
        ))}
      </nav>
      <div className="main">
        <header className="topbar">
          <DataFileBar />
        </header>
        <DataBanners />
        <main id="main-content" className="content" tabIndex={-1}>
          <Page path={path} />
        </main>
      </div>
      <Toasts />
    </div>
  );
}
