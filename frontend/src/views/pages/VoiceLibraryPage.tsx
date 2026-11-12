import React from "react";
import { Link } from "react-router-dom";
import { Plus, Sliders, Play, Pause, Upload, Loader2, ChevronDown, ChevronRight, Edit2, Trash2, Mic, RefreshCw, Download } from "lucide-react";
import { useVoiceController } from "@/controllers/useVoiceController";
import { Button } from "@/views/components/ui/button";
import { Input } from "@/views/components/ui/input";
import { Label } from "@/views/components/ui/label";
import { Slider } from "@/views/components/ui/slider";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/views/components/ui/dialog";

export const VoiceLibraryPage: React.FC = () => {
  const {
    voices,
    isLoading,
    filterLang,
    setFilterLang,
    filterGender,
    setFilterGender,
    activeModal,
    openCloneModal,
    openDesignModal,
    openEditModal,
    closeModal,
    cloneName,
    setCloneName,
    cloneLang,
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
    designName,
    setDesignName,
    designDescription,
    setDesignDescription,
    designGender,
    setDesignGender,
    designPitch,
    setDesignPitch,
    designSpeed,
    setDesignSpeed,
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
    downloadingVoiceId,
    togglePreview,
    downloadVoicePreview,
  } = useVoiceController();

  const filteredVoices = voices.filter((v) => {
    if (filterLang !== "all" && v.language !== filterLang) return false;
    if (filterGender !== "all") {
      const gender = String(v.modifiers?.gender ?? "").trim().toLowerCase();
      if (gender !== filterGender) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Filters & Actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Language Filter Buttons */}
          {[
            { id: "all", label: "All Voices" },
            { id: "km-KH", label: "Khmer (km-KH)" },
            { id: "en-US", label: "English (en-US)" },
          ].map((tab) => {
            const isActive = filterLang === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilterLang(tab.id)}
                className={`h-8 px-3.5 rounded-full border text-xs transition-colors cursor-pointer ${
                  isActive
                    ? "border-[#1264F5] bg-[#1264F5] hover:bg-[#0E52CC] text-white font-semibold"
                    : "border-[#E5EBF5] bg-white text-[#64748B] font-medium hover:text-[#15213D] hover:bg-[#F8FAFC]"
                }`}
              >
                {tab.label}
              </button>
            );
          })}

          <span className="hidden sm:inline-block h-4 w-px bg-[#E5EBF5] mx-1" aria-hidden="true" />

          {/* Gender Filter Buttons */}
          {[
            { id: "all", label: "All" },
            { id: "female", label: "Female" },
            { id: "male", label: "Male" },
          ].map((tab) => {
            const isActive = filterGender === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilterGender(tab.id)}
                className={`h-8 px-3.5 rounded-full border text-xs transition-colors cursor-pointer ${
                  isActive
                    ? "border-[#1264F5] bg-[#1264F5] hover:bg-[#0E52CC] text-white font-semibold"
                    : "border-[#E5EBF5] bg-white text-[#64748B] font-medium hover:text-[#15213D] hover:bg-[#F8FAFC]"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={openDesignModal}
            className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full border border-[#E5EBF5] bg-white hover:bg-[#F8FAFC] hover:border-[#1264F5]/40 text-xs font-semibold text-[#15213D] transition-colors cursor-pointer"
          >
            <Sliders className="h-3.5 w-3.5 text-[#1264F5]" />
            <span>Design Voice</span>
          </button>
          <button
            type="button"
            onClick={openCloneModal}
            className="inline-flex items-center gap-1.5 h-9 px-4 rounded-full bg-[#1264F5] hover:bg-[#0E52CC] text-xs font-semibold text-white transition-colors cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Clone Voice</span>
          </button>
        </div>
      </div>

      {/* Voice Grid */}
      {isLoading ? (
        <div className="py-14 flex justify-center items-center text-[#64748B] text-sm">
          <Loader2 className="h-5 w-5 animate-spin mr-2 text-[#1264F5]" />
          Loading voices...
        </div>
      ) : filteredVoices.length === 0 ? (
        <div className="min-h-[50vh] flex items-center justify-center text-center text-[#64748B] text-sm">
          No voices found for this filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredVoices.map((voice) => {
            const isPlaying = playingVoiceId === voice.id;
            const voiceTypeLabel =
              voice.voice_type === "cloned"
                ? "Cloned Voice"
                : voice.voice_type === "designed"
                ? "Designed Voice"
                : "Built-in";
            return (
              <div
                key={voice.id}
                className={`group flex flex-col justify-between bg-white border rounded-3xl px-5 py-6 min-h-[164px] w-full max-w-sm transition-colors ${
                  isPlaying
                    ? "border-[#1264F5]"
                    : "border-[#E5EBF5] hover:border-[#1264F5]/40"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="text-[15px] font-semibold text-[#15213D] leading-snug truncate">
                      {voice.name}
                    </h3>
                    <p className="text-xs text-[#64748B] mt-1 capitalize">
                      {voice.language} &middot; {voice.visibility}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 text-[11px] font-medium ${
                      voice.voice_type === "cloned"
                        ? "text-[#1264F5]"
                        : "text-[#64748B]"
                    }`}
                  >
                    {voiceTypeLabel}
                  </span>
                </div>

                <div className="flex items-center justify-between gap-2 pt-4 mt-4 border-t border-[#E5EBF5]">
                  <div className="flex items-center gap-1">
                    {voice.voice_type !== "built_in" && (
                      <>
                        <button
                          type="button"
                          onClick={() => openEditModal(voice)}
                          className="h-8 w-8 rounded-lg inline-flex items-center justify-center text-[#64748B] hover:text-[#15213D] hover:bg-[#F8FAFC] transition-colors cursor-pointer"
                          title="Edit Voice"
                          aria-label={`Edit ${voice.name}`}
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => openDeleteConfirm(voice)}
                          className="h-8 w-8 rounded-lg inline-flex items-center justify-center text-[#64748B] hover:text-destructive hover:bg-destructive/5 transition-colors cursor-pointer"
                          title="Delete Voice"
                          aria-label={`Delete ${voice.name}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      onClick={() => downloadVoicePreview(voice)}
                      disabled={downloadingVoiceId === voice.id}
                      className="h-8 w-8 rounded-lg inline-flex items-center justify-center text-[#64748B] hover:text-[#15213D] hover:bg-[#F8FAFC] disabled:opacity-40 transition-colors cursor-pointer"
                      title="Download Voice Sample"
                      aria-label={`Download ${voice.name}`}
                    >
                      {downloadingVoiceId === voice.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-[#1264F5]" />
                      ) : (
                        <Download className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => togglePreview(voice.id)}
                      className={`inline-flex items-center justify-center h-8 px-3.5 rounded-full border text-xs font-medium gap-1.5 transition-colors cursor-pointer ${
                        isPlaying
                          ? "border-[#1264F5] bg-[#1264F5] text-white hover:bg-[#0E52CC]"
                          : "border-[#E5EBF5] bg-white text-[#15213D] hover:border-[#1264F5]/40 hover:text-[#1264F5]"
                      }`}
                    >
                      {isPlaying ? (
                        <>
                          <Pause className="h-3.5 w-3.5" />
                          <span>Stop</span>
                        </>
                      ) : (
                        <>
                          <Play className="h-3.5 w-3.5" />
                          <span>Preview</span>
                        </>
                      )}
                    </button>
                    <Link
                      to={`/?voice=${encodeURIComponent(voice.id)}`}
                      className="inline-flex items-center justify-center h-8 px-3.5 rounded-full bg-[#EBF2FE] text-[#1264F5] hover:bg-[#1264F5] hover:text-white text-xs font-semibold transition-colors gap-1.5"
                      title="Use this voice in TTS Studio"
                    >
                      <Mic className="h-3.5 w-3.5" />
                      <span>Use</span>
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Voice Clone Modal */}
      <Dialog open={activeModal === "clone"} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Instant Voice Cloning</DialogTitle>
            <DialogDescription>
              Upload 5-30 seconds of clean speech to create a personalized neural voice.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <Label htmlFor="clone-name">Voice Name</Label>
              <Input
                id="clone-name"
                value={cloneName}
                onChange={(e) => setCloneName(e.target.value)}
                placeholder="Enter voice name..."
                error={Boolean(cloneErrors.name)}
              />
              {cloneErrors.name && (
                <p className="text-xs text-destructive mt-1">{cloneErrors.name}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="clone-file">Audio Reference Sample (WAV, MP3, M4A, WebM, FLAC)</Label>
              <Input
                id="clone-file"
                type="file"
                accept="audio/*,.wav,.mp3,.ogg,.flac,.m4a,.webm,.aac"
                onChange={(e) => {
                  if (e.target.files?.[0]) setCloneFile(e.target.files[0]);
                }}
                error={Boolean(cloneErrors.file)}
              />
              {cloneErrors.file && (
                <p className="text-xs text-destructive mt-1">{cloneErrors.file}</p>
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <Label htmlFor="clone-transcript">Spoken Text / Transcript</Label>
                <span className="text-[11px] text-muted-foreground">Optional, enables 95%+ match</span>
              </div>
              <textarea
                id="clone-transcript"
                rows={2}
                value={clonePromptText}
                onChange={(e) => setClonePromptText(e.target.value)}
                placeholder="Type the exact text spoken in your audio (or click 'Use this script' below)..."
                className="w-full px-3 py-2 text-xs bg-background border border-input rounded-md text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring resize-none"
              />
              <p className="text-[11px] text-muted-foreground">
                Aligning audio with text triggers Ultimate Cloning for exact vocal nuance, accent, and inflection. If blank, it will be automatically transcribed on GPU.
              </p>
            </div>

            <div className="rounded border border-border bg-muted/20 p-2.5 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-medium text-foreground">Recommended Script to Read:</span>
                <button
                  type="button"
                  onClick={() => setClonePromptText(getDefaultPreviewForLanguage(cloneLang))}
                  className="text-[11px] text-primary hover:underline font-normal cursor-pointer"
                >
                  Use this script
                </button>
              </div>
              <p className="text-muted-foreground select-all font-sans font-medium">
                &ldquo;{getDefaultPreviewForLanguage(cloneLang)}&rdquo;
              </p>
              <p className="text-[11px] text-muted-foreground">
                Speaking this phrase provides the optimal acoustic foundation for your cloned preview.
              </p>
            </div>

            <div className="pt-1">
              <div className="flex items-start gap-2.5">
                <input
                  type="checkbox"
                  id="enhance-check"
                  checked={enhanceAudio}
                  onChange={(e) => setEnhanceAudio(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-input text-primary focus:ring-primary"
                />
                <Label htmlFor="enhance-check" className="text-xs text-muted-foreground leading-normal font-normal">
                  <span className="font-medium text-foreground">Gentle Noise Reduction:</span> Subtly remove low-frequency microphone rumble and background room hiss while keeping your voice 100% natural.
                </Label>
              </div>
            </div>

            <div className="pt-1">
              <div className="flex items-start gap-2.5">
                <input
                  type="checkbox"
                  id="consent-check"
                  checked={consentConfirmed}
                  onChange={(e) => setConsentConfirmed(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-input text-primary focus:ring-primary"
                />
                <Label htmlFor="consent-check" className="text-xs text-muted-foreground leading-normal font-normal">
                  I confirm that I own or hold explicit legal authorization and consent to synthesize and clone this voice.
                </Label>
              </div>
              {cloneErrors.consent && (
                <p className="text-xs text-destructive mt-1">{cloneErrors.consent}</p>
              )}
            </div>

            {cloneErrors.general && (
              <p className="text-xs text-destructive">{cloneErrors.general}</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={closeModal} disabled={isSubmittingClone}>
              Cancel
            </Button>
            <Button onClick={submitClone} disabled={isSubmittingClone}>
              {isSubmittingClone ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Cloning...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-1.5" />
                  Create Voice
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Voice Design Modal */}
      <Dialog open={activeModal === "design"} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="sm:max-w-lg max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Acoustic Voice Design</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2 overflow-y-auto pr-1 flex-1">
            <div className="space-y-1">
              <Label htmlFor="design-name">Voice Name</Label>
              <Input
                id="design-name"
                value={designName}
                onChange={(e) => setDesignName(e.target.value)}
                placeholder="Enter voice name..."
                error={Boolean(designErrors.name)}
              />
              {designErrors.name && (
                <p className="text-xs text-destructive mt-1">{designErrors.name}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label>Speaker Gender</Label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "female", label: "Female" },
                  { id: "male", label: "Male" },
                  { id: "neutral", label: "Neutral" },
                ].map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => setDesignGender(g.id)}
                    className={`flex items-center justify-center py-2 px-3 text-xs font-medium rounded-md border transition-all ${
                      designGender === g.id
                        ? "border-[#1264F5] bg-[#1264F5]/10 text-[#1264F5] font-semibold"
                        : "border-input bg-background hover:bg-muted/50 text-muted-foreground"
                    }`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <Label htmlFor="design-desc">Description</Label>
                <span className="text-[11px] text-muted-foreground font-mono">
                  {designDescription.length}/2,000
                </span>
              </div>
              <textarea
                id="design-desc"
                value={designDescription}
                onChange={(e) => setDesignDescription(e.target.value)}
                placeholder="Enter voice description..."
                rows={3}
                maxLength={2000}
                className={`w-full px-3 py-2 text-xs bg-background border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-y min-h-[72px] transition-colors ${
                  designErrors.description ? "border-destructive ring-destructive" : "border-input"
                }`}
              />
              {designErrors.description && (
                <p className="text-xs text-destructive mt-1">{designErrors.description}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="design-preview-text">Preview Phrase</Label>
              <textarea
                id="design-preview-text"
                value={designPreviewText}
                onChange={(e) => setDesignPreviewText(e.target.value)}
                rows={2}
                maxLength={500}
                className="w-full px-3 py-2 text-xs bg-background border border-input rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-y min-h-[56px]"
              />
              <div className="flex items-center justify-between gap-2 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={generateDesignPreview}
                  disabled={isGeneratingDesignPreview || isSubmittingDesign}
                  className="h-8 text-xs"
                >
                  {isGeneratingDesignPreview ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      Generating Preview...
                    </>
                  ) : designPreviewAudioUrl ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                      Regenerate
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5 mr-1.5" />
                      Generate Preview
                    </>
                  )}
                </Button>

                {designPreviewAudioUrl && (
                  <div className="flex items-center gap-1.5">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={togglePlayDesignPreview}
                      className="h-8 text-xs"
                    >
                      {isPlayingDesignPreview ? (
                        <>
                          <Pause className="h-3.5 w-3.5 mr-1.5" />
                          Stop ({designPreviewDuration.toFixed(1)}s)
                        </>
                      ) : (
                        <>
                          <Play className="h-3.5 w-3.5 mr-1.5" />
                          Listen ({designPreviewDuration.toFixed(1)}s)
                        </>
                      )}
                    </Button>
                    <a
                      href={designPreviewAudioUrl}
                      download={`${(designName || "voice_design_preview").trim().replace(/[^a-zA-Z0-9_-]+/g, "_") || "voice_design_preview"}.wav`}
                      className="inline-flex items-center justify-center h-8 px-2.5 rounded-md border border-input bg-background text-xs font-medium text-foreground hover:bg-muted transition-colors gap-1"
                      title="Download Preview Audio"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>Download</span>
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Advanced Options Accordion */}
            <div className="pt-1">
              <button
                type="button"
                onClick={() => setShowAdvancedDesign(!showAdvancedDesign)}
                className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {showAdvancedDesign ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
                <span>Advanced Options</span>
              </button>

              {showAdvancedDesign && (
                <div className="mt-3 space-y-3 pt-2 border-t border-border">
                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <Label className="text-xs">Pitch Modifier</Label>
                      <span className="font-mono text-xs text-muted-foreground">{designPitch.toFixed(2)}x</span>
                    </div>
                    <Slider
                      value={[designPitch]}
                      min={0.5}
                      max={1.5}
                      step={0.05}
                      onValueChange={(val) => setDesignPitch(val[0])}
                    />
                    <div className="flex justify-between text-[11px] text-muted-foreground">
                      <span>0.5x Lower</span>
                      <span>1.0x Default</span>
                      <span>1.5x Higher</span>
                    </div>
                    {designErrors.pitch && (
                      <p className="text-xs text-destructive mt-1">{designErrors.pitch}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <Label className="text-xs">Pace Modifier</Label>
                      <span className="font-mono text-xs text-muted-foreground">{designSpeed.toFixed(2)}x</span>
                    </div>
                    <Slider
                      value={[designSpeed]}
                      min={0.5}
                      max={1.5}
                      step={0.05}
                      onValueChange={(val) => setDesignSpeed(val[0])}
                    />
                    {designErrors.speed && (
                      <p className="text-xs text-destructive mt-1">{designErrors.speed}</p>
                    )}
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="design-base" className="text-xs">Base Speaker Profile</Label>
                    <select
                      id="design-base"
                      value={designBaseId}
                      onChange={(e) => setDesignBaseId(e.target.value)}
                      className="w-full h-9 px-3 py-1.5 text-xs bg-background border border-input rounded-md text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                    >
                      <option value="">System Default (Automatic)</option>
                      {voices.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.name} ({v.language} - {v.voice_type})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="design-emotion" className="text-xs">Target Emotion</Label>
                    <Input
                      id="design-emotion"
                      value={designEmotion}
                      onChange={(e) => setDesignEmotion(e.target.value)}
                      placeholder="Enter target emotion..."
                      className="h-9 text-xs"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="design-style" className="text-xs">Speech Style</Label>
                    <Input
                      id="design-style"
                      value={designStyle}
                      onChange={(e) => setDesignStyle(e.target.value)}
                      placeholder="Enter speech style..."
                      className="h-9 text-xs"
                    />
                  </div>
                </div>
              )}
            </div>

            {designErrors.general && (
              <p className="text-xs text-destructive">{designErrors.general}</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={closeModal} disabled={isSubmittingDesign}>
              Cancel
            </Button>
            <Button onClick={submitDesign} disabled={isSubmittingDesign}>
              {isSubmittingDesign ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sliders className="h-4 w-4 mr-1.5" />
                  Save Designed Voice
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Voice Modal */}
      <Dialog open={activeModal === "edit"} onOpenChange={closeModal}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>
              Edit Voice {editingVoice ? `— ${editingVoice.name}` : "Profile"}
            </DialogTitle>
            <DialogDescription>
              Update name, description, visibility, or acoustic modifiers for this voice.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <Label htmlFor="edit-name">Voice Name *</Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Voice profile name"
                error={Boolean(editErrors.name)}
              />
              {editErrors.name && (
                <p className="text-xs text-destructive">{editErrors.name}</p>
              )}
            </div>

            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <Label htmlFor="edit-description">Description</Label>
                <span className="text-[11px] text-muted-foreground font-mono">
                  {editDescription.length}/2,000
                </span>
              </div>
              <textarea
                id="edit-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Optional description"
                rows={3}
                maxLength={2000}
                className={`w-full px-3 py-2 text-xs bg-background border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-y min-h-[72px] transition-colors ${
                  editErrors.description ? "border-destructive ring-destructive" : "border-input"
                }`}
              />
              {editErrors.description && (
                <p className="text-xs text-destructive mt-1">{editErrors.description}</p>
              )}
            </div>

            <div className="space-y-1">
              <Label htmlFor="edit-visibility">Visibility</Label>
              <select
                id="edit-visibility"
                value={editVisibility}
                onChange={(e) => setEditVisibility(e.target.value as "public" | "private")}
                className="w-full h-9 px-3 py-1 text-sm bg-background border border-input rounded-md text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="private">Private (Only you can use this voice)</option>
                <option value="public">Public (Visible across the workspace)</option>
              </select>
            </div>

            <div className="space-y-2 pt-2 border-t border-border">
              <div className="flex justify-between items-center text-xs">
                <span className="font-medium">Pitch Multiplier</span>
                <span className="font-mono text-muted-foreground">{editPitch.toFixed(2)}x</span>
              </div>
              <Slider
                value={[editPitch]}
                min={0.5}
                max={1.5}
                step={0.05}
                onValueChange={([val]) => setEditPitch(val)}
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="font-medium">Speed Multiplier</span>
                <span className="font-mono text-muted-foreground">{editSpeed.toFixed(2)}x</span>
              </div>
              <Slider
                value={[editSpeed]}
                min={0.5}
                max={1.5}
                step={0.05}
                onValueChange={([val]) => setEditSpeed(val)}
              />
            </div>

            {editErrors.general && (
              <p className="text-xs text-destructive">{editErrors.general}</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={closeModal} disabled={isSubmittingEdit}>
              Cancel
            </Button>
            <Button onClick={submitEdit} disabled={isSubmittingEdit}>
              {isSubmittingEdit ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={Boolean(deleteConfirmVoice)} onOpenChange={closeDeleteConfirm}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Delete Voice Profile</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{deleteConfirmVoice?.name}&rdquo;? This action will remove the voice profile and cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <Button variant="ghost" onClick={closeDeleteConfirm} disabled={isDeletingVoice}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={submitDelete}
              disabled={isDeletingVoice}
            >
              {isDeletingVoice ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete Voice"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
