import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { apiClient, ApiError } from "@/controllers/apiClient";
import type { JobItem, SystemLanguage, VoiceItem } from "@/models/types";

export interface TTSHistoryItem {
  id: string;
  text: string;
  voiceId: string;
  voiceName: string;
  outputFormat: "mp3" | "wav" | "flac";
  speed: number;
  duration: number;
  audioUrl: string;
  createdAt: string;
}

interface TTSContextValue {
  text: string;
  setText: (text: string) => void;
  voices: VoiceItem[];
  languages: SystemLanguage[];
  selectedVoiceId: string;
  setSelectedVoiceId: (id: string) => void;
  selectVoiceFromParam: (id: string | null) => void;
  language: string;
  setLanguage: (lang: string) => void;
  speed: number;
  setSpeed: (speed: number) => void;
  outputFormat: "mp3" | "wav" | "flac";
  setOutputFormat: (fmt: "mp3" | "wav" | "flac") => void;
  isLoading: boolean;
  generatedAudioUrl: string | null;
  audioDuration: number;
  activeJob: JobItem | null;
  charCount: number;
  isAsyncMode: boolean;
  textError: string | null;
  setTextError: (err: string | null) => void;
  voiceError: string | null;
  setVoiceError: (err: string | null) => void;
  generalError: string | null;
  history: TTSHistoryItem[];
  synthesize: () => Promise<void>;
  stopGeneration: () => void;
  loadHistoryItem: (item: TTSHistoryItem) => void;
  removeHistoryItem: (id: string) => void;
  clearHistory: () => void;
  hasApiKey: boolean;
}

const MAX_HISTORY_ITEMS = 20;

const TTSContext = createContext<TTSContextValue | undefined>(undefined);

function detectSpeechLanguage(inputText: string, fallback: string): string {
  const hasKhmer = /[\u1780-\u17FF]/.test(inputText);
  const hasLatin = /[A-Za-z]/.test(inputText);
  if (hasKhmer && hasLatin) return "mixed";
  if (hasKhmer) return "km-KH";
  if (hasLatin) return "en-US";
  return fallback || "km-KH";
}

