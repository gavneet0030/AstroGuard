"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import { useRouter } from "next/navigation";

import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  AudioWaveform,
  BrainCircuit,
  Command,
  CornerDownLeft,
  LayoutDashboard,
  Search,
  Settings,
  Siren,
  X
} from "lucide-react";

type CommandItem = {
  id: string;
  label: string;
  description: string;
  href: string;
  section: string;
  keywords: string[];
  icon: typeof LayoutDashboard;
};

const COMMANDS: CommandItem[] = [
  {
    id: "overview",
    label: "Mission Control",
    description: "Return to the main command center",
    href: "/",
    section: "OPERATIONS",
    keywords: ["home", "dashboard", "overview", "mission"],
    icon: LayoutDashboard
  },
  {
    id: "telemetry",
    label: "Telemetry Laboratory",
    description: "Inspect the telemetry workspace",
    href: "/telemetry",
    section: "OPERATIONS",
    keywords: ["signals", "telemetry", "data", "waveform"],
    icon: AudioWaveform
  },
  {
    id: "anomalies",
    label: "Anomaly Intelligence",
    description: "Open anomaly analysis workspace",
    href: "/anomalies",
    section: "INTELLIGENCE",
    keywords: ["alerts", "anomalies", "detection", "risk"],
    icon: AlertTriangle
  },
  {
    id: "investigations",
    label: "Mission Investigations",
    description: "Open investigation workspace",
    href: "/investigations",
    section: "INTELLIGENCE",
    keywords: ["cases", "investigation", "incidents"],
    icon: Siren
  },
  {
    id: "models",
    label: "AI Model Observatory",
    description: "Inspect the model workspace",
    href: "/models",
    section: "INTELLIGENCE",
    keywords: ["models", "machine learning", "ai", "ml"],
    icon: BrainCircuit
  },
  {
    id: "settings",
    label: "System Configuration",
    description: "Open platform configuration",
    href: "/settings",
    section: "PLATFORM",
    keywords: ["settings", "configuration", "system"],
    icon: Settings
  }
];

type Props = {
  open: boolean;
  onClose: () => void;
};

export function CommandPalette({ open, onClose }: Props) {
  const router = useRouter();

  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const filteredCommands = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      return COMMANDS;
    }

    return COMMANDS.filter((item) => {
      const searchable = [
        item.label,
        item.description,
        item.section,
        ...item.keywords
      ].join(" ").toLowerCase();

      return searchable.includes(normalized);
    });
  }, [query]);

  const close = useCallback(() => {
    setQuery("");
    setSelectedIndex(0);
    onClose();
  }, [onClose]);

  const execute = useCallback((href: string) => {
    close();
    router.push(href);
  }, [close, router]);

  useEffect(() => {
    if (!open) {
      return;
    }

    setQuery("");
    setSelectedIndex(0);

    const frame = window.requestAnimationFrame(() => {
      inputRef.current?.focus();
    });

    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();

        setSelectedIndex((current) => {
          if (filteredCommands.length === 0) {
            return 0;
          }

          return (current + 1) % filteredCommands.length;
        });

        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();

        setSelectedIndex((current) => {
          if (filteredCommands.length === 0) {
            return 0;
          }

          return (
            current - 1 + filteredCommands.length
          ) % filteredCommands.length;
        });

        return;
      }

      if (event.key === "Enter") {
        event.preventDefault();

        const selected = filteredCommands[selectedIndex];

        if (selected) {
          execute(selected.href);
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, close, execute, filteredCommands, selectedIndex]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="command-overlay"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          close();
        }
      }}
    >
      <section
        ref={dialogRef}
        className="command-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="command-title"
        aria-describedby="command-description"
      >
        <h2 id="command-title" className="sr-only">
          Mission navigation
        </h2>

        <p id="command-description" className="sr-only">
          Search and navigate AstroGuard workspaces.
        </p>

        <div className="command-search">
          <Search size={19} aria-hidden="true" />

          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search mission workspaces..."
            aria-label="Search mission workspaces"
            aria-controls="command-results"
            autoComplete="off"
            spellCheck={false}
          />

          <button
            type="button"
            className="command-close"
            onClick={close}
            aria-label="Close command palette"
          >
            <X size={17} />
          </button>
        </div>

        <div
          id="command-results"
          className="command-results"
          role="listbox"
          aria-label="Navigation results"
        >
          {filteredCommands.length === 0 ? (
            <div className="command-empty">
              <Search size={23} />
              <strong>No matching workspace</strong>
              <span>Try another search term.</span>
            </div>
          ) : (
            filteredCommands.map((item, index) => {
              const Icon = item.icon;
              const active = index === selectedIndex;

              return (
                <button
                  key={item.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={`command-item ${active ? "selected" : ""}`}
                  onMouseEnter={() => setSelectedIndex(index)}
                  onClick={() => execute(item.href)}
                >
                  <span className="command-item-icon">
                    <Icon size={17} />
                  </span>

                  <span className="command-item-copy">
                    <strong>{item.label}</strong>
                    <small>{item.description}</small>
                  </span>

                  <span className="command-item-section">
                    {item.section}
                  </span>

                  {active ? (
                    <CornerDownLeft
                      size={15}
                      className="command-enter-icon"
                    />
                  ) : null}
                </button>
              );
            })
          )}
        </div>

        <footer className="command-footer">
          <span>
            <kbd><ArrowUp size={11} /></kbd>
            <kbd><ArrowDown size={11} /></kbd>
            Navigate
          </span>

          <span>
            <kbd>ENTER</kbd>
            Open
          </span>

          <span>
            <kbd>ESC</kbd>
            Close
          </span>
        </footer>
      </section>
    </div>
  );
}

export function CommandShortcut() {
  return (
    <span className="command-shortcut" aria-hidden="true">
      <Command size={11} />
      <span>K</span>
    </span>
  );
}
