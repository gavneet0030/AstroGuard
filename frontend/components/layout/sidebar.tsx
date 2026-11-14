"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown, Command, LifeBuoy, ShieldCheck } from "lucide-react";
import { navigation, productName, productSubtitle } from "@/lib/navigation";

export function Sidebar() {
  const pathname = usePathname();

  const sections = Array.from(
    new Set(navigation.map((item) => item.section))
  );

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <ShieldCheck size={23} strokeWidth={1.8} />
        </div>
        <div className="brand-copy">
          <div className="brand-name">{productName}</div>
          <div className="brand-subtitle">{productSubtitle}</div>
        </div>
      </div>

      <div className="workspace-switcher">
        <div className="workspace-avatar">AG</div>
        <div className="workspace-copy">
          <strong>Primary Workspace</strong>
          <span>Local environment</span>
        </div>
        <ChevronDown size={15} />
      </div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {sections.map((section) => (
          <div className="nav-section" key={section}>
            <div className="nav-section-label">{section}</div>
            {navigation
              .filter((item) => item.section === section)
              .map((item) => {
                const active =
                  pathname === item.href ||
                  (item.href !== "/" &&
                    pathname.startsWith(item.href));

                const Icon = item.icon;

                return (
                  <Link
                    href={item.href}
                    key={item.href}
                    className={`nav-item ${active ? "active" : ""}`}
                    aria-current={active ? "page" : undefined}
                  >
                    <Icon size={17} />
                    <span>{item.label}</span>
                    {item.status === "live" ? (
                      <span className="nav-live">LIVE</span>
                    ) : null}
                    {item.status === "preview" ? (
                      <span className="nav-preview">PREVIEW</span>
                    ) : null}
                  </Link>
                );
              })}
          </div>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-help">
          <div className="help-icon">
            <LifeBuoy size={17} />
          </div>
          <div>
            <strong>Need assistance?</strong>
            <span>Platform documentation</span>
          </div>
        </div>

        <div className="sidebar-user">
          <div className="user-avatar">AG</div>
          <div className="user-copy">
            <strong>Local Operator</strong>
            <span>Development session</span>
          </div>
          <Command size={16} className="user-command" />
        </div>
      </div>
    </aside>
  );
}