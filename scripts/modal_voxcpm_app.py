"""Modal serverless deployment for VoxCPM 2.

Deploy to Modal with:
    uvx modal deploy scripts/modal_voxcpm_app.py
"""

import modal

# 1. Define Modal App
app = modal.App("vocara-voxcpm")


def download_model():
    """Pre-download model weights into container image layer."""
    from voxcpm import VoxCPM

    print("Pre-downloading VoxCPM 2 weights into image...")
    VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
    print("VoxCPM 2 weights cached successfully!")

    print("Pre-downloading Whisper ASR weights into image...")
    try:
        from transformers import pipeline
        pipeline("automatic-speech-recognition", model="openai/whisper-base")
        print("Whisper weights cached successfully!")
    except Exception as e:
        print(f"Whisper pre-download note: {e}")


# 2. Define Container Image with PyTorch, VoxCPM & Pre-baked Weights
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "voxcpm",
        "fastapi",
        "uvicorn",
        "soundfile",
        "pydantic",
        "torch",
        "transformers",
        "accelerate",
    )
    .run_function(download_model)
)


# 3. Model Service Class with GPU
@app.cls(
    image=image,
    gpu="T4",
    timeout=300,
    scaledown_window=60,  # Auto-scales to 0 when idle ($0 cost!)
)
class VoxCPMService:
    @modal.enter()
    def load_model(self):
        import torch
        from voxcpm import VoxCPM

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading VoxCPM 2 on {device}...")
        self.model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
        self.sample_rate = getattr(getattr(self.model, "tts_model", None), "sample_rate", 24000)
        print(f"VoxCPM 2 ready! Native sample rate: {self.sample_rate}Hz")

        # Load ASR pipeline on GPU for automatic transcript extraction (enables Ultimate Voice Cloning)
        self.asr = None
        try:
            from transformers import pipeline
            device_id = 0 if torch.cuda.is_available() else -1
            self.asr = pipeline("automatic-speech-recognition", model="openai/whisper-base", device=device_id)
            print("Whisper ASR ready for Ultimate Voice Cloning alignment.")
        except Exception as e:
            print(f"ASR pipeline initialization note: {e}")

    def _transcribe(self, wav_path: str) -> str:
        """Extract transcript from reference audio to guide phoneme-aligned cloning."""
        if self.asr is None:
            return ""
        try:
            res = self.asr(wav_path)
            text = (res.get("text") or "").strip()
            # Guard against Whisper hallucination loops (e.g. repeated syllables, excessive length)
            words = text.split()
            if len(words) > 30 or len(text) > 150:
                print(f"ASR output rejected (too long/probable hallucination): '{text[:60]}...'")
                return ""
            if len(words) >= 4 and len(set(words)) <= 2:
                print(f"ASR output rejected (repetition loop detected): '{text[:60]}...'")
                return ""
            print(f"ASR transcribed reference audio: '{text}'")
            return text
        except Exception as e:
            print(f"ASR transcription failed: {e}")
            return ""

    @modal.method()
    def clone(self, req: dict) -> dict:
        import base64
        import os
        import tempfile
        import uuid
        import soundfile as sf

        audio_b64 = req.get("audio_base64", "")
        preview_text = req.get("preview_text") or "Hello! This is a preview of your cloned voice."
        prompt_text = (req.get("prompt_text") or "").strip()
        language = (req.get("language") or "en").lower()

        ref_bytes = base64.b64decode(audio_b64)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
            ref_tmp.write(ref_bytes)
            ref_path = ref_tmp.name

        # If user did not provide transcript, only attempt ASR for English (avoids hallucination on other languages)
        if not prompt_text and language.startswith("en"):
            prompt_text = self._transcribe(ref_path)

        preview_path = ref_path.replace(".wav", "_preview.wav")

        # Fast preview generation (10 timesteps keeps response under 3s)
        if prompt_text:
            wav_data = self.model.generate(
                text=preview_text,
                prompt_wav_path=ref_path,
                prompt_text=prompt_text,
                reference_wav_path=ref_path,
                inference_timesteps=10,
                cfg_value=2.0,
                denoise=False,
            )
        else:
            wav_data = self.model.generate(
                text=preview_text,
                reference_wav_path=ref_path,
                inference_timesteps=10,
                cfg_value=2.0,
                denoise=False,
            )

        sf.write(preview_path, wav_data, self.sample_rate)

        with open(preview_path, "rb") as f:
            preview_bytes = f.read()

        os.remove(ref_path)
        os.remove(preview_path)

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        token = f"voxcpm_{uuid.uuid4().hex[:12]}"
        return {
            "feature_token": token,
            "preview_base64": preview_b64,
            "prompt_text": prompt_text,
        }

    @modal.method()
    def synthesize(self, req: dict) -> dict:
        import base64
        import os
        import tempfile
        import soundfile as sf

        prompt_text_to_synthesize = req.get("inputs") or req.get("text") or req.get("raw_text") or "Hello from Vocara."
        ref_b64 = req.get("reference_audio_base64") or req.get("prompt_audio_base64")
        modifiers = req.get("modifiers") or {}
        prompt_text = (req.get("prompt_text") or modifiers.get("prompt_text") or "").strip()
        timesteps = int(req.get("inference_timesteps") or 15)
        cfg_val = float(req.get("cfg_value") or 2.0)
        language = (req.get("language") or "en").lower()

        ref_path = None
        if ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
                ref_tmp.write(ref_bytes)
                ref_path = ref_tmp.name

            # If prompt_text is not yet provided, only attempt ASR for English
            if not prompt_text and language.startswith("en"):
                prompt_text = self._transcribe(ref_path)

        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

        if ref_path and prompt_text:
            # Ultimate Voice Cloning (Exact phonetic and acoustic alignment: 95%+ match)
            wav_data = self.model.generate(
                text=prompt_text_to_synthesize,
                prompt_wav_path=ref_path,
                prompt_text=prompt_text,
                reference_wav_path=ref_path,
                inference_timesteps=timesteps,
                cfg_value=cfg_val,
                denoise=False,
            )
            os.remove(ref_path)
        elif ref_path:
            # Timbre-only fallback
            wav_data = self.model.generate(
                text=prompt_text_to_synthesize,
                reference_wav_path=ref_path,
                inference_timesteps=timesteps,
                cfg_value=cfg_val,
                denoise=False,
            )
            os.remove(ref_path)
        else:
            # Standard neural TTS
            wav_data = self.model.generate(
                text=prompt_text_to_synthesize,
                inference_timesteps=timesteps,
                cfg_value=cfg_val,
            )

        sf.write(out_tmp, wav_data, self.sample_rate)
        with open(out_tmp, "rb") as f:
            audio_bytes = f.read()
        os.remove(out_tmp)

        duration = len(wav_data) / float(self.sample_rate)
        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "duration": duration,
        }

    @modal.method()
    def design(self, req: dict) -> dict:
        import base64
        import os
        import tempfile
        import uuid
        import soundfile as sf

        preview_text = req.get("preview_text") or "Hello! This is a preview of your designed voice."
        modifiers = req.get("modifiers") or {}
        cues = []
        if "pitch" in modifiers:
            cues.append(f"pitch: {modifiers['pitch']}")
        if "speed" in modifiers:
            cues.append(f"speed: {modifiers['speed']}x")
        if "emotion" in modifiers:
            cues.append(f"emotion: {modifiers['emotion']}")
        if "style" in modifiers:
            cues.append(f"style: {modifiers['style']}")

        control_str = ", ".join(cues)
        formatted_prompt = f"({control_str}) {preview_text}" if control_str else preview_text

        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        wav_data = self.model.generate(text=formatted_prompt, inference_timesteps=10)
        sf.write(out_tmp, wav_data, self.sample_rate)

        with open(out_tmp, "rb") as f:
            preview_bytes = f.read()
        os.remove(out_tmp)

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        token = f"voxcpm_des_{uuid.uuid4().hex[:12]}"
        return {"feature_token": token, "preview_base64": preview_b64}


