"""Modal serverless deployment for VoxCPM 2.

Deploy to Modal with:
    modal deploy scripts/modal_voxcpm_app.py
"""

import base64
import os
import tempfile
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import modal

# 1. Define Modal App
app = modal.App("vocara-voxcpm")

# 2. Define Container Image with PyTorch & VoxCPM
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
    )
)


# 3. Request Schemas
class CloneRequest(BaseModel):
    audio_base64: str
    language: str | None = "en"
    preview_text: str | None = "Hello! This is a preview of your newly cloned voice with Vocara."


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
    modifiers: dict[str, Any] | None = None
    control_instruction: str | None = None
    reference_audio_base64: str | None = None
    prompt_audio_base64: str | None = None
    reference_audio_key: str | None = None


class DesignRequest(BaseModel):
    base_voice_id: str | None = None
    modifiers: dict[str, Any] | None = None
    preview_text: str | None = "Hello! This is a preview of your designed acoustic voice with Vocara."


# 4. Service Class with GPU
@app.cls(
    image=image,
    gpu="T4",
    timeout=300,
    scaledown_window=60,  # Scales to 0 when idle ($0 cost!)
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
        print(f"VoxCPM 2 ready! Sample rate: {self.sample_rate}Hz")

    @modal.method()
    def clone(self, req: dict[str, Any]) -> dict[str, str]:
        import soundfile as sf

        audio_b64 = req.get("audio_base64", "")
        preview_text = req.get("preview_text") or "Hello! This is a preview of your cloned voice."
        ref_bytes = base64.b64decode(audio_b64)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
            ref_tmp.write(ref_bytes)
            ref_path = ref_tmp.name

        preview_path = ref_path.replace(".wav", "_preview.wav")
        wav_data = self.model.generate(
            text=preview_text,
            reference_wav_path=ref_path,
            denoise=True,
            inference_timesteps=10,
        )
        sf.write(preview_path, wav_data, self.sample_rate)

        with open(preview_path, "rb") as f:
            preview_bytes = f.read()

        os.remove(ref_path)
        os.remove(preview_path)

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        token = f"voxcpm_{uuid.uuid4().hex[:12]}"
        return {"feature_token": token, "preview_base64": preview_b64}

    @modal.method()
    def synthesize(self, req: dict[str, Any]) -> dict[str, Any]:
        import soundfile as sf

        prompt_text = req.get("inputs") or req.get("text") or req.get("raw_text") or "Hello from Vocara."
        ref_b64 = req.get("reference_audio_base64") or req.get("prompt_audio_base64")
        ref_path = None

        if ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
                ref_tmp.write(ref_bytes)
                ref_path = ref_tmp.name

        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

        if ref_path:
            wav_data = self.model.generate(
                text=prompt_text,
                reference_wav_path=ref_path,
                denoise=False,
                inference_timesteps=10,
            )
            os.remove(ref_path)
        else:
            wav_data = self.model.generate(text=prompt_text, inference_timesteps=10)

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
    def design(self, req: dict[str, Any]) -> dict[str, str]:
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


# 5. Web App with Endpoints
web_app = FastAPI(title="Vocara VoxCPM Modal Inference Endpoint")
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@web_app.get("/")
@web_app.get("/health")
def health() -> dict[str, str]:
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


@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app
