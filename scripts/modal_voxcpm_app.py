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


# 3. Model Service Class with GPU and Direct Unified FastAPI App (Single Container Architecture)
@app.cls(
    image=image,
    gpu="A100-40GB",  # NVIDIA A100 (40GB) with 1,555 GB/s HBM2 bandwidth for near-instant inference
    cpu=4.0,
    memory=16384,
    timeout=300,
    scaledown_window=900,  # Stays warm for 15 minutes after last request (0s startup during testing!)
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

        # Load ASR pipeline on GPU for automatic transcript extraction
        self.asr = None
        try:
            from transformers import pipeline
            device_id = 0 if torch.cuda.is_available() else -1
            self.asr = pipeline("automatic-speech-recognition", model="openai/whisper-base", device=device_id)
            print("Whisper ASR ready for voice clone alignment.")
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

        # If user did not provide transcript, only attempt ASR for English
        if not prompt_text and language.startswith("en"):
            prompt_text = self._transcribe(ref_path)

        preview_path = ref_path.replace(".wav", "_preview.wav")

        # Cap max_len dynamically to prevent runaway 4096-token generation loops
        preview_max_len = max(100, min(500, int(len(preview_text) * 3) + 80))

        # Natural human preview generation (timesteps=20, cfg_value=1.35)
        if prompt_text:
            wav_data = self.model.generate(
                text=preview_text,
                prompt_wav_path=ref_path,
                prompt_text=prompt_text,
                reference_wav_path=ref_path,
                inference_timesteps=20,
                cfg_value=1.35,
                denoise=False,
                max_len=preview_max_len,
            )
        else:
            wav_data = self.model.generate(
                text=preview_text,
                reference_wav_path=ref_path,
                inference_timesteps=20,
                cfg_value=1.35,
                denoise=False,
                max_len=preview_max_len,
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
        # Natural human acoustic fidelity: 22 diffusion timesteps & relaxed 1.35 guidance
        timesteps = int(req.get("inference_timesteps") or 22)
        cfg_val = float(req.get("cfg_value") or 1.35)
        language = (req.get("language") or "en").lower()
        is_continuation = bool(req.get("is_continuation", False))

        ref_path = None
        if ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
                ref_tmp.write(ref_bytes)
                ref_path = ref_tmp.name

            # If prompt_text is not yet provided, only attempt ASR for English if continuation is requested
            if is_continuation and not prompt_text and language.startswith("en"):
                prompt_text = self._transcribe(ref_path)

        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

        # Calculate dynamic max token limit based on text length (prevents 4096-token runaway hang)
        char_count = len(prompt_text_to_synthesize)
        synth_max_len = max(150, min(1500, int(char_count * 3.5) + 100))

        if ref_path and is_continuation and prompt_text:
            # Continuation mode: continues sentence in the same breath as prompt audio
            wav_data = self.model.generate(
                text=prompt_text_to_synthesize,
                prompt_wav_path=ref_path,
                prompt_text=prompt_text,
                reference_wav_path=ref_path,
                inference_timesteps=timesteps,
                cfg_value=cfg_val,
                denoise=False,
                max_len=synth_max_len,
            )
            os.remove(ref_path)
        elif ref_path:
            # Natural Human Zero-Shot Timbre Cloning:
            # Replicates 100% authentic speaker timbre and acoustic harmonics,
            # while generating authentic sentence-opening cadence, natural pauses, and conversational intonation.
            wav_data = self.model.generate(
                text=prompt_text_to_synthesize,
                reference_wav_path=ref_path,
                inference_timesteps=timesteps,
                cfg_value=cfg_val,
                denoise=False,
                max_len=synth_max_len,
            )
            os.remove(ref_path)
        else:
            # Standard neural TTS
            wav_data = self.model.generate(
                text=prompt_text_to_synthesize,
                inference_timesteps=timesteps,
                cfg_value=cfg_val,
                max_len=synth_max_len,
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
        wav_data = self.model.generate(text=formatted_prompt, inference_timesteps=18, cfg_value=1.35)
        sf.write(out_tmp, wav_data, self.sample_rate)

        with open(out_tmp, "rb") as f:
            preview_bytes = f.read()
        os.remove(out_tmp)

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        token = f"voxcpm_des_{uuid.uuid4().hex[:12]}"
        return {"feature_token": token, "preview_base64": preview_b64}

    # 4. Direct Unified FastAPI ASGI Endpoint inside GPU Container
    @modal.asgi_app(label="vocara-voxcpm-fastapi-app")
    def fastapi_app(self):
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
            inference_timesteps: int | None = 22
            cfg_value: float | None = 1.35
            is_continuation: bool | None = False

        class DesignRequest(BaseModel):
            base_voice_id: str | None = None
            modifiers: dict | None = None
            preview_text: str | None = "Hello! This is a preview of your designed acoustic voice with Vocara."

        @web_app.get("/")
        @web_app.get("/health")
        def health() -> dict:
            return {
                "status": "ok",
                "service": "Vocara VoxCPM Modal Unified Server",
                "architecture": "Single Container Direct In-Memory",
                "gpu": "A100-40GB",
            }

        @web_app.post("/clone")
        def clone_endpoint(req: CloneRequest):
            # Direct in-memory invocation without RPC serialization hop
            return self.clone(req.model_dump())

        @web_app.post("/synthesize")
        def synthesize_endpoint(req: SynthesizeRequest):
            # Direct in-memory invocation without RPC serialization hop
            return self.synthesize(req.model_dump())

        @web_app.post("/design")
        def design_endpoint(req: DesignRequest):
            # Direct in-memory invocation without RPC serialization hop
            return self.design(req.model_dump())

        return web_app
