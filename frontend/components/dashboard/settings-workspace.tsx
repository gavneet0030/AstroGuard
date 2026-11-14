"use client";

import { useState } from "react";
import { Check, Copy, ExternalLink, Server, Shield } from "lucide-react";
import { API_BASE_URL } from "@/lib/api/config";
import { SectionHeading } from "@/components/ui/section-heading";
import { SystemHealth } from "@/components/dashboard/system-health";
import { Panel } from "@/components/ui/panel";

export function SettingsWorkspace() {
  const [copied, setCopied] = useState(false);

  async function copyApiUrl() {
    try {
      await navigator.clipboard.writeText(API_BASE_URL);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <>
      <SectionHeading
        eyebrow="PLATFORM / CONFIGURATION"
        title="System Health"
        description="Inspect backend connectivity and local application configuration."
      />

      <SystemHealth />

      <Panel
        title="Connection configuration"
        subtitle="Frontend environment"
      >
        <div className="configuration-row">
          <div className="configuration-icon">
            <Server size={18} />
          </div>
          <div className="configuration-copy">
            <strong>Backend API base URL</strong>
            <span>{API_BASE_URL}</span>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={() => void copyApiUrl()}
            aria-label="Copy API base URL"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>

        <div className="configuration-row">
          <div className="configuration-icon">
            <Shield size={18} />
          </div>
          <div className="configuration-copy">
            <strong>Authentication</strong>
            <span>
              No authenticated session flow has been connected in this phase.
            </span>
          </div>
          <span className="panel-tag">NOT CONFIGURED</span>
        </div>

        <div className="settings-note">
          <ExternalLink size={14} />
          Set NEXT_PUBLIC_API_BASE_URL in your local environment to change
          the backend target.
        </div>
      </Panel>
    </>
  );
}