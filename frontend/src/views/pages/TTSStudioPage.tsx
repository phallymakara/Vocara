import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Loader2, ChevronDown, ChevronRight, Settings, Copy, Check, Square, X } from "lucide-react";
import { useTTSController } from "@/controllers/useTTSController";
import { Slider } from "@/views/components/ui/slider";
import { Progress } from "@/views/components/ui/progress";
import { AudioPlayer } from "@/views/components/AudioPlayer";
import { AnimatedWaveBackground } from "@/views/components/AnimatedWaveBackground";

export const TTSStudioPage: React.FC = () => {
  const {
    text,
    setText,
    voices,
    languages,
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
    textError,
    voiceError,
    generalError,
    charCount,
    synthesize,
    stopGeneration,
  } = useTTSController();

  const [copiedScript, setCopiedScript] = useState(false);
  const [showAdvancedParams, setShowAdvancedParams] = useState(false);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isLangModalOpen, setIsLangModalOpen] = useState(false);

  const voicePickerRef = useRef<HTMLDivElement | null>(null);
  const langPickerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (isVoiceModalOpen && voicePickerRef.current && !voicePickerRef.current.contains(target)) {
        setIsVoiceModalOpen(false);
      }
      if (isLangModalOpen && langPickerRef.current && !langPickerRef.current.contains(target)) {
        setIsLangModalOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsVoiceModalOpen(false);
        setIsLangModalOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isVoiceModalOpen, isLangModalOpen]);

  const selectedVoice = voices.find((v) => v.id === selectedVoiceId);
  const languageOptions = React.useMemo(() => {
    const base =
      languages.length > 0
        ? languages.map((l) => ({ code: l.code, label: `${l.name} (${l.code})` }))
        : [
            { code: "km-KH", label: "Khmer (km-KH)" },
            { code: "en-US", label: "English (en-US)" },
          ];
    if (!base.some((o) => o.code === "mixed")) {
      base.push({ code: "mixed", label: "Mixed (Khmer & English)" });
    }
    return base;
  }, [languages]);
  const selectedLanguageLabel =
    languageOptions.find((l) => l.code === language)?.label || language;

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
                    {/* Audio Waveform Icon */}
                    <svg
                      className="h-5 w-5"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path d="M12 3a1 1 0 0 1 1 1v16a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1zm-4 4a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1zm8 0a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1zm-12 3a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1zm16 0a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1z" />
                    </svg>
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

                {/* Character Count Footer outside textarea */}
                <div className="flex items-center justify-between text-xs text-[#7B8CA6] px-1">
                  <span>{charCount} characters</span>
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
                      {/* Audio waveform button icon */}
                      <svg
                        className="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        aria-hidden="true"
                      >
                        <path d="M12 3a1 1 0 0 1 1 1v16a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1zm-4 4a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1zm8 0a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1zm-12 3a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1zm16 0a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1z" />
                      </svg>
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
                  <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#EBF2FE] text-[#1264F5] capitalize">
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
                  <Link
                    to={`/jobs?job_id=${encodeURIComponent(activeJob.id)}`}
                    className="text-[#1264F5] hover:underline font-medium"
                  >
                    View in Jobs & Webhooks &rarr;
                  </Link>
                </div>
              </div>
            )}

            {/* Generated Audio Player */}
            {generatedAudioUrl && (
              <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 space-y-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-[#15213D]">
                  <div className="text-[#1264F5] flex items-center justify-center">
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 3a1 1 0 0 1 1 1v16a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1zm-4 4a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1zm8 0a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1z" />
                    </svg>
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
                      setIsLangModalOpen(false);
                      setIsVoiceModalOpen((prev) => !prev);
                    }}
                    className={`relative w-full h-11 px-4 pr-10 text-left text-sm font-normal bg-[#F8FAFC] border rounded-xl text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 cursor-pointer transition-all truncate ${
                      voiceError ? "border-destructive" : "border-[#E5EBF5]"
                    }`}
                  >
                    {selectedVoice ? (
                      <span>
                        {selectedVoice.name} ({selectedVoice.language} - {selectedVoice.voice_type})
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
                        {voices.length === 0 ? (
                          <p className="text-xs text-[#7B8CA6] py-4 text-center">
                            No voices available.{" "}
                            <Link to="/voices?action=clone" className="text-[#1264F5] underline">
                              Clone a voice
                            </Link>{" "}
                            to get started.
                          </p>
                        ) : (
                          voices.map((v) => {
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
                                    ? "border-[#1264F5] text-[#15213D]"
                                    : "border-[#E5EBF5] text-[#15213D] hover:border-[#CBD5E1]"
                                }`}
                              >
                                <div className="min-w-0">
                                  <div className="text-sm font-medium truncate">
                                    {v.name}{" "}
                                    <span className="text-xs font-normal text-[#7B8CA6]">
                                      ({v.language} - {v.voice_type})
                                    </span>
                                  </div>
                                  {v.description && (
                                    <p className="text-xs text-[#7B8CA6] truncate mt-0.5">
                                      {v.description}
                                    </p>
                                  )}
                                </div>
                                {isSelected && <Check className="h-4 w-4 text-[#1264F5] flex-shrink-0" />}
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>
                  )}

                  {voices.length === 0 && (
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

                {/* 2. Language Code Anchored Selector */}
                <div className="space-y-1.5 relative" ref={langPickerRef}>
                  <label
                    htmlFor="language-code-trigger"
                    className="text-xs font-semibold text-[#15213D] block"
                  >
                    Language Code
                  </label>
                  <button
                    id="language-code-trigger"
                    type="button"
                    aria-expanded={isLangModalOpen}
                    onClick={() => {
                      setIsVoiceModalOpen(false);
                      setIsLangModalOpen((prev) => !prev);
                    }}
                    className="relative w-full h-11 px-4 pr-10 text-left text-sm font-normal bg-[#F8FAFC] border border-[#E5EBF5] rounded-xl text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 cursor-pointer transition-all truncate"
                  >
                    <span>{selectedLanguageLabel}</span>
                    <ChevronDown className="absolute right-3.5 top-3.5 h-4 w-4 text-[#7B8CA6] pointer-events-none" />
                  </button>

                  {isLangModalOpen && (
                    <div
                      role="dialog"
                      aria-label="Select Language"
                      className="absolute left-0 right-0 top-full mt-2 z-50 bg-white border border-[#E5EBF5] rounded-2xl p-3 space-y-2.5"
                    >
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-semibold text-[#15213D]">
                          Select Language
                        </span>
                        <button
                          type="button"
                          onClick={() => setIsLangModalOpen(false)}
                          className="text-[#7B8CA6] hover:text-[#15213D] p-1 rounded-lg cursor-pointer"
                          aria-label="Close language selector"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <div className="space-y-1.5">
                        {languageOptions.map((opt) => {
                          const isSelected = opt.code === language;
                          return (
                            <button
                              key={opt.code}
                              type="button"
                              onClick={() => {
                                setLanguage(opt.code);
                                setIsLangModalOpen(false);
                              }}
                              className={`w-full flex items-center justify-between gap-2.5 px-3 py-2.5 rounded-xl border text-left transition-colors cursor-pointer ${
                                isSelected
                                  ? "border-[#1264F5] text-[#15213D]"
                                  : "border-[#E5EBF5] text-[#15213D] hover:border-[#CBD5E1]"
                              }`}
                            >
                              <span className="text-sm font-medium">{opt.label}</span>
                              {isSelected && <Check className="h-4 w-4 text-[#1264F5] flex-shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* 3. Advanced Options (Speaking Rate & Audio Format) */}
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

                      {/* Audio Format Dropdown */}
                      <div className="space-y-1.5">
                        <label
                          htmlFor="audio-format"
                          className="text-xs font-semibold text-[#15213D] block"
                        >
                          Audio Format
                        </label>
                        <div className="relative">
                          <select
                            id="audio-format"
                            value={outputFormat}
                            onChange={(e) =>
                              setOutputFormat(e.target.value as "mp3" | "wav" | "flac")
                            }
                            className="w-full h-11 px-4 pr-10 text-sm font-normal bg-[#F8FAFC] border border-[#E5EBF5] rounded-xl text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 appearance-none cursor-pointer transition-all"
                          >
                            <option value="mp3">MP3 (Compressed, 192kbps)</option>
                            <option value="wav">WAV (Uncompressed, 24kHz PCM)</option>
                            <option value="flac">FLAC (Lossless)</option>
                          </select>
                          <ChevronDown className="absolute right-3.5 top-3.5 h-4 w-4 text-[#7B8CA6] pointer-events-none" />
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