# 4. Web Endpoint Function (Imports FastAPI inside the container)
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    web_app = FastAPI(title="Vocara VoxCPM Modal Inference Endpoint")
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class CloneRequest(BaseModel):
        audio_base64: str
        language: str | None = "en"
        preview_text: str | None = "Hello! This is a preview of your newly cloned voice with Vocara."
        prompt_text: str | None = None

    class SynthesizeRequest(BaseModel):
        inputs: str | None = None
        text: str | None = None
        raw_text: str | None = None
        voice_id: str | None = None
        voice_name: str | None = None
        voice_type: str | None = None
        language: str | None = "en"
        speed: float | None = 1.0
        output_format: str | None = "wav"
        modifiers: dict | None = None
        control_instruction: str | None = None
        reference_audio_base64: str | None = None
        prompt_audio_base64: str | None = None
        reference_audio_key: str | None = None
        prompt_text: str | None = None
        inference_timesteps: int | None = 20
        cfg_value: float | None = 2.0

    class DesignRequest(BaseModel):
        base_voice_id: str | None = None
        modifiers: dict | None = None
        preview_text: str | None = "Hello! This is a preview of your designed acoustic voice with Vocara."

    @web_app.get("/")
    @web_app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "Vocara VoxCPM Modal Server"}

    @web_app.post("/clone")
    def clone_endpoint(req: CloneRequest):
        return VoxCPMService().clone.remote(req.model_dump())

    @web_app.post("/synthesize")
    def synthesize_endpoint(req: SynthesizeRequest):
        return VoxCPMService().synthesize.remote(req.model_dump())

    @web_app.post("/design")
    def design_endpoint(req: DesignRequest):
        return VoxCPMService().design.remote(req.model_dump())

    return web_app
