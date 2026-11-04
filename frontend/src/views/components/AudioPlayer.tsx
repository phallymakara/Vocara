import React, { useRef, useState, useEffect } from "react";
import { Play, Pause, Download, Volume2 } from "lucide-react";
import { Button } from "@/views/components/ui/button";
import { Slider } from "@/views/components/ui/slider";

interface AudioPlayerProps {
  src: string;
  filename?: string;
  duration?: number;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  src,
  filename = "vocara_speech.mp3",
  duration: initialDuration,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalDuration, setTotalDuration] = useState(initialDuration || 0);

  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    if (initialDuration) {
      setTotalDuration(initialDuration);
    }
  }, [src, initialDuration]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  };

  const onTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      if (audioRef.current.duration && !isNaN(audioRef.current.duration)) {
        setTotalDuration(audioRef.current.duration);
      }
    }
  };

  const onEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handleSeek = (values: number[]) => {
    const time = values[0];
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  return (
    <div className="flex items-center gap-4 p-4 border border-border rounded-lg bg-background">
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={onTimeUpdate}
        onEnded={onEnded}
        onLoadedMetadata={() => {
          if (audioRef.current?.duration) {
            setTotalDuration(audioRef.current.duration);
          }
        }}
      />

      <Button
        type="button"
        size="icon"
        variant="default"
        onClick={togglePlay}
        className="h-10 w-10 rounded-full flex-shrink-0"
        title={isPlaying ? "Pause" : "Play"}
      >
        {isPlaying ? (
          <Pause className="h-4 w-4" />
        ) : (
          <Play className="h-4 w-4 ml-0.5" />
        )}
      </Button>

      <div className="flex items-center gap-3 flex-1">
        <span className="text-xs font-mono text-muted-foreground w-10 text-right">
          {formatTime(currentTime)}
        </span>
        <div className="flex-1">
          <Slider
            value={[currentTime]}
            max={totalDuration > 0 ? totalDuration : 1}
            step={0.1}
            onValueChange={handleSeek}
          />
        </div>
        <span className="text-xs font-mono text-muted-foreground w-10">
          {formatTime(totalDuration)}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Volume2 className="h-4 w-4 text-muted-foreground" />
        <a
          href={src}
          download={filename}
          className="inline-flex items-center justify-center h-9 px-3 rounded-md border border-input text-xs font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
          title="Download Audio"
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          <span>Download</span>
        </a>
      </div>
    </div>
  );
};

