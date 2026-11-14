"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  Activity,
  AlertTriangle,
  AudioWaveform,
  BrainCircuit,
  CircleHelp,
  Command,
  LayoutDashboard,
  Menu,
  Settings,
  ShieldCheck,
  Siren,
  X
} from "lucide-react";

import type { ReactNode } from "react";

import {
  CommandPalette,
  CommandShortcut
} from "@/components/command-palette";

const navigation = [
  {
    label: "Mission control",
    href: "/",
    icon: LayoutDashboard,
    section: "OPERATIONS"
  },
  {
    label: "Telemetry laboratory",
    href: "/telemetry",
    icon: AudioWaveform,
    section: "OPERATIONS"
  },
  {
    label: "Anomaly intelligence",
    href: "/anomalies",
    icon: AlertTriangle,
    section: "INTELLIGENCE"
  },
  {
    label: "Investigations",
    href: "/investigations",
    icon: Siren,
    section: "INTELLIGENCE"
  },
  {
    label: "Model observatory",
    href: "/models",
    icon: BrainCircuit,
    section: "INTELLIGENCE"
  },
  {
    label: "System configuration",
    href: "/settings",
    icon: Settings,
    section: "PLATFORM"
  }
];

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg
        viewBox="0 0 64 64"
        width="37"
        height="37"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M32 4.5 54.5 17.4v29.2L32 59.5 9.5 46.6V17.4L32 4.5Z"
          stroke="#70DCE7"
          strokeWidth="1.6"
          opacity=".8"
        />

        <path
          d="M32 12 48 21.2v21.6L32 52 16 42.8V21.2L32 12Z"
          fill="#102B38"
          stroke="#4ABBD0"
          strokeWidth="1.2"
        />

        <path
          d="m20 40 12-25 12 25h-5.8l-2.2-5H28l-2.2 5H20Z"
          fill="#83E5EA"
        />

        <path
          d="M29.8 30.8h4.4L32 25.7l-2.2 5.1Z"
          fill="#0B1720"
        />

        <circle cx="48.5" cy="13" r="2.2" fill="#E6C77A" />

        <path
          d="M7 32h7M50 32h7"
          stroke="#69D9E5"
          strokeLinecap="round"
        />
      </svg>
    </span>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const openPalette = useCallback(() => {
    setMobileOpen(false);
    setPaletteOpen(true);
  }, []);

  const closePalette = useCallback(() => {
    setPaletteOpen(false);
  }, []);

  useEffect(() => {
    function handleGlobalShortcut(event: KeyboardEvent) {
      const isShortcut =
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k";

      if (isShortcut) {
        event.preventDefault();
        setPaletteOpen((current) => !current);
      }
    }

    document.addEventListener("keydown", handleGlobalShortcut);

    return () => {
      document.removeEventListener("keydown", handleGlobalShortcut);
    };
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const current = navigation.find((item) => {
    if (item.href === "/") {
      return pathname === "/";
    }

    return pathname === item.href || pathname.startsWith(`${item.href}/`);
  });

  const sections = Array.from(
    new Set(navigation.map((item) => item.section))
  );

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <aside className={`sidebar ${mobileOpen ? "sidebar-mobile-open" : ""}`}>
        <Link
          href="/"
          className="brand"
          aria-label="AstroGuard mission control home"
        >
          <BrandMark />

          <span className="brand-copy">
            <strong>ASTROGUARD</strong>
            <small>MISSION INTELLIGENCE</small>
          </span>
        </Link>

        <div className="workspace-label">
          FLIGHT OPERATIONS
        </div>

        <nav className="nav-list" aria-label="Primary navigation">
          {sections.map((section) => (
            <div className="nav-section" key={section}>
              <div className="nav-section-label">
                {section}
              </div>

              {navigation
                .filter((item) => item.section === section)
                .map((item) => {
                  const Icon = item.icon;

                  const active =
                    item.href === "/"
                      ? pathname === "/"
                      : pathname === item.href ||
                        pathname.startsWith(`${item.href}/`);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`nav-link ${active ? "active" : ""}`}
                      aria-current={active ? "page" : undefined}
                    >
                      <Icon size={17} strokeWidth={1.8} />

                      <span>{item.label}</span>

                      {active ? (
                        <span className="nav-active-dot" />
                      ) : null}
                    </Link>
                  );
                })}
            </div>
          ))}
        </nav>

        <div className="sidebar-spacer" />

        <button
          type="button"
          className="sidebar-search-trigger"
          onClick={openPalette}
        >
          <SearchIcon />
          <span>Quick navigation</span>
          <kbd>CTRL K</kbd>
        </button>

        <div className="sidebar-status">
          <span className="status-orbit">
            <Activity size={14} />
          </span>

          <div>
            <strong>Local control plane</strong>
            <small>Backend health monitored</small>
          </div>

          <span
            className="status-led"
            aria-label="Backend status is shown in health panel"
          />
        </div>

        <div className="sidebar-footer">
          <CircleHelp size={14} />
          Research prototype · v0.6
        </div>
      </aside>

      {mobileOpen ? (
        <button
          type="button"
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <div className="main-column">
        <header className="topbar">
          <button
            type="button"
            className="mobile-menu-button"
            aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((current) => !current)}
          >
            {mobileOpen ? <X size={19} /> : <Menu size={19} />}
          </button>

          <div className="breadcrumb">
            <Command size={14} />
            <span>ASTROGUARD</span>
            <b>/</b>
            <span className="breadcrumb-current">
              {current?.label ?? "Mission control"}
            </span>
          </div>

          <div className="topbar-right">
            <div className="environment-pill">
              <i />
              LOCAL ENVIRONMENT
            </div>

            <button
              type="button"
              className="topbar-search"
              onClick={openPalette}
              aria-label="Open command palette"
            >
              <span>Search workspace</span>
              <CommandShortcut />
            </button>

            <div className="operator-chip">
              <span className="operator-glyph">
                <ShieldCheck size={15} />
              </span>
              <span>Operator</span>
            </div>
          </div>
        </header>

        <main
          id="main-content"
          className="page-content"
          tabIndex={-1}
        >
          {children}
        </main>

        <footer className="app-footer">
          <span>ASTROGUARD · RESEARCH PROTOTYPE</span>
          <span>
            Not affiliated with NASA · Data status is shown explicitly
          </span>
        </footer>
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={closePalette}
      />
    </div>
  );
}

function SearchIcon() {
  return (
    <span className="sidebar-search-icon" aria-hidden="true">
      <svg
        width="15"
        height="15"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </svg>
    </span>
  );
}