export const TTSProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [text, setText] = useState<string>("");
  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [languages, setLanguages] = useState<SystemLanguage[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>("");
  const [language, setLanguage] = useState<string>("km-KH");
  const [speed, setSpeed] = useState<number>(1.0);
  const [outputFormat, setOutputFormat] = useState<"mp3" | "wav" | "flac">("mp3");

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [generatedAudioUrl, setGeneratedAudioUrl] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [activeJob, setActiveJob] = useState<JobItem | null>(null);
  const [history, setHistory] = useState<TTSHistoryItem[]>([]);

  const [textError, setTextError] = useState<string | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const trackedUrlsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      trackedUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      trackedUrlsRef.current.clear();
    };
  }, []);

  useEffect(() => {
    const loadInitial = async () => {
      try {
        const [voiceList, langList] = await Promise.all([
          apiClient.listVoices(),
          apiClient.getLanguages(),
        ]);
        setVoices(voiceList);
        setLanguages(langList);

        if (voiceList.length > 0) {
          const nonBuiltIn = voiceList.filter((v) => v.voice_type !== "built_in");
          const originalKhmer = voiceList.find((v) => v.id === "voice-voxcpm-khmer-original");
          const defaultVoice = nonBuiltIn[0] || originalKhmer || voiceList[0];
          setSelectedVoiceId((prev) => prev || defaultVoice.id);
        }
      } catch {
        // Ignored if unauthenticated or transient error
      }
    };

    loadInitial();
  }, []);

  const selectVoiceFromParam = (voiceParam: string | null) => {
    if (!voiceParam || voices.length === 0) return;
    const matched = voices.find((v) => v.id === voiceParam);
    if (matched) {
      setSelectedVoiceId(matched.id);
      if (matched.language) {
        setLanguage(matched.language);
      }
    }
  };

  const clearActiveGeneration = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  const stopGeneration = () => {
    clearActiveGeneration();
    setIsLoading(false);
  };

  const pushHistoryItem = (item: TTSHistoryItem) => {
    trackedUrlsRef.current.add(item.audioUrl);
    setHistory((prev) => {
      const next = [item, ...prev];
      if (next.length > MAX_HISTORY_ITEMS) {
        const evicted = next.slice(MAX_HISTORY_ITEMS);
        evicted.forEach((old) => {
          URL.revokeObjectURL(old.audioUrl);
          trackedUrlsRef.current.delete(old.audioUrl);
        });
        return next.slice(0, MAX_HISTORY_ITEMS);
      }
      return next;
    });
  };

  const finalizeGeneratedAudio = (
    blob: Blob,
    duration: number,
    meta: {
      text: string;
      voiceId: string;
      voiceName: string;
      outputFormat: "mp3" | "wav" | "flac";
      speed: number;
    }
  ) => {
    const url = URL.createObjectURL(blob);
    trackedUrlsRef.current.add(url);
    setGeneratedAudioUrl(url);
    setAudioDuration(duration);
    setIsLoading(false);
    abortControllerRef.current = null;

    pushHistoryItem({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      text: meta.text,
      voiceId: meta.voiceId,
      voiceName: meta.voiceName,
      outputFormat: meta.outputFormat,
      speed: meta.speed,
      duration,
      audioUrl: url,
      createdAt: new Date().toISOString(),
    });

    window.dispatchEvent(new CustomEvent("vocara:usage-updated"));
  };

  const pollJob = (
    jobId: string,
    controller: AbortController,
    meta: {
      text: string;
      voiceId: string;
      voiceName: string;
      outputFormat: "mp3" | "wav" | "flac";
      speed: number;
    }
  ) => {
    pollIntervalRef.current = setInterval(async () => {
      if (controller.signal.aborted) {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        return;
      }
      try {
        const job = await apiClient.getJob(jobId, controller.signal);
        setActiveJob(job);

        if (job.status === "completed") {
          clearActiveGeneration();
          const blob = await apiClient.getJobResultBlob(job.id, controller.signal);
          finalizeGeneratedAudio(blob, job.audio_duration_seconds, meta);
        } else if (job.status === "failed") {
          clearActiveGeneration();
          setIsLoading(false);
          setGeneralError(job.error_message || "The synthesis job could not be completed.");
        }
      } catch (err: unknown) {
        clearActiveGeneration();
        setIsLoading(false);
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          setGeneralError("Failed to check job progress.");
        }
      }
    }, 1500);
  };

  const synthesize = async () => {
    setTextError(null);
    setVoiceError(null);
    setGeneralError(null);

    if (!apiClient.getAuthToken() && !apiClient.getApiKey()) {
      setGeneralError("Please sign in or set an API key before generating speech.");
      return;
    }

    if (!text.trim()) {
      setTextError("Please enter text to synthesize.");
      return;
    }

    if (!selectedVoiceId) {
      setVoiceError("Please select a voice profile.");
      return;
    }

    clearActiveGeneration();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const snapshotVoice = voices.find((v) => v.id === selectedVoiceId);
    const meta = {
      text,
      voiceId: selectedVoiceId,
      voiceName: snapshotVoice?.name || "Selected Voice",
      outputFormat,
      speed,
    };

    setIsLoading(true);
    setGeneratedAudioUrl(null);
    setActiveJob(null);

    try {
      const detectedLanguage = detectSpeechLanguage(text, language);
      const result = await apiClient.synthesizeSpeech(
        {
          text,
          voice_id: selectedVoiceId,
          language: detectedLanguage,
          speed,
          output_format: outputFormat,
        },
        controller.signal
      );

      if (controller.signal.aborted) return;

      if (result.type === "stream") {
        finalizeGeneratedAudio(result.audioBlob, result.duration, meta);
      } else if (result.type === "job") {
        setActiveJob(result.job);
        pollJob(result.job.id, controller, meta);
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setIsLoading(false);
        return;
      }
      setIsLoading(false);
      abortControllerRef.current = null;
      if (err instanceof ApiError) {
        if (err.fieldErrors?.text) {
          setTextError(err.fieldErrors.text);
        } else if (err.fieldErrors?.voice_id) {
          setVoiceError(err.fieldErrors.voice_id);
        } else {
          setGeneralError(err.message);
        }
      } else {
        setGeneralError("Could not generate audio. Please check your connection.");
      }
    }
  };

  const loadHistoryItem = (item: TTSHistoryItem) => {
    setText(item.text);
    setSelectedVoiceId(item.voiceId);
    setOutputFormat(item.outputFormat);
    setSpeed(item.speed);
    setGeneratedAudioUrl(item.audioUrl);
    setAudioDuration(item.duration);
    setTextError(null);
    setVoiceError(null);
    setGeneralError(null);
  };

  const removeHistoryItem = (id: string) => {
    setHistory((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target && target.audioUrl !== generatedAudioUrl) {
        URL.revokeObjectURL(target.audioUrl);
        trackedUrlsRef.current.delete(target.audioUrl);
      }
      return prev.filter((item) => item.id !== id);
    });
  };

  const clearHistory = () => {
    setHistory((prev) => {
      prev.forEach((item) => {
        if (item.audioUrl !== generatedAudioUrl) {
          URL.revokeObjectURL(item.audioUrl);
          trackedUrlsRef.current.delete(item.audioUrl);
        }
      });
      return [];
    });
  };

  const charCount = text.length;
  const isAsyncMode = charCount >= 250;

  return (
    <TTSContext.Provider
      value={{
        text,
        setText,
        voices,
        languages,
        selectedVoiceId,
        setSelectedVoiceId,
        selectVoiceFromParam,
        language,
        setLanguage,
        speed,
        setSpeed,
        outputFormat,
        setOutputFormat,
        isLoading,
        generatedAudioUrl,
        audioDuration,
        activeJob,
        charCount,
        isAsyncMode,
        textError,
        setTextError,
        voiceError,
        setVoiceError,
        generalError,
        history,
        synthesize,
        stopGeneration,
        loadHistoryItem,
        removeHistoryItem,
        clearHistory,
        hasApiKey: Boolean(apiClient.getAuthToken() || apiClient.getApiKey()),
      }}
    >
      {children}
    </TTSContext.Provider>
  );
};

export function useTTSContext(): TTSContextValue {
  const ctx = useContext(TTSContext);
  if (!ctx) {
    throw new Error("useTTSContext must be used within TTSProvider");
  }
  return ctx;
}

