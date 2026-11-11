"""Modal serverless deployment for Khmer-adapted VoxCPM 2.

Deploy to Modal with:
    uvx modal deploy scripts/modal_voxcpm_app.py
"""

import os

import modal

APP_NAME = os.environ.get("MODAL_APP_NAME", "vocara-voxcpm")
ASGI_LABEL = os.environ.get("MODAL_ASGI_LABEL", "vocara-voxcpm-fastapi-app")
DEFAULT_MODEL_ID = os.environ.get("VOXCPM_MODEL_ID", "ravuthz/VoxCPM2-khmer")
DEFAULT_LORA_ID = os.environ.get("VOXCPM_LORA_ID", "")
DEFAULT_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE_HZ", "48000"))

app = modal.App(APP_NAME)


def download_model():
    """Pre-download configured VoxCPM 2 weights and optional LoRA adapter into image layer."""
    from voxcpm import VoxCPM

    model_id = os.environ.get("VOXCPM_MODEL_ID", DEFAULT_MODEL_ID)
    lora_id = os.environ.get("VOXCPM_LORA_ID", "").strip()
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY") or None

    print(f"Pre-downloading VoxCPM 2 weights from {model_id}...")
    VoxCPM.from_pretrained(model_id, load_denoiser=False)

    if lora_id:
        from huggingface_hub import snapshot_download

        print(f"Pre-downloading LoRA adapter from {lora_id}...")
        snapshot_download(repo_id=lora_id, token=hf_token)

    print("Model weights cached successfully!")


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
        "huggingface-hub",
        "khmer-nltk",
    )
    .env(
        {
            "VOXCPM_MODEL_ID": DEFAULT_MODEL_ID,
            "VOXCPM_LORA_ID": DEFAULT_LORA_ID,
            "AUDIO_SAMPLE_RATE_HZ": str(DEFAULT_SAMPLE_RATE),
        }
    )
    .run_function(download_model)
)


