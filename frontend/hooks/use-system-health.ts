"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchHealthSnapshot } from "@/lib/api/health";
import { HEALTH_POLL_INTERVAL } from "@/lib/api/config";
import type { HealthSnapshot } from "@/types/system";

export function useSystemHealth() {
  const [snapshot, setSnapshot] =
    useState<HealthSnapshot | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);

    try {
      const result = await fetchHealthSnapshot();
      setSnapshot(result);
      setLastError(null);
    } catch (error) {
      setLastError(
        error instanceof Error
          ? error.message
          : "Unable to retrieve health"
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    const run = async () => {
      if (!active) {
        return;
      }

      await refresh();
    };

    void run();

    const timer = window.setInterval(
      () => void run(),
      HEALTH_POLL_INTERVAL
    );

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [refresh]);

  return {
    snapshot,
    loading,
    refreshing,
    lastError,
    refresh
  };
}