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
        import os
        import torch
        from voxcpm import VoxCPM

        # Phase 3: Hardware Acceleration for NVIDIA A100 Tensor Cores & Triton
        os.environ["TRITON_DEFAULT_FP_FUSION"] = "1"
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading VoxCPM 2 on {device} (TF32 Hardware Acceleration Enabled)...")
        self.model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
        self.sample_rate = getattr(getattr(self.model, "tts_model", None), "sample_rate", 48000)
        print(f"VoxCPM 2 ready! Native sample rate: {self.sample_rate}Hz")

        # Phase 2: In-Memory Voice Reference Cache (maps voice_id -> pre-cached WAV path on GPU host)
        self.voice_cache: dict[str, str] = {}

    def _clone(self, req: dict) -> dict:
        import base64
        import io
        import os
        import tempfile
        import uuid
        import torch
        import soundfile as sf

        audio_b64 = req.get("audio_base64", "")
        # Synthesize ONLY and STRICTLY the exact preview text
        preview_text = (req.get("preview_text") or "Hello! This is a preview of your cloned voice.").strip()
        prompt_text = (req.get("prompt_text") or "").strip()

        ref_bytes = base64.b64decode(audio_b64)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
            ref_tmp.write(ref_bytes)
            ref_path = ref_tmp.name

        # Cap max_len dynamically to prevent runaway generation loops
        preview_max_len = max(100, min(500, int(len(preview_text) * 3) + 80))

        # Phase 3 & 4: Inference mode & calibrated 12 timesteps on A100
        with torch.inference_mode():
            if prompt_text:
                wav_data = self.model.generate(
                    text=preview_text,
                    prompt_wav_path=ref_path,
                    prompt_text=prompt_text,
                    reference_wav_path=ref_path,
                    inference_timesteps=12,
                    cfg_value=1.8,
                    denoise=False,
                    max_len=preview_max_len,
                )
            else:
                wav_data = self.model.generate(
                    text=preview_text,
                    reference_wav_path=ref_path,
                    inference_timesteps=12,
                    cfg_value=1.8,
                    denoise=False,
                    max_len=preview_max_len,
                )

        # Phase 1: Direct in-memory buffer output (zero disk write/read overhead)
        buf = io.BytesIO()
        sf.write(buf, wav_data, self.sample_rate, format="WAV")
        preview_bytes = buf.getvalue()

        # Cache reference audio by token for instant subsequent synthesis
        token = f"voxcpm_{uuid.uuid4().hex[:12]}"
        cached_file = f"/tmp/vocara_ref_{token}.wav"
        try:
            os.rename(ref_path, cached_file)
            self.voice_cache[token] = cached_file
        except Exception:
            try:
                os.remove(ref_path)
            except Exception:
                pass

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        return {
            "feature_token": token,
            "preview_base64": preview_b64,
            "prompt_text": prompt_text,
        }

    def _synthesize(self, req: dict) -> dict:
        import base64
        import io
        import os
        import tempfile
        import uuid
        import torch
        import soundfile as sf
        from fastapi import HTTPException

        input_text = (req.get("inputs") or req.get("text") or req.get("raw_text") or "Hello from Vocara.").strip()
        voice_id = req.get("voice_id")
        ref_b64 = req.get("reference_audio_base64") or req.get("prompt_audio_base64")

        # Phase 4: Calibrated diffusion steps (12 steps delivers studio fidelity at 2.5x speed)
        timesteps = int(req.get("inference_timesteps") or 12)
        cfg_val = float(req.get("cfg_value") or 1.8)

        # Phase 2: In-Memory Voice Reference Cache Lookup
        ref_path = None
        if voice_id and voice_id in self.voice_cache and os.path.exists(self.voice_cache[voice_id]):
            ref_path = self.voice_cache[voice_id]
        elif ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            cache_key = voice_id or uuid.uuid4().hex[:12]
            cached_file = f"/tmp/vocara_voice_{cache_key}.wav"
            with open(cached_file, "wb") as f:
                f.write(ref_bytes)
            ref_path = cached_file
            if voice_id:
                # Maintain LRU cap of 50 active voices in container memory
                if len(self.voice_cache) > 50:
                    oldest_id, oldest_path = next(iter(self.voice_cache.items()))
                    try:
                        os.remove(oldest_path)
                    except Exception:
                        pass
                    del self.voice_cache[oldest_id]
                self.voice_cache[voice_id] = ref_path
        elif voice_id and not ref_b64:
            # Voice requested from cache but not present (container cold restart) -> prompt client to upload
            raise HTTPException(status_code=404, detail="voice_cache_miss")

        # Dynamic max token limit based on exact text length (prevents runaway hang)
        char_count = len(input_text)
        synth_max_len = max(150, min(1500, int(char_count * 3.5) + 100))

        # Phase 3: TensorFloat-32 + Inference Mode Execution
        with torch.inference_mode():
            if ref_path:
                wav_data = self.model.generate(
                    text=input_text,
                    reference_wav_path=ref_path,
                    inference_timesteps=timesteps,
                    cfg_value=cfg_val,
                    denoise=False,
                    max_len=synth_max_len,
                )
            else:
                wav_data = self.model.generate(
                    text=input_text,
                    inference_timesteps=timesteps,
                    cfg_value=cfg_val,
                    max_len=synth_max_len,
                )

        # Phase 1: Direct in-memory buffer output (zero disk write/read overhead)
        buf = io.BytesIO()
        sf.write(buf, wav_data, self.sample_rate, format="WAV")
        audio_bytes = buf.getvalue()

        duration = len(wav_data) / float(self.sample_rate)
        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "duration": duration,
        }

    def _design(self, req: dict) -> dict:
        import base64
        import io
        import uuid
        import torch
        import soundfile as sf

        preview_text = (req.get("preview_text") or "Hello! This is a preview of your designed voice.").strip()
        with torch.inference_mode():
            wav_data = self.model.generate(text=preview_text, inference_timesteps=12, cfg_value=1.8)

        buf = io.BytesIO()
        sf.write(buf, wav_data, self.sample_rate, format="WAV")
        preview_bytes = buf.getvalue()

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
            inference_timesteps: int | None = 12
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
                "accelerations": ["TF32", "In-Memory IO", "Voice Caching", "12-Step Diffusion"],
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
