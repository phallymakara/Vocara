import React from "react";
import { Link } from "react-router-dom";
import { Plus, Sliders, Play, Pause, Upload, Loader2, ChevronDown, ChevronRight, Copy, Check, Edit2, Trash2, Mic } from "lucide-react";
import { useVoiceController } from "@/controllers/useVoiceController";
import { Button } from "@/views/components/ui/button";
import { Input } from "@/views/components/ui/input";
import { Label } from "@/views/components/ui/label";
import { Badge } from "@/views/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/views/components/ui/card";
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
    activeModal,
    openCloneModal,
    openDesignModal,
    openEditModal,
    closeModal,
    cloneName,
    setCloneName,
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
  } = useVoiceController();

  const [copiedVoiceId, setCopiedVoiceId] = React.useState<string | null>(null);

  const handleCopyVoiceId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedVoiceId(id);
    setTimeout(() => setCopiedVoiceId(null), 2000);
  };

  const filteredVoices = voices.filter((v) => {
    if (filterLang === "all") return true;
    return v.language === filterLang;
  });

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Voice Library
          </h2>
          <p className="text-sm text-muted-foreground">
            Explore built-in speakers, clone custom voices with consent, or design acoustic variations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={openDesignModal}>
            <Sliders className="h-4 w-4 mr-1.5" />
            Design Voice
          </Button>
          <Button size="sm" onClick={openCloneModal}>
            <Plus className="h-4 w-4 mr-1.5" />
            Clone Voice
          </Button>
        </div>
      </div>

      {/* Language Filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground font-medium">Filter language:</span>
        <div className="flex gap-1.5">
          {[
            { id: "all", label: "All Voices" },
            { id: "km-KH", label: "Khmer (km-KH)" },
            { id: "en-US", label: "English (en-US)" },
          ].map((tab) => (
            <Button
              key={tab.id}
              variant={filterLang === tab.id ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setFilterLang(tab.id)}
              className="text-xs h-7 px-2.5"
            >
              {tab.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Voice Grid */}
      {isLoading ? (
        <div className="py-12 flex justify-center items-center text-muted-foreground text-sm">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          Loading voices...
        </div>
      ) : filteredVoices.length === 0 ? (
        <div className="py-12 text-center text-muted-foreground text-sm border border-dashed rounded-lg">
          No voices found for this filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredVoices.map((voice) => {
            const isPlaying = playingVoiceId === voice.id;
            return (
              <Card key={voice.id} className="relative">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-base">{voice.name}</CardTitle>
                      <CardDescription className="text-xs mt-0.5">
                        {voice.language} • {voice.visibility}
                      </CardDescription>
                    </div>
                    <Badge
                      variant={
                        voice.voice_type === "cloned"
                          ? "default"
                          : voice.voice_type === "designed"
                          ? "secondary"
                          : "outline"
                      }
                      className="text-[11px] capitalize"
                    >
                      {voice.voice_type.replace("_", " ")}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-2">
                  <p className="text-xs text-muted-foreground line-clamp-2 min-h-[32px]">
                    {voice.description || "High-clarity neural acoustic profile for production synthesis."}
                  </p>
                  <p
                    className="text-[11px] text-muted-foreground/80 font-mono truncate"
                    title={
                      voice.language.startsWith("en")
                        ? "Sample phrase: Hello, I am Vocara, an AI text-to-speech converter."
                        : "Sample phrase: សួស្តីខ្ញុំជាវូការាជាអេអាយបម្លែងអក្សរទៅជាសម្លេង"
                    }
                  >
                    Preview: &ldquo;
                    {voice.language.startsWith("en")
                      ? "Hello, I am Vocara..."
                      : "សួស្តីខ្ញុំជាវូការា..."}
                    &rdquo;
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-border">
                    <button
                      type="button"
                      onClick={() => handleCopyVoiceId(voice.id)}
                      className="inline-flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground hover:text-foreground transition-colors group cursor-pointer"
                      title="Click to copy Voice ID for MCP or API"
                    >
                      <span>ID: {voice.id.slice(0, 14)}...</span>
                      {copiedVoiceId === voice.id ? (
                        <Check className="h-3 w-3 text-emerald-600" />
                      ) : (
                        <Copy className="h-3 w-3 opacity-60 group-hover:opacity-100 transition-opacity" />
                      )}
                    </button>
                    <div className="flex items-center gap-1.5">
                      {voice.voice_type !== "built_in" && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditModal(voice)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                            title="Edit Voice"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openDeleteConfirm(voice)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                            title="Delete Voice"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </>
                      )}
                      <Button
                        variant={isPlaying ? "default" : "outline"}
                        size="sm"
                        onClick={() => togglePreview(voice.id)}
                        className="h-8 text-xs gap-1.5"
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
                      </Button>
                      <Link
                        to={`/?voice=${encodeURIComponent(voice.id)}`}
                        className="inline-flex items-center justify-center h-8 px-2.5 text-xs font-medium rounded border border-input bg-background hover:bg-slate-100 dark:hover:bg-slate-800 text-sky-600 hover:text-sky-700 transition-colors gap-1"
                        title="Use this voice in TTS Studio"
                      >
                        <Mic className="h-3.5 w-3.5" />
                        <span>Use</span>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
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
                  onClick={() => setClonePromptText("សួស្តីខ្ញុំជាវូការាជាអេអាយបម្លែងអក្សរទៅជាសម្លេង")}
                  className="text-[11px] text-primary hover:underline font-normal cursor-pointer"
                >
                  Use this script
                </button>
              </div>
              <p className="text-muted-foreground select-all font-sans font-medium">
                &ldquo;សួស្តីខ្ញុំជាវូការាជាអេអាយបម្លែងអក្សរទៅជាសម្លេង&rdquo;
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
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Acoustic Voice Design</DialogTitle>
            <DialogDescription>
              Derive a new voice profile by adjusting acoustic pitch and speaking pace modifiers.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
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

            <div className="space-y-1">
              <Label htmlFor="design-desc">Description</Label>
              <Input
                id="design-desc"
                value={designDescription}
                onChange={(e) => setDesignDescription(e.target.value)}
                placeholder="Enter voice description..."
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <Label>Pitch Modifier</Label>
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
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <Label>Pace Modifier</Label>
                <span className="font-mono text-xs text-muted-foreground">{designSpeed.toFixed(2)}x</span>
              </div>
              <Slider
                value={[designSpeed]}
                min={0.5}
                max={1.5}
                step={0.05}
                onValueChange={(val) => setDesignSpeed(val[0])}
              />
            </div>

            <div className="rounded border border-border bg-muted/20 p-2.5 text-xs space-y-1">
              <span className="font-medium text-foreground">Preview Phrase:</span>
              <p className="text-muted-foreground select-all font-sans font-medium">
                &ldquo;សួស្តីខ្ញុំជាវូការាជាអេអាយបម្លែងអក្សរទៅជាសម្លេង&rdquo;
              </p>
              <p className="text-[11px] text-muted-foreground">
                The designed acoustic variation will be automatically previewed using this phrase.
              </p>
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
              <Label htmlFor="edit-description">Description</Label>
              <Input
                id="edit-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Optional description"
              />
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
