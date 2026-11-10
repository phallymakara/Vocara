import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient, ApiError } from "@/controllers/apiClient";
import type { SystemLanguage, VoiceItem } from "@/models/types";

export function useVoiceController() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [voices, setVoices] = useState<VoiceItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [filterLang, setFilterLangState] = useState<string>(() => searchParams.get("lang") || "all");

  // Active modal ("clone" | "design" | "edit" | null)
  const [activeModal, setActiveModal] = useState<"clone" | "design" | "edit" | null>(() => {
    const action = searchParams.get("action");
    if (action === "clone" || action === "design") {
      return action;
    }
    return null;
  });

  // Edit Form State
  const [editingVoice, setEditingVoice] = useState<VoiceItem | null>(null);
  const [editName, setEditName] = useState<string>("");
  const [editDescription, setEditDescription] = useState<string>("");
  const [editVisibility, setEditVisibility] = useState<"public" | "private">("private");
  const [editPitch, setEditPitch] = useState<number>(1.0);
  const [editSpeed, setEditSpeed] = useState<number>(1.0);
  const [isSubmittingEdit, setIsSubmittingEdit] = useState<boolean>(false);
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});

  // Delete State
  const [deleteConfirmVoice, setDeleteConfirmVoice] = useState<VoiceItem | null>(null);
  const [isDeletingVoice, setIsDeletingVoice] = useState<boolean>(false);

  // Clone Form State
  const [cloneName, setCloneName] = useState<string>("");
  const [cloneLang, setCloneLang] = useState<string>("km-KH");
  const [cloneDescription, setCloneDescription] = useState<string>("");
  const [cloneFile, setCloneFile] = useState<File | null>(null);
  const [clonePromptText, setClonePromptText] = useState<string>("");
  const [consentConfirmed, setConsentConfirmed] = useState<boolean>(false);
  const [enhanceAudio, setEnhanceAudio] = useState<boolean>(true);
  const [isSubmittingClone, setIsSubmittingClone] = useState<boolean>(false);
  const [cloneErrors, setCloneErrors] = useState<Record<string, string>>({});

  // Design Form State
  const [designName, setDesignName] = useState<string>("");
  const [designDescription, setDesignDescription] = useState<string>("");
  const [designGender, setDesignGender] = useState<string>("female");
  const [designPitch, setDesignPitch] = useState<number>(1.0);
  const [designSpeed, setDesignSpeed] = useState<number>(1.0);
  const [designBaseId, setDesignBaseId] = useState<string>("");
  const [designEmotion, setDesignEmotion] = useState<string>("");
  const [designStyle, setDesignStyle] = useState<string>("");
  const [showAdvancedDesign, setShowAdvancedDesign] = useState<boolean>(false);
  const [isSubmittingDesign, setIsSubmittingDesign] = useState<boolean>(false);
  const [designErrors, setDesignErrors] = useState<Record<string, string>>({});

  // Design Audition Preview State (Generate / Regenerate before saving)
  const [systemLanguages, setSystemLanguages] = useState<SystemLanguage[]>([]);
  const [designPreviewText, setDesignPreviewTextState] = useState<string>("");
  const [designPreviewAudioUrl, setDesignPreviewAudioUrl] = useState<string | null>(null);
  const [designPreviewBase64, setDesignPreviewBase64] = useState<string | null>(null);
  const [designPreviewDuration, setDesignPreviewDuration] = useState<number>(0);
  const [designResolvedInstruction, setDesignResolvedInstruction] = useState<string>("");
  const [isGeneratingDesignPreview, setIsGeneratingDesignPreview] = useState<boolean>(false);
  const [isPlayingDesignPreview, setIsPlayingDesignPreview] = useState<boolean>(false);
  const [designPreviewAudioEl, setDesignPreviewAudioEl] = useState<HTMLAudioElement | null>(null);

  // Preview Audio
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const [previewAudio, setPreviewAudio] = useState<HTMLAudioElement | null>(null);

  useEffect(() => {
    loadVoices();
    loadSystemLanguages();
    return () => {
      if (previewAudio) {
        previewAudio.pause();
      }
      if (designPreviewAudioEl) {
        designPreviewAudioEl.pause();
      }
    };
  }, []);

  const loadSystemLanguages = async () => {
    try {
      const langs = await apiClient.getLanguages();
      setSystemLanguages(langs);
      const kmDefault = langs.find((l) => l.code.toLowerCase() === "km-kh") || langs[0];
      if (kmDefault?.default_preview_text) {
        setDesignPreviewTextState((prev) => (prev ? prev : kmDefault.default_preview_text || ""));
      }
    } catch {
      // Ignored if API unavailable
    }
  };

  const getDefaultPreviewForLanguage = (langCode: string): string => {
    const matched = systemLanguages.find((l) => l.code.toLowerCase() === langCode.toLowerCase());
    if (matched?.default_preview_text) {
      return matched.default_preview_text;
    }
    return systemLanguages[0]?.default_preview_text || "";
  };

  const invalidateDesignPreview = () => {
    if (designPreviewAudioEl) {
      designPreviewAudioEl.pause();
      setIsPlayingDesignPreview(false);
    }
    if (designPreviewAudioUrl) {
      URL.revokeObjectURL(designPreviewAudioUrl);
    }
    setDesignPreviewAudioUrl(null);
    setDesignPreviewBase64(null);
    setDesignPreviewDuration(0);
    setDesignResolvedInstruction("");
  };

  const setDesignPreviewText = (val: string) => {
    setDesignPreviewTextState(val);
    invalidateDesignPreview();
  };

  const setDesignDescriptionValidated = (val: string) => {
    setDesignDescription(val);
    invalidateDesignPreview();
  };

  const setDesignGenderValidated = (val: string) => {
    setDesignGender(val);
    invalidateDesignPreview();
  };

  const setDesignPitchValidated = (val: number) => {
    setDesignPitch(val);
    invalidateDesignPreview();
  };

  const setDesignSpeedValidated = (val: number) => {
    setDesignSpeed(val);
    invalidateDesignPreview();
  };

  // Synchronize modal state and language filter with URL search parameters
  const actionParam = searchParams.get("action");
  const langParam = searchParams.get("lang");

  useEffect(() => {
    if (actionParam === "clone") {
      setActiveModal("clone");
    } else if (actionParam === "design") {
      setActiveModal("design");
    } else if (!editingVoice) {
      setActiveModal(null);
    }
  }, [actionParam, editingVoice]);

  useEffect(() => {
    if (langParam) {
      setFilterLangState(langParam);
    } else {
      setFilterLangState("all");
    }
  }, [langParam]);

  const setFilterLang = (lang: string) => {
    setFilterLangState(lang);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (lang === "all") {
        next.delete("lang");
      } else {
        next.set("lang", lang);
      }
      return next;
    });
  };

  const openCloneModal = () => {
    setActiveModal("clone");
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("action", "clone");
      return next;
    });
  };

  const openDesignModal = () => {
    setActiveModal("design");
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("action", "design");
      return next;
    });
  };

  const closeModal = () => {
    setActiveModal(null);
    setEditingVoice(null);
    invalidateDesignPreview();
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("action");
      next.delete("edit");
      return next;
    });
  };

  const loadVoices = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.listVoices();
      setVoices(data);
    } catch {
      // Ignored
    } finally {
      setIsLoading(false);
    }
  };

  const togglePreview = (voiceId: string) => {
    if (playingVoiceId === voiceId && previewAudio) {
      previewAudio.pause();
      setPlayingVoiceId(null);
      return;
    }

    if (previewAudio) {
      previewAudio.pause();
    }

    const url = apiClient.getVoicePreviewUrl(voiceId);
    const audio = new Audio();
    audio.src = url;
    audio.onended = () => setPlayingVoiceId(null);
    audio.onerror = (e) => {
      console.error("Audio preview failed to load:", url, e);
      setPlayingVoiceId(null);
    };
    audio.play().catch((err) => {
      console.warn("Audio autoplay blocked or interrupted:", err);
      setPlayingVoiceId(null);
    });
    setPreviewAudio(audio);
    setPlayingVoiceId(voiceId);
  };

  const submitClone = async () => {
    const errors: Record<string, string> = {};
    if (!cloneName.trim()) {
      errors.name = "Please enter a name for the voice.";
    }
    if (!cloneFile) {
      errors.file = "Please upload an audio sample (WAV, MP3, or FLAC).";
    }
    if (!consentConfirmed) {
      errors.consent = "Consent confirmation is required before cloning.";
    }

    if (Object.keys(errors).length > 0) {
      setCloneErrors(errors);
      return false;
    }

    setIsSubmittingClone(true);
    setCloneErrors({});

    try {
      const formData = new FormData();
      formData.append("name", cloneName);
      formData.append("language", cloneLang);
      formData.append("description", cloneDescription);
      formData.append("consent_confirmed", "true");
      formData.append("enhance_audio", enhanceAudio ? "true" : "false");
      if (clonePromptText.trim()) {
        formData.append("prompt_text", clonePromptText.trim());
      }
      if (cloneFile) {
        formData.append("file", cloneFile);
      }

      await apiClient.cloneVoice(formData);
      setActiveModal(null);
      setCloneName("");
      setClonePromptText("");
      setCloneFile(null);
      setConsentConfirmed(false);
      setEnhanceAudio(true);
      await loadVoices();
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setCloneErrors(err.fieldErrors || { general: err.message });
      } else {
        setCloneErrors({ general: "Voice cloning failed. Please check your audio sample." });
      }
      return false;
    } finally {
      setIsSubmittingClone(false);
    }
  };

  const generateDesignPreview = async () => {
    const errors: Record<string, string> = {};
    if (designDescription.trim().length > 2000) {
      errors.description = "Description cannot exceed 2,000 characters.";
    }
    if (designPitch < 0.5 || designPitch > 2.0) {
      errors.pitch = "Pitch modifier must be between 0.5x and 2.0x.";
    }
    if (designSpeed < 0.5 || designSpeed > 2.0) {
      errors.speed = "Pace modifier must be between 0.5x and 2.0x.";
    }
    if (!designDescription.trim() && !designBaseId.trim()) {
      errors.description = "Please describe the voice personality before generating a preview.";
    }

    if (Object.keys(errors).length > 0) {
      setDesignErrors(errors);
      return false;
    }

    setIsGeneratingDesignPreview(true);
    setDesignErrors({});
    invalidateDesignPreview();

    try {
      const targetText = designPreviewText.trim() || getDefaultPreviewForLanguage("km-KH");
      const res = await apiClient.previewDesignVoice({
        description: designDescription.trim(),
        gender: designGender,
        pitch: designPitch,
        speed: designSpeed,
        base_voice_id: designBaseId.trim() || undefined,
        emotion: designEmotion.trim() || undefined,
        style: designStyle.trim() || undefined,
        preview_text: targetText || undefined,
      });

      const binary = atob(res.audio_base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: res.content_type || "audio/wav" });
      const blobUrl = URL.createObjectURL(blob);

      setDesignPreviewBase64(res.audio_base64);
      setDesignPreviewAudioUrl(blobUrl);
      setDesignPreviewDuration(res.duration_seconds || 0);
      setDesignResolvedInstruction(res.control_instruction || "");

      // Auto-play newly generated audition sample
      const audio = new Audio(blobUrl);
      audio.onended = () => setIsPlayingDesignPreview(false);
      audio.onerror = () => setIsPlayingDesignPreview(false);
      setDesignPreviewAudioEl(audio);
      audio.play().then(() => setIsPlayingDesignPreview(true)).catch(() => setIsPlayingDesignPreview(false));

      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setDesignErrors(err.fieldErrors || { general: err.message });
      } else {
        setDesignErrors({ general: "Could not generate preview. Please try again." });
      }
      return false;
    } finally {
      setIsGeneratingDesignPreview(false);
    }
  };

  const togglePlayDesignPreview = () => {
    if (!designPreviewAudioUrl) return;
    if (isPlayingDesignPreview && designPreviewAudioEl) {
      designPreviewAudioEl.pause();
      setIsPlayingDesignPreview(false);
      return;
    }
    const audio = designPreviewAudioEl || new Audio(designPreviewAudioUrl);
    audio.src = designPreviewAudioUrl;
    audio.onended = () => setIsPlayingDesignPreview(false);
    audio.onerror = () => setIsPlayingDesignPreview(false);
    setDesignPreviewAudioEl(audio);
    audio.play().then(() => setIsPlayingDesignPreview(true)).catch(() => setIsPlayingDesignPreview(false));
  };

  const submitDesign = async () => {
    const errors: Record<string, string> = {};
    const trimmedName = designName.trim();
    if (!trimmedName) {
      errors.name = "Please enter a voice name.";
    } else if (trimmedName.length < 2) {
      errors.name = "Voice name must be at least 2 characters.";
    } else if (trimmedName.length > 100) {
      errors.name = "Voice name cannot exceed 100 characters.";
    }

    if (designDescription.trim().length > 2000) {
      errors.description = "Description cannot exceed 2,000 characters.";
    }

    if (designPitch < 0.5 || designPitch > 2.0) {
      errors.pitch = "Pitch modifier must be between 0.5x and 2.0x.";
    }

    if (designSpeed < 0.5 || designSpeed > 2.0) {
      errors.speed = "Pace modifier must be between 0.5x and 2.0x.";
    }

    if (Object.keys(errors).length > 0) {
      setDesignErrors(errors);
      return false;
    }

    setIsSubmittingDesign(true);
    setDesignErrors({});

    try {
      await apiClient.designVoice({
        name: trimmedName,
        description: designDescription.trim(),
        gender: designGender,
        pitch: designPitch,
        speed: designSpeed,
        base_voice_id: designBaseId.trim() || undefined,
        emotion: designEmotion.trim() || undefined,
        style: designStyle.trim() || undefined,
        preview_text: designPreviewText.trim() || undefined,
        preview_audio_base64: designPreviewBase64 || undefined,
      });

      invalidateDesignPreview();
      closeModal();
      setDesignName("");
      setDesignDescription("");
      setDesignGender("female");
      setDesignBaseId("");
      setDesignEmotion("");
      setDesignStyle("");
      setShowAdvancedDesign(false);
      await loadVoices();
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setDesignErrors(err.fieldErrors || { general: err.message });
      } else {
        setDesignErrors({ general: "Voice design failed. Please try again." });
      }
      return false;
    } finally {
      setIsSubmittingDesign(false);
    }
  };

  const openEditModal = (voice: VoiceItem) => {
    setEditingVoice(voice);
    setEditName(voice.name);
    setEditDescription(voice.description || "");
    setEditVisibility(voice.visibility as "public" | "private");
    const pitch = Number(voice.modifiers?.pitch ?? 1.0);
    const speed = Number(voice.modifiers?.speed ?? 1.0);
    setEditPitch(isNaN(pitch) ? 1.0 : pitch);
    setEditSpeed(isNaN(speed) ? 1.0 : speed);
    setEditErrors({});
    setActiveModal("edit");
  };

  const submitEdit = async () => {
    if (!editingVoice) return false;
    const errors: Record<string, string> = {};
    if (!editName.trim()) {
      errors.name = "Please enter a voice name.";
    }
    if (editDescription.trim().length > 2000) {
      errors.description = "Description cannot exceed 2,000 characters.";
    }

    if (Object.keys(errors).length > 0) {
      setEditErrors(errors);
      return false;
    }

    setIsSubmittingEdit(true);
    setEditErrors({});

    try {
      await apiClient.updateVoice(editingVoice.id, {
        name: editName.trim(),
        description: editDescription.trim(),
        visibility: editVisibility,
        modifiers: {
          pitch: editPitch,
          speed: editSpeed,
        },
      });

      setActiveModal(null);
      setEditingVoice(null);
      await loadVoices();
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setEditErrors(err.fieldErrors || { general: err.message });
      } else {
        setEditErrors({ general: "Failed to update voice. Please try again." });
      }
      return false;
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const openDeleteConfirm = (voice: VoiceItem) => {
    setDeleteConfirmVoice(voice);
  };

  const closeDeleteConfirm = () => {
    setDeleteConfirmVoice(null);
  };

  const submitDelete = async () => {
    if (!deleteConfirmVoice) return;
    setIsDeletingVoice(true);
    try {
      await apiClient.deleteVoice(deleteConfirmVoice.id);
      setDeleteConfirmVoice(null);
      await loadVoices();
    } catch (err: unknown) {
      console.error("Failed to delete voice:", err);
    } finally {
      setIsDeletingVoice(false);
    }
  };

  const filteredVoices = voices.filter((v) => {
    if (filterLang === "all") return true;
    return v.language.toLowerCase().includes(filterLang.toLowerCase());
  });

  return {
    voices,
    filteredVoices,
    isLoading,
    filterLang,
    setFilterLang,
    activeModal,
    setActiveModal,
    openCloneModal,
    openDesignModal,
    openEditModal,
    closeModal,
    // Clone
    cloneName,
    setCloneName,
    cloneLang,
    setCloneLang,
    cloneDescription,
    setCloneDescription,
    cloneFile,
    setCloneFile,
    clonePromptText,
    setClonePromptText,
    consentConfirmed,
    setConsentConfirmed,
    enhanceAudio,
    setEnhanceAudio,
    isSubmittingClone,
    cloneErrors,
    submitClone,
    // Design
    designName,
    setDesignName,
    designDescription,
    setDesignDescription: setDesignDescriptionValidated,
    designGender,
    setDesignGender: setDesignGenderValidated,
    designPitch,
    setDesignPitch: setDesignPitchValidated,
    designSpeed,
    setDesignSpeed: setDesignSpeedValidated,
    designBaseId,
    setDesignBaseId,
    designEmotion,
    setDesignEmotion,
    designStyle,
    setDesignStyle,
    showAdvancedDesign,
    setShowAdvancedDesign,
    isSubmittingDesign,
    designErrors,
    submitDesign,
    // Design Audition Preview
    designPreviewText,
    setDesignPreviewText,
    designPreviewAudioUrl,
    designPreviewDuration,
    designResolvedInstruction,
    isGeneratingDesignPreview,
    isPlayingDesignPreview,
    generateDesignPreview,
    togglePlayDesignPreview,
    getDefaultPreviewForLanguage,
    // Edit
    editingVoice,
    editName,
    setEditName,
    editDescription,
    setEditDescription,
    editVisibility,
    setEditVisibility,
    editPitch,
    setEditPitch,
    editSpeed,
    setEditSpeed,
    isSubmittingEdit,
    editErrors,
    submitEdit,
    // Delete
    deleteConfirmVoice,
    openDeleteConfirm,
    closeDeleteConfirm,
    isDeletingVoice,
    submitDelete,
    // Audio
    playingVoiceId,
    togglePreview,
  };
}
