"""Audio inspection, normalization, and validation utilities."""

import io

import numpy as np
import soundfile as sf

from vocara.core.exceptions import InvalidAudioError


def validate_reference_audio(
    audio_bytes: bytes,
    min_size_bytes: int = 1024,
    max_size_bytes: int = 15 * 1024 * 1024,  # 15 MB
) -> dict[str, str | int]:
    """Validate reference audio payload before cloning."""
    if not audio_bytes:
        raise InvalidAudioError("Uploaded audio file is empty.")

    size = len(audio_bytes)
    if size < min_size_bytes:
        raise InvalidAudioError("Uploaded audio is too short or corrupted.")
    if size > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise InvalidAudioError(f"Audio exceeds maximum permitted file size of {max_mb}MB.")

    # Detect common audio headers (RIFF/WAV, ID3/MP3, OGG, fLaC)
    header = audio_bytes[:12]
    detected_format = "unknown"

    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        detected_format = "wav"
    elif (
        header.startswith(b"ID3")
        or header.startswith(b"\xff\xfb")
        or header.startswith(b"\xff\xf3")
    ):
        detected_format = "mp3"
    elif header.startswith(b"OggS"):
        detected_format = "ogg"
    elif header.startswith(b"fLaC"):
        detected_format = "flac"

    if detected_format == "unknown":
        raise InvalidAudioError(
            "Unsupported audio container. Please upload a standard WAV, MP3, OGG, or FLAC file."
        )

    return {
        "format": detected_format,
        "size_bytes": size,
    }


def get_audio_duration_seconds(audio_bytes: bytes) -> float:
    """Inspect audio binary and return duration in seconds."""
    try:
        with sf.SoundFile(io.BytesIO(audio_bytes)) as sound_file:
            return float(sound_file.frames) / float(sound_file.samplerate)
    except Exception as err:
        raise InvalidAudioError(f"Failed to decode audio duration: {err}") from err


def normalize_audio_to_wav(
    audio_bytes: bytes, target_sample_rate: int = 24000
) -> tuple[bytes, float]:
    """Normalize multi-format audio into standardized 24kHz mono 16-bit PCM WAV.

    Returns:
        tuple[wav_bytes, duration_seconds]: The normalized WAV audio and duration.
    """
    try:
        with io.BytesIO(audio_bytes) as in_buf:
            data, sample_rate = sf.read(in_buf, dtype="float32")

        # Convert to mono if multi-channel
        if data.ndim > 1:
            data = data.mean(axis=1)

        duration = len(data) / float(sample_rate)

        # Resample using linear interpolation if sample rate differs
        if sample_rate != target_sample_rate:
            target_length = int(len(data) * target_sample_rate / sample_rate)
            time_orig = np.linspace(0, duration, len(data), endpoint=False)
            time_target = np.linspace(0, duration, target_length, endpoint=False)
            data = np.interp(time_target, time_orig, data).astype("float32")

        # Write to WAV PCM_16 format
        out_buf = io.BytesIO()
        sf.write(out_buf, data, target_sample_rate, format="WAV", subtype="PCM_16")
        return out_buf.getvalue(), duration

    except Exception as err:
        raise InvalidAudioError(f"Audio normalization failed: {err}") from err


def generate_synthetic_tone_wav(
    duration_seconds: float = 1.0,
    sample_rate: int = 24000,
    frequency: float = 440.0,
) -> bytes:
    """Generate a clean synthetic PCM WAV tone for preview and mock audio tests."""
    total_samples = int(sample_rate * duration_seconds)
    t = np.linspace(0, duration_seconds, total_samples, endpoint=False)
    sine_wave = (0.5 * np.sin(2 * np.pi * frequency * t)).astype("float32")

    out_buf = io.BytesIO()
    sf.write(out_buf, sine_wave, sample_rate, format="WAV", subtype="PCM_16")
    return out_buf.getvalue()
