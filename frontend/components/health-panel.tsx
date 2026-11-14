"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Server, Database, Radio, Clock3 } from "lucide-react";
import { getHealthSnapshot } from "@/lib/api";
import type { HealthCheck, HealthSnapshot } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/button";

function HealthIcon({ id }: { id: string }) {
  if (id === "database") return <Database size={17} />;
  if (id === "readiness") return <Radio size={17} />;
  return <Server size={17} />;
}

function CheckRow({ check }: { check: HealthCheck }) {
  return (
    <div className="health-row">
      <div className="health-service-icon"><HealthIcon id={check.id} /></div>
      <div className="health-copy">
        <strong>{check.name}</strong>
        <small>{check.endpoint} · {check.detail}</small>
      </div>
      <div className="health-meta">
        <span>{check.latencyMs === null ? "—" : `${check.latencyMs} ms`}</span>
        <StatusBadge state={check.state} />
      </div>
    </div>
  );
}

export function HealthPanel() {
  const [snapshot, setSnapshot] = useState<HealthSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await getHealthSnapshot();
      setSnapshot(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Health check failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const next = await getHealthSnapshot();
        if (active) setSnapshot(next);
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Health check failed.");
      }
    };
    void load();
    return () => { active = false; };
  }, []);

  return (
    <section className="panel health-panel">
      <header className="panel-header">
        <div><div className="eyebrow">LIVE CONNECTIVITY</div><h2>System health</h2></div>
        <Button onClick={() => void refresh()} disabled={loading} aria-label="Refresh system health">
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
        </Button>
      </header>
      {error ? <div className="inline-error">{error}</div> : null}
      <div className="health-list">
        {snapshot ? snapshot.checks.map((check) => <CheckRow key={check.id} check={check} />) :
          <div className="loading-state"><span className="loading-spinner" /> Checking verified endpoints…</div>}
      </div>
      <footer className="health-footer">
        <span><Clock3 size={13} /> Last checked: {snapshot ? new Date(snapshot.checkedAt).toLocaleTimeString() : "Pending"}</span>
        <span className="health-note">Endpoint response ≠ full dependency certification</span>
      </footer>
    </section>
  );
}
