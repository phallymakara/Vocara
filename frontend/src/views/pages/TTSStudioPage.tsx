import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Loader2, ChevronDown, ChevronRight, Settings, Copy, Check, Square, X, History, Trash2, RotateCcw, AudioLines } from "lucide-react";
import { useTTSController } from "@/controllers/useTTSController";
import { Slider } from "@/views/components/ui/slider";
import { Progress } from "@/views/components/ui/progress";
import { AudioPlayer } from "@/views/components/AudioPlayer";
import { AnimatedWaveBackground } from "@/views/components/AnimatedWaveBackground";

function estimateAudioLengthLabel(inputText: string, speed: number): string {
  const trimmed = inputText.trim();
  if (!trimmed) return "0s";

  const khmerChars = (trimmed.match(/[\u1780-\u17FF]/g) ?? []).length;
  const nonKhmerChars = trimmed.replace(/[\u1780-\u17FF\s]/g, "").length;
  const pauseCount = (trimmed.match(/[.!?។\n]/g) ?? []).length;

  const baseSeconds = khmerChars / 11 + nonKhmerChars / 13.5 + pauseCount * 0.2;
  const adjustedSeconds = Math.max(1, Math.round(baseSeconds / Math.max(0.5, speed)));

  if (adjustedSeconds < 60) {
    return `~${adjustedSeconds}s`;
  }
  const mins = Math.floor(adjustedSeconds / 60);
  const secs = adjustedSeconds % 60;
  return secs > 0 ? `~${mins}m ${secs}s` : `~${mins}m`;
}

