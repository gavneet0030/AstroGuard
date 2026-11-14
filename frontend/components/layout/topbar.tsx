"use client";

import { Bell, ChevronRight, Search, ShieldCheck } from "lucide-react";
import { usePathname } from "next/navigation";
import { navigation } from "@/lib/navigation";

export function Topbar() {
  const pathname = usePathname();

  const current =
    navigation.find((item) => item.href === pathname) ??
    navigation.find(
      (item) =>
        item.href !== "/" &&
        pathname.startsWith(item.href)
    );

  return (
    <header className="topbar">
      <div className="breadcrumbs">
        <span className="breadcrumb-root">Workspace</span>
        <ChevronRight size={14} />
        <span className="breadcrumb-current">
          {current?.label ?? "Overview"}
        </span>
      </div>

      <div className="topbar-actions">
        <div className="environment-pill">
          <span className="environment-dot" />
          LOCAL ENVIRONMENT
        </div>

        <button
          type="button"
          className="icon-button search-button"
          aria-label="Search interface"
          title="Search"
        >
          <Search size={17} />
          <span>Search</span>
          <kbd>⌘ K</kbd>
        </button>

        <button
          type="button"
          className="icon-button"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell size={17} />
        </button>

        <div className="topbar-divider" />

        <div className="topbar-operator">
          <div className="operator-icon">
            <ShieldCheck size={16} />
          </div>
          <span>Operator</span>
        </div>
      </div>
    </header>
  );
}