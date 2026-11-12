import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTTSContext } from "@/controllers/TTSContext";

export function useTTSController() {
  const [searchParams, setSearchParams] = useSearchParams();
  const voiceParam = searchParams.get("voice");
  const ctx = useTTSContext();

  useEffect(() => {
    if (voiceParam) {
      ctx.selectVoiceFromParam(voiceParam);
    }
  }, [voiceParam, ctx.voices]);

  const setSelectedVoiceId = (id: string) => {
    ctx.setSelectedVoiceId(id);
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

  return {
    ...ctx,
    setSelectedVoiceId,
  };
}
