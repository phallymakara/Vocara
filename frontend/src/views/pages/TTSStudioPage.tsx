import React from "react";
import { Mic, Zap, Clock, Loader2, Sparkles } from "lucide-react";
import { useTTSController } from "@/controllers/useTTSController";
import { Button } from "@/views/components/ui/button";
import { Textarea } from "@/views/components/ui/textarea";
import { Label } from "@/views/components/ui/label";
import { Badge } from "@/views/components/ui/badge";
import { Slider } from "@/views/components/ui/slider";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/views/components/ui/card";
import { Progress } from "@/views/components/ui/progress";
import { AudioPlayer } from "@/views/components/AudioPlayer";

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
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Text-to-Speech Studio
        </h2>
        <p className="text-sm text-muted-foreground">
          High-fidelity neural voice synthesis with native Khmer and English support.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Text Input & Synthesizer */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Input Script</CardTitle>
                  <CardDescription>
                    Enter text in Khmer or English to generate speech.
                  </CardDescription>
                </div>
                <Badge variant={isAsyncMode ? "secondary" : "outline"} className="gap-1 text-xs">
                  {isAsyncMode ? (
                    <>
                      <Clock className="h-3 w-3" />
                      <span>Async Job (250+ chars)</span>
                    </>
                  ) : (
                    <>
                      <Zap className="h-3 w-3 text-amber-500" />
                      <span>Direct Stream (&lt;250 chars)</span>
                    </>
                  )}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="space-y-3">
              <div className="space-y-1">
                <Textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Enter script text to synthesize..."
                  className="min-h-[160px] resize-y font-normal"
                  error={Boolean(textError)}
                />
                <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                  <span>
                    {charCount} characters
                  </span>
                  <span>Max recommended: 5,000</span>
                </div>
                {textError && (
                  <p className="text-xs text-destructive mt-1">{textError}</p>
                )}
              </div>

              {generalError && (
                <p className="text-xs text-destructive">{generalError}</p>
              )}

              <div className="pt-2">
                <Button
                  onClick={synthesize}
                  disabled={isLoading}
                  className="w-full sm:w-auto"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Synthesizing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Generate Speech
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Job In-Progress Indicator */}
          {activeJob && (
            <Card>
              <CardContent className="pt-6 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Background Job #{activeJob.id.slice(0, 8)}</span>
                  <Badge variant={activeJob.status === "completed" ? "default" : "secondary"}>
                    {activeJob.status}
                  </Badge>
                </div>
                <Progress
                  value={activeJob.status === "completed" ? 100 : activeJob.status === "processing" ? 60 : 25}
                  className="h-2"
                />
                <p className="text-xs text-muted-foreground">
                  Status: {activeJob.status}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Audio Result Player */}
          {generatedAudioUrl && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Mic className="h-4 w-4 text-sky-600" />
                <span>Generated Output</span>
              </div>
              <AudioPlayer
                src={generatedAudioUrl}
                filename="synthesized_speech.mp3"
                duration={audioDuration}
              />
            </div>
          )}
        </div>

        {/* Right 1 Col: Voice & Audio Settings */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Voice Parameters</CardTitle>
              <CardDescription>Configure speaker voice and acoustic profile.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Voice Selector */}
              <div className="space-y-1.5">
                <Label htmlFor="voice-select">Speaker Voice</Label>
                <select
                  id="voice-select"
                  value={selectedVoiceId}
                  onChange={(e) => setSelectedVoiceId(e.target.value)}
                  className={`w-full h-10 px-3 py-2 text-sm bg-background border rounded-md text-foreground focus:outline-none focus:ring-1 focus:ring-ring ${
                    voiceError ? "border-destructive focus:ring-destructive" : "border-input"
                  }`}
                >
                  <option value="" disabled>Select speaker voice...</option>
                  {voices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} ({v.language} - {v.voice_type})
                    </option>
                  ))}
                </select>
                {voiceError && (
                  <p className="text-xs text-destructive mt-1">{voiceError}</p>
                )}
              </div>

              {/* Language */}
              <div className="space-y-1.5">
                <Label htmlFor="language-select">Language Code</Label>
                <select
                  id="language-select"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full h-10 px-3 py-2 text-sm bg-background border border-input rounded-md text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="km-KH">Khmer (km-KH)</option>
                  <option value="en-US">English (en-US)</option>
                </select>
              </div>

              {/* Speech Speed */}
              <div className="space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <Label>Speaking Rate</Label>
                  <span className="font-mono text-xs text-muted-foreground">{speed.toFixed(2)}x</span>
                </div>
                <Slider
                  value={[speed]}
                  min={0.5}
                  max={2.0}
                  step={0.05}
                  onValueChange={(val) => setSpeed(val[0])}
                />
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>0.5x Slow</span>
                  <span>1.0x Normal</span>
                  <span>2.0x Fast</span>
                </div>
              </div>

              {/* Audio Format */}
              <div className="space-y-1.5">
                <Label htmlFor="format-select">Audio Format</Label>
                <select
                  id="format-select"
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value as "mp3" | "wav" | "flac")}
                  className="w-full h-10 px-3 py-2 text-sm bg-background border border-input rounded-md text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="mp3">MP3 (Compressed, 192kbps)</option>
                  <option value="wav">WAV (Uncompressed, 24kHz PCM)</option>
                  <option value="flac">FLAC (Lossless)</option>
                </select>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
