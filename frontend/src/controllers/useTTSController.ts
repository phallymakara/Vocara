import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient, ApiError } from "@/controllers/apiClient";
import type { VoiceItem, JobItem, SystemLanguage } from "@/models/types";

export function useTTSController() {
  const [searchParams, setSearchParams] = useSearchParams();
  const voiceParam = searchParams.get("voice");

  const [text, setText] = useState<string>("");
  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [languages, setLanguages] = useState<SystemLanguage[]>([]);
  const [selectedVoiceId, setSelectedVoiceIdState] = useState<string>(voiceParam || "");
  const [language, setLanguage] = useState<string>("km-KH");
  const [speed, setSpeed] = useState<number>(1.0);
  const [outputFormat, setOutputFormat] = useState<"mp3" | "wav" | "flac">("mp3");

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [generatedAudioUrl, setGeneratedAudioUrl] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [activeJob, setActiveJob] = useState<JobItem | null>(null);

  const [textError, setTextError] = useState<string | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const charCount = text.length;
  const isAsyncMode = charCount >= 250;

  const setSelectedVoiceId = (id: string) => {
    setSelectedVoiceIdState(id);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (id) {
        next.set("voice", id);
      } else {
        next.delete("voice");
      }
      return next;
    });
  };

  useEffect(() => {
    if (voiceParam && voices.length > 0) {
      const matched = voices.find((v) => v.id === voiceParam);
      if (matched) {
        setSelectedVoiceIdState(matched.id);
        if (matched.language) {
          setLanguage(matched.language);
        }
      }
    }
  }, [voiceParam, voices]);

  useEffect(() => {
    loadVoices();
    loadLanguages();
  }, []);

  const loadLanguages = async () => {
    try {
      const langs = await apiClient.getLanguages();
      setLanguages(langs);
      const matched = langs.find((l) => l.code.toLowerCase() === language.toLowerCase()) || langs[0];
      if (matched?.default_preview_text) {
        setText((prev) => (prev ? prev : matched.default_preview_text || ""));
      }
    } catch {
      // Ignored if unauthenticated
    }
  };

  useEffect(() => {
    if (languages.length > 0 && !text) {
      const matched = languages.find((l) => l.code.toLowerCase() === language.toLowerCase());
      if (matched?.default_preview_text) {
        setText(matched.default_preview_text);
      }
    }
  }, [language, languages]);

  const loadVoices = async () => {
    try {
      const data = await apiClient.listVoices();
      setVoices(data);
      if (data.length > 0) {
        if (voiceParam && data.some((v) => v.id === voiceParam)) {
          setSelectedVoiceIdState(voiceParam);
        } else if (!selectedVoiceId) {
          setSelectedVoiceIdState(data[0].id);
        }
      }
    } catch {
      // Ignored if unauthenticated
    }
  };

  const synthesize = async () => {
    setTextError(null);
    setVoiceError(null);
    setGeneralError(null);

    if (!apiClient.getApiKey()) {
      setGeneralError("Please set an API key before generating speech.");
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

    setIsLoading(true);
    setGeneratedAudioUrl(null);
    setActiveJob(null);

    try {
      const result = await apiClient.synthesizeSpeech({
        text,
        voice_id: selectedVoiceId,
        language,
        speed,
        output_format: outputFormat,
      });

      if (result.type === "stream") {
        const url = URL.createObjectURL(result.audioBlob);
        setGeneratedAudioUrl(url);
        setAudioDuration(result.duration);
        setIsLoading(false);
      } else if (result.type === "job") {
        setActiveJob(result.job);
        pollJob(result.job.id);
      }
    } catch (err: unknown) {
      setIsLoading(false);
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

  const pollJob = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await apiClient.getJob(jobId);
        setActiveJob(job);

        if (job.status === "completed") {
          clearInterval(interval);
          const blob = await apiClient.getJobResultBlob(job.id);
          const url = URL.createObjectURL(blob);
          setGeneratedAudioUrl(url);
          setAudioDuration(job.audio_duration_seconds);
          setIsLoading(false);
        } else if (job.status === "failed") {
          clearInterval(interval);
          setIsLoading(false);
          setGeneralError(job.error_message || "The synthesis job could not be completed.");
        }
      } catch {
        clearInterval(interval);
        setIsLoading(false);
        setGeneralError("Failed to check job progress.");
      }
    }, 1500);
  };

  return {
    text,
    setText,
    voices,
    selectedVoiceId,
    setSelectedVoiceId,
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
    synthesize,
    hasApiKey: Boolean(apiClient.getApiKey()),
  };
}
