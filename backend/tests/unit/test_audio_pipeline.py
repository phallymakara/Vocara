"""Unit tests for Audio Preprocessing & Quality Enhancement Pipeline."""

import io
import numpy as np
import pytest
import soundfile as sf

from vocara.core.exceptions import InvalidAudioError
from vocara.utils.audio import (
    apply_duration_guardrails,
    decode_audio_to_pcm,
    normalize_audio_levels,
    preprocess_reference_audio,
    reduce_background_noise,
    trim_silence,
    validate_reference_audio,
)


def _generate_wav_bytes(
    duration_s: float = 4.0,
    sample_rate: int = 24000,
    freq: float = 220.0,
    amplitude: float = 0.5,
    leading_silence_s: float = 0.0,
    trailing_silence_s: float = 0.0,
    noise_level: float = 0.0,
) -> bytes:
    """Helper to synthesize test audio WAV buffers."""
    parts = []
    if leading_silence_s > 0:
        parts.append(np.zeros(int(sample_rate * leading_silence_s), dtype=np.float32))

    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    tone = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    if noise_level > 0:
        tone += (noise_level * np.random.randn(len(t))).astype(np.float32)
    parts.append(tone)

    if trailing_silence_s > 0:
        parts.append(np.zeros(int(sample_rate * trailing_silence_s), dtype=np.float32))

    audio = np.concatenate(parts)
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def test_validate_and_decode_wav():
    raw_wav = _generate_wav_bytes(duration_s=3.0)
    meta = validate_reference_audio(raw_wav)
    assert meta["format"] == "wav"
    assert meta["size_bytes"] > 1024

    pcm, sr = decode_audio_to_pcm(raw_wav)
    assert sr == 24000
    assert len(pcm) > 0
    assert isinstance(pcm, np.ndarray)


def test_validate_rejects_empty_and_tiny_files():
    with pytest.raises(InvalidAudioError, match="empty"):
        validate_reference_audio(b"")

    with pytest.raises(InvalidAudioError, match="too short"):
        validate_reference_audio(b"RIFF1234WAVE" + b"\x00" * 100)


def test_trim_silence_removes_dead_audio():
    sample_rate = 24000
    # 2 seconds silence + 3 seconds tone + 2 seconds silence
    raw_wav = _generate_wav_bytes(
        duration_s=3.0,
        sample_rate=sample_rate,
        leading_silence_s=2.0,
        trailing_silence_s=2.0,
    )
    pcm, sr = decode_audio_to_pcm(raw_wav)
    assert len(pcm) / sr >= 6.9

    trimmed = trim_silence(pcm, sr, db_threshold=-40.0)
    trimmed_duration = len(trimmed) / sr
    # Should be approximately 3.0s + padding (around 3.3s), significantly less than 7s
    assert 2.8 <= trimmed_duration <= 3.8


def test_trim_silence_raises_on_pure_silence():
    sample_rate = 24000
    silent_pcm = np.zeros(sample_rate * 4, dtype=np.float32)
    with pytest.raises(InvalidAudioError, match="No speech detected"):
        trim_silence(silent_pcm, sample_rate)


def test_duration_guardrails_min_duration():
    sample_rate = 24000
    short_pcm = np.ones(int(sample_rate * 1.5), dtype=np.float32) * 0.1
    with pytest.raises(InvalidAudioError, match="too short"):
        apply_duration_guardrails(short_pcm, sample_rate, min_seconds=2.5)


def test_duration_guardrails_crops_long_audio():
    sample_rate = 24000
    # 40 seconds total: first 20s quiet, next 20s loud speech
    quiet = np.ones(int(sample_rate * 20), dtype=np.float32) * 0.05
    loud = np.ones(int(sample_rate * 20), dtype=np.float32) * 0.5
    long_pcm = np.concatenate([quiet, loud])

    cropped = apply_duration_guardrails(
        long_pcm, sample_rate, max_seconds=30.0, target_crop_seconds=18.0
    )
    assert len(cropped) == int(18.0 * sample_rate)
    # The cropped window should have selected the louder speech section
    assert float(np.mean(cropped**2)) > 0.15


def test_reduce_background_noise():
    sample_rate = 24000
    # Tone with stationary background noise
    t = np.linspace(0, 4, 4 * sample_rate, endpoint=False)
    tone = (0.4 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    noise = (0.05 * np.random.randn(len(t))).astype(np.float32)
    noisy_audio = tone + noise

    denoised = reduce_background_noise(noisy_audio, sample_rate, reduction_db=6.0)
    assert len(denoised) == len(noisy_audio)
    # Spectral gating preserves vocal envelope
    assert np.max(np.abs(denoised)) > 0.2


def test_normalize_audio_levels():
    # Very quiet audio (-40 dB)
    quiet_pcm = np.ones(24000, dtype=np.float32) * 0.01
    normalized = normalize_audio_levels(quiet_pcm, target_rms_db=-20.0, peak_ceiling_db=-1.0)

    rms = np.sqrt(np.mean(normalized**2))
    rms_db = 20 * np.log10(rms)
    assert pytest.approx(rms_db, abs=1.0) == -20.0

    # Ensure peak doesn't exceed -1.0 dBFS (~0.891)
    peak = np.max(np.abs(normalized))
    assert peak <= 0.892


def test_preprocess_reference_audio_end_to_end():
    # 6 seconds audio with leading/trailing silence and slight noise
    raw_wav = _generate_wav_bytes(
        duration_s=4.0,
        sample_rate=44100,
        leading_silence_s=1.0,
        trailing_silence_s=1.0,
        noise_level=0.02,
    )

    clean_wav, duration, metrics = preprocess_reference_audio(
        raw_wav,
        target_sample_rate=24000,
        enable_denoise=True,
        enable_normalization=True,
    )

    assert isinstance(clean_wav, bytes)
    assert len(clean_wav) > 1024
    assert clean_wav.startswith(b"RIFF")
    # Natural audio duration is preserved without aggressive silence cropping
    assert 5.5 <= duration <= 6.5
    assert metrics["sample_rate"] == 24000
    assert metrics["denoise_applied"] is True
    assert metrics["normalization_applied"] is True

