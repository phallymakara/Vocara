import { useState, useEffect, useCallback } from "react";
import { apiClient, ApiError } from "@/controllers/apiClient";
import type { WebhookSubscription, JobItem } from "@/models/types";

export function useWebhookController() {
  // Webhooks State
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([]);
  const [isLoadingWebhooks, setIsLoadingWebhooks] = useState<boolean>(true);
  const [targetUrl, setTargetUrl] = useState<string>("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([
    "job.completed",
    "job.failed",
  ]);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [webhookError, setWebhookError] = useState<string | null>(null);

  // Job Inspection State
  const [jobIdInput, setJobIdInput] = useState<string>("");
  const [inspectedJob, setInspectedJob] = useState<JobItem | null>(null);
  const [isInspectingJob, setIsInspectingJob] = useState<boolean>(false);
  const [jobSearchError, setJobSearchError] = useState<string | null>(null);

  const loadWebhooks = useCallback(async () => {
    if (!apiClient.getApiKey()) {
      setIsLoadingWebhooks(false);
      setWebhooks([]);
      setWebhookError(null);
      return;
    }
    setIsLoadingWebhooks(true);
    setWebhookError(null);
    try {
      const data = await apiClient.listWebhooks();
      setWebhooks(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setWebhookError(err.message);
      } else {
        setWebhookError("Could not retrieve webhooks. Please check your connection.");
      }
    } finally {
      setIsLoadingWebhooks(false);
    }
  }, []);

  useEffect(() => {
    loadWebhooks();
  }, [loadWebhooks]);

  const toggleEvent = (event: string) => {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  const createWebhook = async () => {
    setUrlError(null);
    setWebhookError(null);

    if (!targetUrl.trim()) {
      setUrlError("Please enter a valid webhook endpoint URL.");
      return;
    }

    if (!targetUrl.startsWith("http://") && !targetUrl.startsWith("https://")) {
      setUrlError("URL must start with http:// or https://");
      return;
    }

    if (selectedEvents.length === 0) {
      setWebhookError("Please select at least one event.");
      return;
    }

    try {
      await apiClient.createWebhook(targetUrl.trim(), selectedEvents);
      setTargetUrl("");
      await loadWebhooks();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.fieldErrors?.url) {
          setUrlError(err.fieldErrors.url);
        } else {
          setWebhookError(err.message);
        }
      } else {
        setWebhookError("Unable to register webhook endpoint.");
      }
    }
  };

  const deleteWebhook = async (id: string) => {
    setWebhookError(null);
    try {
      await apiClient.deleteWebhook(id);
      await loadWebhooks();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setWebhookError(err.message);
      } else {
        setWebhookError("Failed to delete webhook subscription.");
      }
    }
  };

  const inspectJob = async () => {
    setJobSearchError(null);
    setInspectedJob(null);

    const id = jobIdInput.trim();
    if (!id) {
      setJobSearchError("Please enter a Job ID.");
      return;
    }

    setIsInspectingJob(true);
    try {
      const job = await apiClient.getJob(id);
      setInspectedJob(job);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setJobSearchError(err.message);
      } else {
        setJobSearchError("Job not found or failed to fetch.");
      }
    } finally {
      setIsInspectingJob(false);
    }
  };

  const downloadJobAudio = async (jobId: string) => {
    try {
      const blob = await apiClient.getJobResultBlob(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `job_${jobId}.mp3`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setJobSearchError("Could not download audio result for this job.");
    }
  };

  return {
    webhooks,
    isLoadingWebhooks,
    targetUrl,
    setTargetUrl,
    selectedEvents,
    toggleEvent,
    urlError,
    webhookError,
    jobIdInput,
    setJobIdInput,
    inspectedJob,
    isInspectingJob,
    jobSearchError,
    loadWebhooks,
    createWebhook,
    deleteWebhook,
    inspectJob,
    downloadJobAudio,
  };
}