export const TTSStudioPage: React.FC = () => {
  const {
    text,
    setText,
    voices,
    selectedVoiceId,
    setSelectedVoiceId,
    speed,
    setSpeed,
    outputFormat,
    setOutputFormat,
    isLoading,
    generatedAudioUrl,
    audioDuration,
    activeJob,
    textError,
    voiceError,
    generalError,
    charCount,
    history,
    synthesize,
    stopGeneration,
    loadHistoryItem,
    removeHistoryItem,
    clearHistory,
  } = useTTSController();

  const [copiedScript, setCopiedScript] = useState(false);
  const [showAdvancedParams, setShowAdvancedParams] = useState(false);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isFormatModalOpen, setIsFormatModalOpen] = useState(false);

  const voicePickerRef = useRef<HTMLDivElement | null>(null);
  const formatPickerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (isVoiceModalOpen && voicePickerRef.current && !voicePickerRef.current.contains(target)) {
        setIsVoiceModalOpen(false);
      }
      if (isFormatModalOpen && formatPickerRef.current && !formatPickerRef.current.contains(target)) {
        setIsFormatModalOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsVoiceModalOpen(false);
        setIsFormatModalOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isVoiceModalOpen, isFormatModalOpen]);

  const audioFormatOptions: Array<{ value: "mp3" | "wav" | "flac"; label: string }> = [
    { value: "mp3", label: "MP3 (Compressed, 192kbps)" },
    { value: "wav", label: "WAV (Uncompressed, 24kHz PCM)" },
    { value: "flac", label: "FLAC (Lossless)" },
  ];
  const selectedAudioFormatLabel =
    audioFormatOptions.find((f) => f.value === outputFormat)?.label || outputFormat.toUpperCase();

  const selectableVoices = voices.filter((v) => v.voice_type !== "built_in");
  const selectedVoice = selectableVoices.find((v) => v.id === selectedVoiceId) || voices.find((v) => v.id === selectedVoiceId);

  const handleCopyScript = () => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedScript(true);
    setTimeout(() => setCopiedScript(false), 2000);
  };

  return (
    <div className="relative min-h-[calc(100vh-4rem)] pb-12">
      {/* Animated Abstract Wave Background in Top-Right */}
      <AnimatedWaveBackground />

      {/* Main Content Area */}
      <div className="relative z-10 max-w-7xl mx-auto space-y-6 pt-2">
        {/* Workspace 2-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Input Script Card (60-65% width) */}
          <div className="lg:col-span-7 xl:col-span-7 space-y-6">
            <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
              {/* Card Header */}
              <div className="flex items-center justify-between gap-2.5">
                <div className="flex items-center gap-2.5">
                  <div className="text-[#1264F5] flex items-center justify-center flex-shrink-0">
                    <AudioLines className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-bold text-[#15213D] leading-tight">
                    Input Script
                  </h3>
                </div>

                <button
                  type="button"
                  onClick={handleCopyScript}
                  disabled={!text}
                  title="Copy script text"
                  aria-label="Copy script text"
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#E5EBF5] text-xs font-medium text-[#64748B] hover:text-[#15213D] hover:bg-[#F8FAFC] disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer"
                >
                  {copiedScript ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                      <span className="text-emerald-600">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>

              {/* Text Area Container */}
              <div className="space-y-2">
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Enter text in Khmer or English to synthesize..."
                  rows={6}
                  className={`w-full min-h-[170px] md:min-h-[185px] p-4 text-[#15213D] text-sm md:text-base leading-relaxed bg-white border rounded-2xl resize-y transition-all focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 placeholder:text-[#94A3B8] font-normal ${
                    textError ? "border-destructive" : "border-[#E5EBF5]"
                  }`}
                />

                {/* Character Count & Estimated Audio Length Footer */}
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[#7B8CA6] px-1">
                  <div className="flex items-center gap-2 tabular-nums">
                    <span>{charCount} characters</span>
                    <span>&middot;</span>
                    <span>
                      Est. length:{" "}
                      <span className="font-medium text-[#15213D]">
                        {estimateAudioLengthLabel(text, speed)}
                      </span>
                    </span>
                  </div>
                  <span>Max recommended: 5,000</span>
                </div>
              </div>

              {textError && (
                <p className="text-xs text-destructive mt-1">{textError}</p>
              )}
              {generalError && (
                <p className="text-xs text-destructive mt-1">{generalError}</p>
              )}

              {/* Generate Speech & Stop Buttons */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={synthesize}
                  disabled={isLoading}
                  className="bg-[#1264F5] hover:bg-[#0E52CC] active:scale-[0.98] disabled:opacity-60 disabled:pointer-events-none text-white px-7 py-3 rounded-full text-sm font-semibold flex items-center gap-2.5 transition-all cursor-pointer shadow-none"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Synthesizing...</span>
                    </>
                  ) : (
                    <>
                      <AudioLines className="h-4 w-4" />
                      <span>Generate Speech</span>
                    </>
                  )}
                </button>

                {isLoading && (
                  <button
                    type="button"
                    onClick={stopGeneration}
                    className="px-5 py-3 rounded-full border border-[#E5EBF5] bg-white hover:bg-[#F8FAFC] text-[#15213D] text-sm font-semibold flex items-center gap-2 transition-colors cursor-pointer"
                  >
                    <Square className="h-3.5 w-3.5 fill-current text-destructive" />
                    <span>Stop Generate</span>
                  </button>
                )}
              </div>
            </div>

            {/* Asynchronous Background Job Tracker Card */}
            {activeJob && (
              <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-[#15213D]">
                    Background Job #{activeJob.id.slice(0, 8)}
                  </span>
                  <span className="px-2.5 py-1 rounded-full border border-[#E5EBF5] bg-white text-xs font-medium text-[#15213D] capitalize">
                    {activeJob.status}
                  </span>
                </div>
                <Progress
                  value={
                    activeJob.status === "completed"
                      ? 100
                      : activeJob.status === "processing"
                      ? 65
                      : 25
                  }
                  className="h-2 bg-[#E5EBF5]"
                />
                <div className="flex items-center justify-between text-xs text-[#7B8CA6]">
                  <span>Status: {activeJob.status}</span>
                </div>
              </div>
            )}

            {/* Generated Audio Player */}
            {generatedAudioUrl && (
              <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 space-y-3 animate-panel-enter">
                <div className="flex items-center gap-2 text-sm font-semibold text-[#15213D]">
                  <div className="text-[#1264F5] flex items-center justify-center">
                    <AudioLines className="h-4 w-4" />
                  </div>
                  <span>Synthesized Output Audio</span>
                </div>
                <AudioPlayer
                  src={generatedAudioUrl}
                  filename={`vocara_synthesized_speech.${outputFormat}`}
                  duration={audioDuration}
                />
              </div>
            )}

            {/* Generation History Section */}
            <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-[#15213D]">
                  <History className="h-4 w-4 text-[#1264F5]" />
                  <span>Generation History</span>
                  {history.length > 0 && (
                    <span className="text-[11px] font-medium text-[#15213D] border border-[#E5EBF5] bg-white px-2 py-0.5 rounded-full tabular-nums">
                      {history.length}
                    </span>
                  )}
                </div>

                {history.length > 0 && (
                  <button
                    type="button"
                    onClick={clearHistory}
                    className="text-xs font-medium text-[#64748B] hover:text-destructive transition-colors cursor-pointer"
                  >
                    Clear all
                  </button>
                )}
              </div>

              {history.length === 0 ? (
                <div className="py-6 text-center text-xs text-[#64748B] border border-dashed border-[#E5EBF5] rounded-2xl">
                  Generated audio clips from this session will appear here.
                </div>
              ) : (
                <div className="space-y-3">
                  {history.map((item) => {
                    const timeLabel = new Date(item.createdAt).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    });
                    return (
                      <div
                        key={item.id}
                        className="border border-[#E5EBF5] rounded-2xl p-4 space-y-3 bg-[#F8FAFC]/50 animate-panel-enter"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 space-y-1">
                            <div className="flex flex-wrap items-center gap-2 text-xs">
                              <span className="font-semibold text-[#15213D]">
                                {item.voiceName}
                              </span>
                              <span className="px-2 py-0.5 rounded-full bg-white border border-[#E5EBF5] text-[11px] font-medium text-[#64748B] uppercase">
                                {item.outputFormat}
                              </span>
                              <span className="text-[#64748B] tabular-nums">
                                {item.speed.toFixed(2)}x
                              </span>
                              <span className="text-[#94A3B8]">&middot;</span>
                              <span className="text-[#64748B] tabular-nums">{timeLabel}</span>
                            </div>
                            <p className="text-xs text-[#64748B] line-clamp-2 leading-relaxed">
                              {item.text}
                            </p>
                          </div>

                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button
                              type="button"
                              onClick={() => loadHistoryItem(item)}
                              title="Load script and settings"
                              className="h-7 px-2.5 rounded-full border border-[#E5EBF5] bg-white hover:bg-[#F8FAFC] text-[11px] font-medium text-[#15213D] inline-flex items-center gap-1 transition-colors cursor-pointer"
                            >
                              <RotateCcw className="h-3 w-3 text-[#64748B]" />
                              <span>Load</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => removeHistoryItem(item.id)}
                              title="Remove from history"
                              aria-label="Remove from history"
                              className="h-7 w-7 rounded-full border border-[#E5EBF5] bg-white hover:bg-destructive/10 hover:border-destructive/30 text-[#64748B] hover:text-destructive inline-flex items-center justify-center transition-colors cursor-pointer"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        </div>

                        <AudioPlayer
                          src={item.audioUrl}
                          filename={`vocara_${item.id.slice(0, 8)}.${item.outputFormat}`}
                          duration={item.duration}
                        />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Voice Parameters Card (35-40% width) */}
          <div className="lg:col-span-5 xl:col-span-5 space-y-6">
            <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
              {/* Card Header */}
              <div className="flex items-center gap-2.5">
                <div className="text-[#1264F5] flex items-center justify-center flex-shrink-0">
                  <Settings className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-[#15213D] leading-tight">
                  Voice Parameters
                </h3>
              </div>

              {/* Parameter Form Controls */}
              <div className="space-y-4 pt-1">
                {/* 1. Speaker Voice Anchored Selector */}
                <div className="space-y-1.5 relative" ref={voicePickerRef}>
                  <label
                    htmlFor="speaker-voice-trigger"
                    className="text-xs font-semibold text-[#15213D] block"
                  >
                    Speaker Voice
                  </label>

                  <button
                    id="speaker-voice-trigger"
                    type="button"
                    aria-expanded={isVoiceModalOpen}
                    onClick={() => {
                      setIsFormatModalOpen(false);
                      setIsVoiceModalOpen((prev) => !prev);
                    }}
                    className={`relative w-full h-11 px-4 pr-10 text-left text-sm font-normal bg-white border rounded-xl text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 cursor-pointer transition-all truncate ${
                      voiceError ? "border-destructive" : "border-[#E5EBF5]"
                    }`}
                  >
                    {selectedVoice ? (
                      <span>
                        {selectedVoice.name} &middot; {selectedVoice.voice_type}
                      </span>
                    ) : (
                      <span className="text-[#94A3B8]">Select speaker voice...</span>
                    )}
                    <ChevronDown className="absolute right-3.5 top-3.5 h-4 w-4 text-[#7B8CA6] pointer-events-none" />
                  </button>

                  {isVoiceModalOpen && (
                    <div
                      role="dialog"
                      aria-label="Select Speaker Voice"
                      className="absolute left-0 right-0 top-full mt-2 z-50 bg-white border border-[#E5EBF5] rounded-2xl p-3 space-y-2.5"
                    >
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-semibold text-[#15213D]">
                          Select Speaker Voice
                        </span>
                        <button
                          type="button"
                          onClick={() => setIsVoiceModalOpen(false)}
                          className="text-[#7B8CA6] hover:text-[#15213D] p-1 rounded-lg cursor-pointer"
                          aria-label="Close speaker voice selector"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <div className="max-h-64 overflow-y-auto space-y-1.5 pr-0.5">
                        {selectableVoices.length === 0 ? (
                          <p className="text-xs text-[#7B8CA6] py-4 text-center">
                            No voices available.{" "}
                            <Link to="/voices?action=clone" className="text-[#1264F5] underline">
                              Clone a voice
                            </Link>{" "}
                            to get started.
                          </p>
                        ) : (
                          selectableVoices.map((v) => {
                            const isSelected = v.id === selectedVoiceId;
                            return (
                              <button
                                key={v.id}
                                type="button"
                                onClick={() => {
                                  setSelectedVoiceId(v.id);
                                  setIsVoiceModalOpen(false);
                                }}
                                className={`w-full flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-xl border text-left transition-colors cursor-pointer ${
                                  isSelected
                                    ? "border-[#1264F5] bg-[#1264F5] text-white"
                                    : "border-[#E5EBF5] bg-white text-[#15213D] hover:border-[#CBD5E1]"
                                }`}
                              >
                                <div className="min-w-0">
                                  <div className="text-sm font-medium truncate">
                                    {v.name}{" "}
                                    <span
                                      className={`text-xs font-normal ${
                                        isSelected ? "text-white/80" : "text-[#7B8CA6]"
                                      }`}
                                    >
                                      &middot; {v.voice_type}
                                    </span>
                                  </div>
                                </div>
                                {isSelected && <Check className="h-4 w-4 text-white flex-shrink-0" />}
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>
                  )}

                  {selectableVoices.length === 0 && (
                    <p className="text-[11px] text-[#7B8CA6] mt-1">
                      No voices available.{" "}
                      <Link
                        to="/voices?action=clone"
                        className="text-[#1264F5] underline"
                      >
                        Clone a voice
                      </Link>{" "}
                      to begin.
                    </p>
                  )}
                  {voiceError && (
                    <p className="text-xs text-destructive mt-1">{voiceError}</p>
                  )}
                </div>

                {/* 2. Audio Format Anchored Selector */}
                <div className="space-y-1.5 relative" ref={formatPickerRef}>
                  <label
                    htmlFor="audio-format-trigger"
                    className="text-xs font-semibold text-[#15213D] block"
                  >
                    Audio Format
                  </label>
                  <button
                    id="audio-format-trigger"
                    type="button"
                    aria-expanded={isFormatModalOpen}
                    onClick={() => {
                      setIsVoiceModalOpen(false);
                      setIsFormatModalOpen((prev) => !prev);
                    }}
                    className="relative w-full h-11 px-4 pr-10 text-left text-sm font-normal bg-white border border-[#E5EBF5] rounded-xl text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 cursor-pointer transition-all truncate"
                  >
                    <span>{selectedAudioFormatLabel}</span>
                    <ChevronDown className="absolute right-3.5 top-3.5 h-4 w-4 text-[#7B8CA6] pointer-events-none" />
                  </button>

                  {isFormatModalOpen && (
                    <div
                      role="dialog"
                      aria-label="Select Audio Format"
                      className="absolute left-0 right-0 top-full mt-2 z-50 bg-white border border-[#E5EBF5] rounded-2xl p-3 space-y-2.5"
                    >
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-semibold text-[#15213D]">
                          Select Audio Format
                        </span>
                        <button
                          type="button"
                          onClick={() => setIsFormatModalOpen(false)}
                          className="text-[#7B8CA6] hover:text-[#15213D] p-1 rounded-lg cursor-pointer"
                          aria-label="Close audio format selector"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <div className="space-y-1.5">
                        {audioFormatOptions.map((opt) => {
                          const isSelected = opt.value === outputFormat;
                          return (
                            <button
                              key={opt.value}
                              type="button"
                              onClick={() => {
                                setOutputFormat(opt.value);
                                setIsFormatModalOpen(false);
                              }}
                              className={`w-full flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-xl border text-left transition-colors cursor-pointer ${
                                isSelected
                                  ? "border-[#1264F5] bg-[#1264F5] text-white"
                                  : "border-[#E5EBF5] bg-white text-[#15213D] hover:border-[#CBD5E1]"
                              }`}
                            >
                              <span className="text-sm font-medium">{opt.label}</span>
                              {isSelected && <Check className="h-4 w-4 text-white flex-shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* 3. Advanced Options (Speaking Rate) */}
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={() => setShowAdvancedParams(!showAdvancedParams)}
                    className="flex items-center gap-1.5 text-xs font-medium text-[#7B8CA6] hover:text-[#15213D] transition-colors cursor-pointer"
                  >
                    {showAdvancedParams ? (
                      <ChevronDown className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5" />
                    )}
                    <span>Advanced Options</span>
                  </button>

                  {showAdvancedParams && (
                    <div className="mt-3 space-y-4 pt-3 border-t border-[#E5EBF5]">
                      {/* Speaking Rate Slider */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <label className="font-semibold text-[#15213D]">
                            Speaking Rate
                          </label>
                          <span className="font-bold font-mono text-sm text-[#1264F5]">
                            {speed.toFixed(2)}x
                          </span>
                        </div>

                        <Slider
                          value={[speed]}
                          min={0.5}
                          max={2.0}
                          step={0.05}
                          onValueChange={(val) => setSpeed(val[0])}
                          className="py-1"
                        />

                        <div className="flex justify-between text-[11px] text-[#7B8CA6] pt-0.5">
                          <span>0.5x Slow</span>
                          <span>1.0x Normal</span>
                          <span>2.0x Fast</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TTSStudioPage;
