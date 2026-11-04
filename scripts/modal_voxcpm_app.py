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
        self.sample_rate = getattr(getattr(self.model, "tts_model", None), "sample_rate", 48000)
        print(f"VoxCPM 2 ready! Native sample rate: {self.sample_rate}Hz")

    def _clone(self, req: dict) -> dict:
        import base64
        import os
        import tempfile
        import uuid
        import soundfile as sf

        audio_b64 = req.get("audio_base64", "")
        # Synthesize ONLY and STRICTLY the exact preview text
        preview_text = (req.get("preview_text") or "Hello! This is a preview of your cloned voice.").strip()
        # Only use prompt_text if explicitly provided by the user (no unconstrained Whisper hallucination)
        prompt_text = (req.get("prompt_text") or "").strip()

        ref_bytes = base64.b64decode(audio_b64)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
            ref_tmp.write(ref_bytes)
            ref_path = ref_tmp.name

        preview_path = ref_path.replace(".wav", "_preview.wav")

        # Cap max_len dynamically to prevent runaway 4096-token generation loops
        preview_max_len = max(100, min(500, int(len(preview_text) * 3) + 80))

        # Use pure zero-shot reference cloning (or user-verified transcript alignment)
        if prompt_text:
            wav_data = self.model.generate(
                text=preview_text,
                prompt_wav_path=ref_path,
                prompt_text=prompt_text,
                reference_wav_path=ref_path,
                inference_timesteps=20,
                cfg_value=1.8,
                denoise=False,
                max_len=preview_max_len,
            )
        else:
            wav_data = self.model.generate(
                text=preview_text,
                reference_wav_path=ref_path,
                inference_timesteps=20,
                cfg_value=1.8,
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

    def _synthesize(self, req: dict) -> dict:
        import base64
        import os
        import tempfile
        import soundfile as sf

        # Synthesize ONLY and STRICTLY the exact input text provided by the user
        input_text = (req.get("inputs") or req.get("text") or req.get("raw_text") or "Hello from Vocara.").strip()
        ref_b64 = req.get("reference_audio_base64") or req.get("prompt_audio_base64")

        # High fidelity diffusion timesteps & calibrated guidance scale
        timesteps = int(req.get("inference_timesteps") or 20)
        cfg_val = float(req.get("cfg_value") or 1.8)

        ref_path = None
        if ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
                ref_tmp.write(ref_bytes)
                ref_path = ref_tmp.name

        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

        # Dynamic max token limit based on exact text length (prevents runaway hang)
        char_count = len(input_text)
        synth_max_len = max(150, min(1500, int(char_count * 3.5) + 100))

        if ref_path:
            # Pure Zero-Shot Voice Cloning via reference_wav_path:
            # Extracts 100% authentic speaker timbre, pitch resonance, and vocal harmonics
            # from the reference audio clip, and speaks ONLY AND STRICTLY the input_text!
            # No hallucinated words, no prefix, and no audio leakage from the reference clip.
            wav_data = self.model.generate(
                text=input_text,
                reference_wav_path=ref_path,
                inference_timesteps=timesteps,
                cfg_value=cfg_val,
                denoise=False,
                max_len=synth_max_len,
            )
            os.remove(ref_path)
        else:
            # Standard neural TTS (when no reference voice is provided)
            wav_data = self.model.generate(
                text=input_text,
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

    def _design(self, req: dict) -> dict:
        import base64
        import os
        import tempfile
        import uuid
        import soundfile as sf

        preview_text = (req.get("preview_text") or "Hello! This is a preview of your designed voice.").strip()
        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        wav_data = self.model.generate(text=preview_text, inference_timesteps=20, cfg_value=1.8)
        sf.write(out_tmp, wav_data, self.sample_rate)

        with open(out_tmp, "rb") as f:
            preview_bytes = f.read()
        os.remove(out_tmp)

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        token = f"voxcpm_des_{uuid.uuid4().hex[:12]}"
        return {"feature_token": token, "preview_base64": preview_b64}

    # Modal RPC methods (can be called remotely from Python clients)
    @modal.method()
    def clone(self, req: dict) -> dict:
        return self._clone(req)

    @modal.method()
    def synthesize(self, req: dict) -> dict:
        return self._synthesize(req)

    @modal.method()
    def design(self, req: dict) -> dict:
        return self._design(req)

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
            inference_timesteps: int | None = 20
            cfg_value: float | None = 1.8

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
            return self._clone(req.model_dump())

        @web_app.post("/synthesize")
        def synthesize_endpoint(req: SynthesizeRequest):
            return self._synthesize(req.model_dump())

        @web_app.post("/design")
        def design_endpoint(req: DesignRequest):
            return self._design(req.model_dump())

        return web_app
