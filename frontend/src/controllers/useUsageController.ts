import { useState, useEffect, useCallback } from "react";
import { apiClient, ApiError } from "@/controllers/apiClient";
import type { UsageSummary } from "@/models/types";

export function useUsageController() {
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const loadUsage = useCallback(async () => {
    if (!apiClient.getApiKey()) {
      setIsLoading(false);
      setUsage(null);
      setGeneralError(null);
      return;
    }
    setIsLoading(true);
    setGeneralError(null);
    try {
      const data = await apiClient.getUsage();
      setUsage(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Could not load usage data. Please check your connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsage();
  }, [loadUsage]);

  const percentUsed = usage ? Math.round(usage.quota_percentage_used) : 0;
  const charactersRemaining = usage ? usage.quota_remaining : 0;

  const formatDuration = (totalSeconds: number): string => {
    if (totalSeconds < 60) {
      return `${Math.round(totalSeconds)}s`;
    }
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = Math.round(totalSeconds % 60);
    return `${minutes}m ${seconds}s`;
  };

  return {
    usage,
    isLoading,
    generalError,
    percentUsed,
    charactersRemaining,
    formatDuration,
    loadUsage,
  };
}
