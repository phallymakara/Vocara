"""VoxCPM 2 Google Colab Inference Server for Vocara.

Run this script inside a Google Colab notebook with a free T4 GPU to host
real VoxCPM 2 zero-shot voice cloning and speech synthesis for Vocara.
"""

# Cell 1 in Colab: Install required libraries
# !pip install -q voxcpm fastapi uvicorn pycloudflared python-multipart pydantic nest-asyncio soundfile

import asyncio
import base64
import os
import tempfile
import uuid
from typing import Any, Optional

import nest_asyncio
import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pycloudflared import try_cloudflare
from voxcpm import VoxCPM

nest_asyncio.apply()

# 1. Initialize FastAPI Application
app = FastAPI(title="Vocara VoxCPM Colab Inference Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Load VoxCPM 2 Model onto GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading VoxCPM 2 model on device: {device}...")
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
sample_rate = getattr(getattr(model, "tts_model", None), "sample_rate", 24000)
print(f"VoxCPM 2 model loaded successfully! Native sample rate: {sample_rate}Hz")


# Request Schemas
class CloneRequest(BaseModel):
    audio_base64: str
    language: Optional[str] = "en"
    preview_text: Optional[str] = "Hello! This is a preview of your newly cloned voice with Vocara."


class SynthesizeRequest(BaseModel):
    inputs: Optional[str] = None
    text: Optional[str] = None
    raw_text: Optional[str] = None
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    voice_type: Optional[str] = None
    language: Optional[str] = "en"
    speed: Optional[float] = 1.0
    output_format: Optional[str] = "wav"
    modifiers: Optional[dict[str, Any]] = None
    control_instruction: Optional[str] = None
    reference_audio_base64: Optional[str] = None
    prompt_audio_base64: Optional[str] = None
    reference_audio_key: Optional[str] = None


class DesignRequest(BaseModel):
    base_voice_id: Optional[str] = None
    modifiers: Optional[dict[str, Any]] = None
    preview_text: Optional[str] = "Hello! This is a preview of your designed acoustic voice with Vocara."


# 3. Endpoints
@app.get("/")
@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "Vocara VoxCPM 2 Inference Server",
        "device": device,
        "sample_rate": sample_rate,
    }


@app.post("/clone")
def clone_voice(req: CloneRequest) -> dict[str, str]:
    """Extract timbre from reference audio and synthesize a preview."""
    try:
        ref_bytes = base64.b64decode(req.audio_base64)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
            ref_tmp.write(ref_bytes)
            ref_path = ref_tmp.name

        preview_path = ref_path.replace(".wav", "_preview.wav")
        text = req.preview_text or "Hello! This is a preview of your cloned voice."

        # Zero-shot voice cloning with VoxCPM (10 timesteps for high speed & quality)
        wav_data = model.generate(
            text=text,
            reference_wav_path=ref_path,
            denoise=True,
            inference_timesteps=10,
        )
        sf.write(preview_path, wav_data, sample_rate)

        with open(preview_path, "rb") as f:
            preview_bytes = f.read()

        # Clean up temporary files
        os.remove(ref_path)
        os.remove(preview_path)

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        token = f"voxcpm_{uuid.uuid4().hex[:12]}"
        return {"feature_token": token, "preview_base64": preview_b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {str(e)}")


@app.post("/")
@app.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    """Synthesize speech using VoxCPM, optionally using cloned reference timbre."""
    try:
        prompt_text = req.inputs or req.text or req.raw_text or "Hello from Vocara."
        ref_b64 = req.reference_audio_base64 or req.prompt_audio_base64
        ref_path = None

        if ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref_tmp:
                ref_tmp.write(ref_bytes)
                ref_path = ref_tmp.name

        out_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

        if ref_path:
            wav_data = model.generate(
                text=prompt_text,
                reference_wav_path=ref_path,
                denoise=False,
                inference_timesteps=10,
            )
            os.remove(ref_path)
        else:
            wav_data = model.generate(text=prompt_text, inference_timesteps=10)

        sf.write(out_tmp, wav_data, sample_rate)
        with open(out_tmp, "rb") as f:
            audio_bytes = f.read()
        os.remove(out_tmp)

        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


@app.post("/design")
def design_voice(req: DesignRequest) -> dict[str, str]:
    """Design custom voice with acoustic modifiers."""
    try:
        preview_text = req.preview_text or "Hello! This is a preview of your designed voice."
        modifiers = req.modifiers or {}
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
        wav_data = model.generate(text=formatted_prompt, inference_timesteps=10)
        sf.write(out_tmp, wav_data, sample_rate)

        with open(out_tmp, "rb") as f:
            preview_bytes = f.read()
        os.remove(out_tmp)

        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        token = f"voxcpm_des_{uuid.uuid4().hex[:12]}"
        return {"feature_token": token, "preview_base64": preview_b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice design failed: {str(e)}")


# 4. Launch Background Server & Cloudflare Tunnel
async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def run():
    print("Starting Cloudflare Tunnel...")
    tunnel_url = try_cloudflare(port=8000)
    print("\n" + "=" * 65)
    print("VOXCPM 2 COLAB SERVER IS RUNNING!")
    print(f"Public URL: {tunnel_url.tunnel}")
    print("=" * 65)
    print("\nCopy the URL above and set it in your local Vocara 'backend/.env':")
    print("INFERENCE_ENGINE_TYPE=huggingface")
    print(f"HUGGINGFACE_ENDPOINT_URL={tunnel_url.tunnel}")
    print("=" * 65 + "\n")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server())


if __name__ == "__main__":
    run()

