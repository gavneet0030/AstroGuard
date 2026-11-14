import { Activity, AlertTriangle, BrainCircuit, LayoutDashboard, Radar, Search, type LucideIcon } from "lucide-react";

export interface AppNavigationItem {
  label: string;
  href: string;
  icon: LucideIcon;
  section: string;
  status?: "live" | "preview";
}

export const navigation: AppNavigationItem[] = [
  {
    label: "Overview",
    href: "/",
    icon: LayoutDashboard,
    section: "Workspace"
  },
  {
    label: "Telemetry",
    href: "/telemetry",
    icon: Activity,
    section: "Workspace",
    status: "preview"
  },
  {
    label: "Anomalies",
    href: "/anomalies",
    icon: AlertTriangle,
    section: "Intelligence",
    status: "preview"
  },
  {
    label: "Investigations",
    href: "/investigations",
    icon: Search,
    section: "Intelligence",
    status: "preview"
  },
  {
    label: "Model Observatory",
    href: "/models",
    icon: BrainCircuit,
    section: "Intelligence",
    status: "preview"
  },
  {
    label: "System Health",
    href: "/settings",
    icon: Radar,
    section: "Platform"
  }
];

export const productName = "ASTROGUARD";
export const productSubtitle = "Telemetry Intelligence Platform";
export const productVersion = "0.6.0";