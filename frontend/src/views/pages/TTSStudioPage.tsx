import React from "react";
import { Link } from "react-router-dom";
import { Zap, Clock, Loader2, ChevronDown, Settings } from "lucide-react";
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
    isAsyncMode,
    synthesize,
  } = useTTSController();

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
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-2xl bg-[#EBF2FE] text-[#1264F5] flex items-center justify-center flex-shrink-0">
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
                  <div>
                    <h3 className="text-base font-bold text-[#15213D] leading-tight">
                      Input Script
                    </h3>
                    <p className="text-xs text-[#7B8CA6] mt-0.5">
                      Enter text in Khmer or English to generate speech.
                    </p>
                  </div>
                </div>

                {/* Direct Stream / Async Pill */}
                <div
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium border ${
                    isAsyncMode
                      ? "bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]"
                      : "bg-[#FEF6EB] text-[#D97706] border-[#FDE68A]/70"
                  }`}
                >
                  {isAsyncMode ? (
                    <>
                      <Clock className="h-3.5 w-3.5 text-[#64748B]" />
                      <span>Async Job (250+ chars)</span>
                    </>
                  ) : (
                    <>
                      <Zap className="h-3.5 w-3.5 text-[#F59E0B] fill-[#F59E0B]" />
                      <span>Direct Stream (&lt;250 chars)</span>
                    </>
                  )}
                </div>
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

              {/* Generate Speech Button */}
              <div>
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
                  <div className="w-8 h-8 rounded-xl bg-[#EBF2FE] text-[#1264F5] flex items-center justify-center">
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 3a1 1 0 0 1 1 1v16a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1zm-4 4a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1zm8 0a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V8a1 1 0 0 1 1-1z" />
                    </svg>
                  </div>
                  <span>Synthesized Output Audio</span>
                </div>
                <AudioPlayer
                  src={generatedAudioUrl}
                  filename="vocara_synthesized_speech.mp3"
                  duration={audioDuration}
                />
              </div>
            )}
          </div>

          {/* Right Column: Voice Parameters Card (35-40% width) */}
          <div className="lg:col-span-5 xl:col-span-5 space-y-6">
            <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
              {/* Card Header */}
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-[#EBF2FE] text-[#1264F5] flex items-center justify-center flex-shrink-0">
                  <Settings className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#15213D] leading-tight">
                    Voice Parameters
                  </h3>
                  <p className="text-xs text-[#7B8CA6] mt-0.5">
                    Configure speaker voice and acoustic profile.
                  </p>
                </div>
              </div>

              {/* Parameter Form Controls */}
              <div className="space-y-4 pt-1">
                {/* 1. Speaker Voice Dropdown */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="speaker-voice"
                    className="text-xs font-semibold text-[#15213D] block"
                  >
                    Speaker Voice
                  </label>

                  <div className="relative">
                    <select
                      id="speaker-voice"
                      value={selectedVoiceId}
                      onChange={(e) => setSelectedVoiceId(e.target.value)}
                      className={`w-full h-11 px-4 pr-10 text-sm font-normal bg-[#F8FAFC] border rounded-xl text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 appearance-none cursor-pointer transition-all ${
                        voiceError ? "border-destructive" : "border-[#E5EBF5]"
                      }`}
                    >
                      <option value="" disabled>
                        Select speaker voice...
                      </option>
                      {voices.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.name} ({v.language} - {v.voice_type})
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3.5 top-3.5 h-4 w-4 text-[#7B8CA6] pointer-events-none" />
                  </div>

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

                {/* 2. Language Code Dropdown */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="language-code"
                    className="text-xs font-semibold text-[#15213D] block"
                  >
                    Language Code
                  </label>
                  <div className="relative">
                    <select
                      id="language-code"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full h-11 px-4 pr-10 text-sm font-normal bg-[#F8FAFC] border border-[#E5EBF5] rounded-xl text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 appearance-none cursor-pointer transition-all"
                    >
                      <option value="km-KH">Khmer (km-KH)</option>
                      <option value="en-US">English (en-US)</option>
                      <option value="mixed">Mixed (Khmer & English)</option>
                    </select>
                    <ChevronDown className="absolute right-3.5 top-3.5 h-4 w-4 text-[#7B8CA6] pointer-events-none" />
                  </div>
                </div>

                {/* 3. Speaking Rate Slider */}
                <div className="space-y-2 pt-1">
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

                {/* 4. Audio Format Dropdown */}
                <div className="space-y-1.5 pt-1">
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TTSStudioPage;