@app.cls(
    image=image,
    gpu="A100-40GB",
    cpu=4.0,
    memory=16384,
    timeout=300,
    scaledown_window=900,
)
@modal.concurrent(max_inputs=10)
class VoxCPMService:
    @modal.enter()
    def load_model(self):
        import inspect
        import torch
        from voxcpm import VoxCPM

        os.environ["TRITON_DEFAULT_FP_FUSION"] = "1"
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

        model_id = os.environ.get("VOXCPM_MODEL_ID", DEFAULT_MODEL_ID)
        lora_id = os.environ.get("VOXCPM_LORA_ID", "").strip()
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY") or None
        device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"Loading VoxCPM 2 ({model_id}) on {device} (TF32 enabled)...")
        init_kwargs: dict = {"load_denoiser": False}
        from_pretrained_params = set(inspect.signature(VoxCPM.from_pretrained).parameters.keys())
        voxcpm_init_params = set(inspect.signature(VoxCPM.__init__).parameters.keys())
        if "optimize" in from_pretrained_params or "optimize" in voxcpm_init_params:
            # Avoid torch.compile CUDA graph RNG reuse and eliminate ~100s cold-start compile overhead
            init_kwargs["optimize"] = False

        if lora_id:
            from huggingface_hub import snapshot_download

            lora_dir = snapshot_download(repo_id=lora_id, token=hf_token)
            if "lora_weights_path" in from_pretrained_params:
                init_kwargs["lora_weights_path"] = lora_dir
            elif "lora_path" in from_pretrained_params:
                init_kwargs["lora_path"] = lora_dir

        self.model = VoxCPM.from_pretrained(model_id, **init_kwargs)
        self.model_id = model_id
        self.lora_id = lora_id or None
        self.sample_rate = getattr(
            getattr(self.model, "tts_model", None),
            "sample_rate",
            int(os.environ.get("AUDIO_SAMPLE_RATE_HZ", str(DEFAULT_SAMPLE_RATE))),
        )
        self._generate_params = set(inspect.signature(self.model.generate).parameters.keys())
        tts_model = getattr(self.model, "tts_model", None)
        self._bpc_params = (
            set(inspect.signature(tts_model.build_prompt_cache).parameters.keys())
            if tts_model and hasattr(tts_model, "build_prompt_cache")
            else set()
        )
        self._gpc_params = (
            set(inspect.signature(tts_model.generate_with_prompt_cache).parameters.keys())
            if tts_model and hasattr(tts_model, "generate_with_prompt_cache")
            else set()
        )
        self.voice_cache: dict[str, str] = {}
        self.prompt_cache_map: dict[str, dict] = {}
        print(
            f"VoxCPM 2 ready! model={model_id}, lora={self.lora_id}, "
            f"sample_rate={self.sample_rate}Hz, generate_params={sorted(self._generate_params)}"
        )

    @staticmethod
    def _segment_khmer_text(text: str) -> str:
        """Apply optional Khmer word segmentation when VOXCPM_KHMER_WORD_SPACING=true.

        By default VoxCPM 2 receives natural unsegmented Khmer phrasing so words flow smoothly
        without artificial staccato pauses between every word.
        """
        import re

        if not text:
            return ""
        if os.environ.get("VOXCPM_KHMER_WORD_SPACING", "false").lower() != "true":
            return text.strip()
        khmer_run_re = re.compile(r"([\u1780-\u17FF]+)")
        if not khmer_run_re.search(text):
            return text

        try:
            from khmernltk import word_tokenize
        except Exception:
            return text

        parts: list[str] = []
        last_idx = 0
        for match in khmer_run_re.finditer(text):
            if match.start() > last_idx:
                parts.append(text[last_idx : match.start()])
            khmer_span = match.group(1)
            tokens = [tok.strip() for tok in word_tokenize(khmer_span, return_tokens=True) if tok.strip()]
            parts.append(" ".join(tokens) if tokens else khmer_span)
            last_idx = match.end()

        if last_idx < len(text):
            parts.append(text[last_idx:])

        joined = "".join(parts)
        return re.sub(r"[ \t]+", " ", joined).strip()

    @staticmethod
    def _normalize_speech_text(text: str) -> str:
        """Normalize spacing and punctuation for smooth conversational human pacing."""
        import re

        if not text:
            return ""

        text = text.strip()
        text = re.sub(r"\s*[-—–~]+\s*", ", ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s+([។៕.!?,;:])", r"\1", text)
        text = re.sub(r"([។៕.!?,;:])(?=[^\s\d])", r"\1 ", text)
        return text.strip()

    @staticmethod
    def _distill_control_instruction(
        control_instruction: str | None = None,
        modifiers: dict | None = None,
    ) -> str:
        """Build a concise parenthetical VoxCPM2 acoustic instruction from structured modifiers or description."""
        import re

        if control_instruction and control_instruction.strip():
            cleaned = control_instruction.strip().strip("()")
            # Keep ASCII acoustic tags inside (...) so VoxCPM 2 never reads Khmer instructions aloud
            ascii_only = re.sub(r"[^\x20-\x7E]+", " ", cleaned)
            return re.sub(r"\s+", " ", ascii_only)[:140].strip()

        if not modifiers:
            return ""

        cues: list[str] = []
        gender = str(modifiers.get("gender") or "").strip().lower()
        if gender == "female":
            cues.append("woman")
        elif gender == "male":
            cues.append("man")

        desc = str(modifiers.get("description") or "").strip()
        if desc:
            first_clause = re.split(r"[\n.!?។]+", desc)[0].strip()
            ascii_clause = re.sub(r"[^\x20-\x7E]+", " ", first_clause).strip()
            if ascii_clause:
                cues.append(ascii_clause[:90].strip())

        emotion = str(modifiers.get("emotion") or "").strip()
        if emotion:
            ascii_emo = re.sub(r"[^\x20-\x7E]+", " ", emotion).strip()
            if ascii_emo:
                cues.append(f"{ascii_emo} tone")

        style = str(modifiers.get("style") or "").strip()
        if style:
            ascii_sty = re.sub(r"[^\x20-\x7E]+", " ", style).strip()
            if ascii_sty:
                cues.append(f"{ascii_sty} style")

        try:
            pitch = float(modifiers.get("pitch", 1.0))
            if pitch <= 0.85:
                cues.append("deep lower pitch")
            elif pitch >= 1.15:
                cues.append("bright higher pitch")
        except (TypeError, ValueError):
            pass

        try:
            speed = float(modifiers.get("speed", 1.0))
            if speed <= 0.85:
                cues.append("speaks slowly")
            elif speed >= 1.15:
                cues.append("lively pace")
        except (TypeError, ValueError):
            pass

        combined = ", ".join(cues)
        return re.sub(r"\s+", " ", combined)[:140].strip()

    @classmethod
    def _extract_instruction_and_text(
        cls,
        raw_text: str,
        control_instruction: str | None = None,
        modifiers: dict | None = None,
    ) -> tuple[str, str]:
        """Separate control instruction from spoken body before segmentation and chunk length computation."""
        import re

        text = (raw_text or "").strip()
        leading_match = re.match(r"^\(([^)]{2,300})\)\s*(.+)$", text, flags=re.DOTALL)
        extracted_inline = ""
        if leading_match:
            extracted_inline = leading_match.group(1).strip()
            text = leading_match.group(2).strip()

        resolved_instruction = cls._distill_control_instruction(
            control_instruction=control_instruction or extracted_inline or None,
            modifiers=modifiers,
        )
        return resolved_instruction, text

    @staticmethod
    def _split_into_speech_chunks(text: str, max_chunk_chars: int = 450) -> list[str]:
        """Pack consecutive sentences up to max_chunk_chars so multi-sentence audio stays one voice."""
        import re

        text = text.strip()
        if not text:
            return []

        boundary_pattern = r"([។៕.!?\n]+)"
        tokens = re.split(boundary_pattern, text)

        sentences: list[str] = []
        current = ""
        for token in tokens:
            if not token:
                continue
            if re.match(boundary_pattern, token):
                current += token
                if current.strip():
                    sentences.append(current.strip())
                    current = ""
            else:
                if current:
                    sentences.append(current.strip())
                current = token
        if current.strip():
            sentences.append(current.strip())

        packed_chunks: list[str] = []
        buf = ""
        for s in sentences:
            if len(s) > max_chunk_chars:
                if buf.strip():
                    packed_chunks.append(buf.strip())
                    buf = ""
                clause_tokens = re.split(r"([,;]+)", s)
                clause_buf = ""
                for ct in clause_tokens:
                    if len(clause_buf) + len(ct) <= max_chunk_chars:
                        clause_buf += ct
                    else:
                        if clause_buf.strip():
                            packed_chunks.append(clause_buf.strip())
                        clause_buf = ct
                if clause_buf.strip():
                    packed_chunks.append(clause_buf.strip())
                continue

            candidate = f"{buf} {s}".strip() if buf else s
            if len(candidate) <= max_chunk_chars:
                buf = candidate
            else:
                if buf.strip():
                    packed_chunks.append(buf.strip())
                buf = s
        if buf.strip():
            packed_chunks.append(buf.strip())

        safe_chunks: list[str] = []
        for c in packed_chunks:
            if len(c) <= max_chunk_chars:
                safe_chunks.append(c)
            else:
                for i in range(0, len(c), max_chunk_chars):
                    safe_chunks.append(c[i : i + max_chunk_chars])

        return [c for c in safe_chunks if c.strip()]

    @staticmethod
    def _stitch_audio_chunks(chunks: list, sample_rate: int, pause_ms: int = 120):
        """Crossfade and stitch audio chunks smoothly."""
        import numpy as np

        if not chunks:
            return np.array([], dtype=np.float32)
        if len(chunks) == 1:
            return chunks[0]

        pause_samples = int(sample_rate * (pause_ms / 1000.0))
        fade_len = min(256, max(1, pause_samples // 2))
        fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
        silence = np.zeros(pause_samples, dtype=np.float32)

        pieces = []
        for i, c in enumerate(chunks):
            chunk_copy = c.copy()
            if len(chunk_copy) > fade_len:
                if i > 0:
                    chunk_copy[:fade_len] *= fade_in
                if i < len(chunks) - 1:
                    chunk_copy[-fade_len:] *= fade_out
            pieces.append(chunk_copy)
            if i < len(chunks) - 1:
                pieces.append(silence)

        return np.concatenate(pieces)

    def _encode_audio(self, wav_data, output_format: str) -> bytes:
        import io
        import soundfile as sf

        buf = io.BytesIO()
        fmt = (output_format or "wav").lower()
        if fmt == "mp3":
            try:
                sf.write(buf, wav_data, self.sample_rate, format="MP3")
                return buf.getvalue()
            except Exception:
                buf.seek(0)
                buf.truncate()
        sf.write(buf, wav_data, self.sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    @staticmethod
    def _prepare_reference_audio(
        raw_bytes: bytes,
        dest_path: str,
        target_rms: float = 0.10,
        max_sec: float = 10.0,
    ) -> str:
        """Trim silence, cap duration, and RMS-normalize reference audio for stable speaker extraction."""
        import io
        import numpy as np
        import soundfile as sf

        try:
            pcm, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32", always_2d=False)
            if pcm.ndim > 1:
                pcm = np.mean(pcm, axis=1)
            peak = float(np.max(np.abs(pcm))) if len(pcm) else 0.0
            if peak > 0.0 and len(pcm) > int(0.25 * sr):
                win, hop = int(0.05 * sr), int(0.01 * sr)
                thresh = max(0.008, peak * 0.08)
                active = [
                    i
                    for i in range(0, max(1, len(pcm) - win), hop)
                    if float(np.sqrt(np.mean(pcm[i : i + win] ** 2))) > thresh
                ]
                if active:
                    pad = int(0.08 * sr)
                    pcm = pcm[max(0, active[0] - pad) : min(len(pcm), active[-1] + win + pad)]
            max_samples = int(max_sec * sr)
            if len(pcm) > max_samples:
                pcm = pcm[:max_samples]
            rms = float(np.sqrt(np.mean(pcm ** 2))) if len(pcm) else 0.0
            if rms > 1e-5:
                gain = min(target_rms / rms, 0.90 / (float(np.max(np.abs(pcm))) + 1e-9))
                pcm = np.clip(pcm * gain, -0.95, 0.95)
            sf.write(dest_path, pcm, sr, format="WAV", subtype="PCM_16")
        except Exception:
            with open(dest_path, "wb") as f:
                f.write(raw_bytes)
        return dest_path

    def _store_cached_voice(self, cache_key: str, ref_bytes: bytes) -> str:
        """Precondition and cache reference audio cleanly under LRU eviction."""
        cached_file = f"/tmp/vocara_voice_{cache_key}.wav"
        self._prepare_reference_audio(ref_bytes, cached_file)
        if cache_key not in self.voice_cache and len(self.voice_cache) >= 50:
            oldest_id, oldest_path = next(iter(self.voice_cache.items()))
            self.prompt_cache_map.pop(oldest_id, None)
            if oldest_path != cached_file:
                try:
                    os.remove(oldest_path)
                except Exception:
                    pass
            del self.voice_cache[oldest_id]
        self.voice_cache[cache_key] = cached_file
        self.prompt_cache_map.pop(cache_key, None)
        return cached_file

    def _get_or_build_prompt_cache(self, ref_path: str | None, cache_key: str | None = None) -> dict | None:
        """Build or reuse VoxCPM2 isolated reference prompt_cache with VAD trimming."""
        if not ref_path or not self._bpc_params:
            return None
        if cache_key and cache_key in self.prompt_cache_map:
            return self.prompt_cache_map[cache_key]
        bpc_kwargs: dict = {"reference_wav_path": ref_path}
        if "trim_silence_vad" in self._bpc_params:
            bpc_kwargs["trim_silence_vad"] = True
        pc = self.model.tts_model.build_prompt_cache(**bpc_kwargs)
        if cache_key:
            self.prompt_cache_map[cache_key] = pc
        return pc

    def _generate_chunk(
        self,
        model_text: str,
        spoken_len: int,
        timesteps: int,
        cfg_val: float,
        prompt_cache: dict | None = None,
        ref_path: str | None = None,
        seed: int = 42,
    ):
        """Generate one speech chunk using locked prompt_cache and deterministic per-request seed."""
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        synth_max_len = max(160, min(1200, int(spoken_len * 4.0) + 120))
        if prompt_cache is not None and self._gpc_params:
            gpc_kwargs: dict = {
                "target_text": model_text,
                "prompt_cache": prompt_cache,
                "inference_timesteps": timesteps,
                "cfg_value": cfg_val,
            }
            if "min_len" in self._gpc_params:
                gpc_kwargs["min_len"] = 2
            if "max_len" in self._gpc_params:
                gpc_kwargs["max_len"] = synth_max_len
            if "retry_badcase" in self._gpc_params:
                # Avoid Khmer UTF-8 byte-length badcase retries that resample speakers mid-utterance
                gpc_kwargs["retry_badcase"] = False
            wav, _, _ = self.model.tts_model.generate_with_prompt_cache(**gpc_kwargs)
            return wav.squeeze(0).cpu().numpy()

        kwargs: dict = {
            "text": model_text,
            "inference_timesteps": timesteps,
            "cfg_value": cfg_val,
        }
        if "max_len" in self._generate_params:
            kwargs["max_len"] = synth_max_len
        if "normalize" in self._generate_params:
            kwargs["normalize"] = False
        if "retry_badcase" in self._generate_params:
            kwargs["retry_badcase"] = False
        if ref_path and "reference_wav_path" in self._generate_params:
            kwargs["reference_wav_path"] = ref_path
        if "denoise" in self._generate_params:
            kwargs["denoise"] = False
        return self.model.generate(**kwargs)

    @staticmethod
    def _resolve_speaker_seed(voice_id: str | None) -> int:
        import zlib

        if not voice_id:
            return 42
        return (zlib.crc32(voice_id.encode("utf-8")) % 100000) + 1

    def _clone(self, req: dict) -> dict:
        import base64
        import uuid
        import torch

        audio_b64 = req.get("audio_base64", "")
        voice_id = req.get("voice_id")
        token = voice_id or f"voxcpm_{uuid.uuid4().hex[:12]}"
        prompt_text = (req.get("prompt_text") or "").strip()

        ref_bytes = base64.b64decode(audio_b64)
        cached_file = self._store_cached_voice(token, ref_bytes)
        if voice_id and voice_id != token:
            self.voice_cache[voice_id] = cached_file

        preview_b64 = None
        if req.get("generate_preview", False):
            raw_preview = (req.get("preview_text") or "").strip()
            if raw_preview:
                segmented_preview = self._normalize_speech_text(self._segment_khmer_text(raw_preview))
                timesteps = int(req.get("inference_timesteps") or 20)
                cfg_val = float(req.get("cfg_value") or 2.0)
                seed = self._resolve_speaker_seed(voice_id or token)
                with torch.inference_mode():
                    pc = self._get_or_build_prompt_cache(cached_file, cache_key=token)
                    wav_data = self._generate_chunk(
                        model_text=segmented_preview,
                        spoken_len=len(segmented_preview),
                        timesteps=timesteps,
                        cfg_val=cfg_val,
                        prompt_cache=pc,
                        ref_path=cached_file,
                        seed=seed,
                    )
                wav_bytes = self._encode_audio(wav_data, "wav")
                preview_b64 = base64.b64encode(wav_bytes).decode("utf-8")

        return {
            "feature_token": token,
            "preview_base64": preview_b64,
            "prompt_text": prompt_text,
            "status": "cached",
        }

    def _synthesize(self, req: dict) -> dict:
        import base64
        import uuid
        import torch
        from fastapi import HTTPException

        raw_text = (req.get("inputs") or req.get("text") or req.get("raw_text") or "").strip()
        if not raw_text:
            raise HTTPException(status_code=400, detail="Input text cannot be empty.")

        voice_id = req.get("voice_id")
        ref_b64 = req.get("reference_audio_base64") or req.get("prompt_audio_base64")
        timesteps = int(req.get("inference_timesteps") or 20)
        cfg_val = float(req.get("cfg_value") or 2.0)
        max_chunk_chars = int(req.get("max_chunk_chars") or 450)
        modifiers = req.get("modifiers") or {}
        explicit_instruction = req.get("control_instruction")

        ref_path = None
        cache_key = voice_id
        if voice_id and voice_id in self.voice_cache and os.path.exists(self.voice_cache[voice_id]):
            ref_path = self.voice_cache[voice_id]
        elif ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            cache_key = voice_id or uuid.uuid4().hex[:12]
            ref_path = self._store_cached_voice(cache_key, ref_bytes)
        elif voice_id and not ref_b64:
            raise HTTPException(status_code=404, detail="voice_cache_miss")

        instruction, spoken_body = self._extract_instruction_and_text(
            raw_text,
            control_instruction=explicit_instruction if not ref_path else None,
            modifiers=modifiers if not ref_path else None,
        )
        segmented_body = self._normalize_speech_text(self._segment_khmer_text(spoken_body))
        chunks = self._split_into_speech_chunks(segmented_body, max_chunk_chars=max_chunk_chars)
        if not chunks:
            chunks = [segmented_body]

        seed = self._resolve_speaker_seed(cache_key)
        raw_audio_chunks = []
        with torch.inference_mode():
            prompt_cache = self._get_or_build_prompt_cache(ref_path, cache_key=cache_key)
            for chunk in chunks:
                # Keep pure isolated reference timbre when ref_path is active so VoxCPM2 stays one speaker
                model_input = f"({instruction}){chunk}" if (instruction and not ref_path) else chunk
                chunk_audio = self._generate_chunk(
                    model_text=model_input,
                    spoken_len=len(chunk),
                    timesteps=timesteps,
                    cfg_val=cfg_val,
                    prompt_cache=prompt_cache,
                    ref_path=ref_path,
                    seed=seed,
                )
                raw_audio_chunks.append(chunk_audio)

        wav_data = self._stitch_audio_chunks(raw_audio_chunks, self.sample_rate, pause_ms=120)
        audio_bytes = self._encode_audio(wav_data, req.get("output_format") or "wav")
        duration = len(wav_data) / float(self.sample_rate)

        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "duration": round(duration, 3),
            "sample_rate": self.sample_rate,
            "control_instruction": instruction if not ref_path else "",
            "prompt_text": segmented_body,
        }

    def _design(self, req: dict) -> dict:
        """Synthesize a designed voice anchored to a primary Khmer reference speaker (if provided) + style cues."""
        import base64
        import uuid
        import torch
        from fastapi import HTTPException

        raw_text = (req.get("preview_text") or "").strip()
        if not raw_text:
            raise HTTPException(status_code=400, detail="preview_text cannot be empty.")

        modifiers = req.get("modifiers") or {}
        timesteps = int(req.get("inference_timesteps") or 20)
        cfg_val = float(req.get("cfg_value") or 1.75)
        max_chunk_chars = int(req.get("max_chunk_chars") or 450)
        ref_b64 = req.get("reference_audio_base64") or req.get("prompt_audio_base64")
        voice_id = req.get("base_voice_id") or req.get("voice_id")

        ref_path = None
        cache_key = voice_id
        if ref_b64:
            ref_bytes = base64.b64decode(ref_b64)
            cache_key = voice_id or uuid.uuid4().hex[:12]
            ref_path = self._store_cached_voice(cache_key, ref_bytes)
        elif voice_id and voice_id in self.voice_cache and os.path.exists(self.voice_cache[voice_id]):
            ref_path = self.voice_cache[voice_id]

        instruction, spoken_body = self._extract_instruction_and_text(
            raw_text,
            control_instruction=req.get("control_instruction"),
            modifiers=modifiers,
        )
        segmented_body = self._normalize_speech_text(self._segment_khmer_text(spoken_body))
        chunks = self._split_into_speech_chunks(segmented_body, max_chunk_chars=max_chunk_chars)
        if not chunks:
            chunks = [segmented_body]

        import random

        seed = int(req.get("seed") or random.randint(1, 999999))
        raw_audio_chunks = []
        with torch.inference_mode():
            prompt_cache = self._get_or_build_prompt_cache(ref_path, cache_key=cache_key)
            for chunk in chunks:
                model_input = f"({instruction}){chunk}" if instruction else chunk
                chunk_audio = self._generate_chunk(
                    model_text=model_input,
                    spoken_len=len(chunk),
                    timesteps=timesteps,
                    cfg_val=cfg_val,
                    prompt_cache=prompt_cache,
                    ref_path=ref_path,
                    seed=seed,
                )
                raw_audio_chunks.append(chunk_audio)

        wav_data = self._stitch_audio_chunks(raw_audio_chunks, self.sample_rate, pause_ms=120)
        preview_bytes = self._encode_audio(wav_data, "wav")
        preview_b64 = base64.b64encode(preview_bytes).decode("utf-8")
        duration = round(len(wav_data) / float(self.sample_rate), 3)
        token = f"voxcpm_des_{uuid.uuid4().hex[:12]}"

        return {
            "feature_token": token,
            "audio_base64": preview_b64,
            "preview_base64": preview_b64,
            "duration": duration,
            "sample_rate": self.sample_rate,
            "control_instruction": instruction,
            "prompt_text": segmented_body,
        }

    @modal.method()
    def clone(self, req: dict) -> dict:
        return self._clone(req)

    @modal.method()
    def synthesize(self, req: dict) -> dict:
        return self._synthesize(req)

    @modal.method()
    def design(self, req: dict) -> dict:
        return self._design(req)

    @modal.asgi_app(label=ASGI_LABEL)
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
            voice_id: str | None = None
            language: str | None = None
            preview_text: str | None = None
            prompt_text: str | None = None
            generate_preview: bool | None = False
            inference_timesteps: int | None = None
            cfg_value: float | None = None
            max_chunk_chars: int | None = None

        class SynthesizeRequest(BaseModel):
            inputs: str | None = None
            text: str | None = None
            raw_text: str | None = None
            voice_id: str | None = None
            voice_name: str | None = None
            voice_type: str | None = None
            language: str | None = None
            speed: float | None = 1.0
            output_format: str | None = "wav"
            modifiers: dict | None = None
            control_instruction: str | None = None
            reference_audio_base64: str | None = None
            prompt_audio_base64: str | None = None
            reference_audio_key: str | None = None
            prompt_text: str | None = None
            inference_timesteps: int | None = None
            cfg_value: float | None = None
            max_chunk_chars: int | None = None
            max_chunk_chars: int | None = None

        class DesignRequest(BaseModel):
            base_voice_id: str | None = None
            voice_id: str | None = None
            modifiers: dict | None = None
            control_instruction: str | None = None
            reference_audio_base64: str | None = None
            prompt_audio_base64: str | None = None
            preview_text: str
            inference_timesteps: int | None = None
            cfg_value: float | None = None
            max_chunk_chars: int | None = None

        @web_app.get("/")
        @web_app.get("/health")
        def health() -> dict:
            return {
                "status": "ok",
                "service": "Vocara VoxCPM Modal Unified Server",
                "model_id": self.model_id,
                "lora_id": self.lora_id,
                "sample_rate": self.sample_rate,
                "gpu": "A100-40GB",
                "features": ["khmer-nltk-segmentation", "voice-design", "continuation-cloning", "TF32"],
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
