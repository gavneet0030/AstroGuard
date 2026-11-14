import type { ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({
  children
}: {
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-column">
        <Topbar />
        <main className="main-content">{children}</main>
        <footer className="app-footer">
          <span>ASTROGUARD MISSION CONTROL</span>
          <span>Platform interface v0.6.0</span>
        </footer>
      </div>
    </div>
  );
}