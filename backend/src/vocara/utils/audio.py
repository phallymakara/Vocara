"""Audio inspection, normalization, preprocessing, and validation utilities."""

import io
import subprocess
from typing import Any

import numpy as np
import soundfile as sf

from vocara.core.exceptions import InvalidAudioError


def validate_reference_audio(
    audio_bytes: bytes,
    min_size_bytes: int = 1024,
    max_size_bytes: int = 25 * 1024 * 1024,  # 25 MB
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

    # Detect common audio headers (RIFF/WAV, ID3/MP3, OGG, fLaC, M4A, WebM, AAC)
    header = audio_bytes[:16]
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
    elif header.startswith(b"\x1a\x45\xdf\xa3"):
        detected_format = "webm"
    elif b"ftyp" in audio_bytes[4:24]:
        detected_format = "m4a"
    elif header.startswith(b"\xff\xf1") or header.startswith(b"\xff\xf9"):
        detected_format = "aac"
    else:
        # Check if soundfile can decode it regardless of signature
        try:
            with io.BytesIO(audio_bytes) as buf:
                with sf.SoundFile(buf) as test_sf:
                    detected_format = test_sf.format.lower()
        except Exception:
            pass

    if detected_format == "unknown":
        raise InvalidAudioError(
            "Unsupported audio container. Please upload a standard WAV, MP3, OGG, FLAC, M4A, or WebM file."
        )

    return {
        "format": detected_format,
        "size_bytes": size,
    }


def decode_audio_to_pcm(audio_bytes: bytes) -> tuple[np.ndarray, int]:
    """Decode audio bytes of any format into float32 PCM numpy array and sample rate."""
    # 1. Primary: Fast in-memory decoding via soundfile
    try:
        with io.BytesIO(audio_bytes) as in_buf:
            data, sample_rate = sf.read(in_buf, dtype="float32")
        return data, sample_rate
    except Exception:
        pass

    # 2. Resilient fallback: decode using ffmpeg pipe if soundfile lacks container demuxer (e.g. M4A/WebM)
    try:
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-f",
                "wav",
                "-acodec",
                "pcm_f32le",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_data, _ = proc.communicate(input=audio_bytes, timeout=10)
        if proc.returncode == 0 and len(stdout_data) > 44:
            with io.BytesIO(stdout_data) as in_buf:
                data, sample_rate = sf.read(in_buf, dtype="float32")
            return data, sample_rate
    except Exception:
        pass

    raise InvalidAudioError(
        "Failed to decode audio file. Please ensure the file is an uncorrupted WAV, MP3, OGG, FLAC, M4A, or WebM audio."
    )


def trim_silence(
    data: np.ndarray,
    sample_rate: int,
    db_threshold: float = -42.0,
    frame_ms: int = 20,
    padding_ms: int = 150,
) -> np.ndarray:
    """Detect voice activity and trim leading and trailing dead silence."""
    frame_length = max(1, int(sample_rate * frame_ms / 1000))
    total_frames = len(data) // frame_length

    if total_frames < 2:
        return data

    speech_flags = np.zeros(total_frames, dtype=bool)
    for i in range(total_frames):
        frame = data[i * frame_length : (i + 1) * frame_length]
        rms = float(np.sqrt(np.mean(frame**2) + 1e-12))
        db = 20.0 * np.log10(rms)
        if db >= db_threshold:
            speech_flags[i] = True

    speech_indices = np.where(speech_flags)[0]
    if len(speech_indices) == 0:
        raise InvalidAudioError("No speech detected in audio recording. Please speak clearly into the microphone.")

    first_frame = speech_indices[0]
    last_frame = speech_indices[-1]

    padding_samples = int(sample_rate * padding_ms / 1000)
    start_idx = max(0, first_frame * frame_length - padding_samples)
    end_idx = min(len(data), (last_frame + 1) * frame_length + padding_samples)

    return data[start_idx:end_idx]


def apply_duration_guardrails(
    data: np.ndarray,
    sample_rate: int,
    min_seconds: float = 2.5,
    max_seconds: float = 30.0,
    target_crop_seconds: float = 18.0,
) -> np.ndarray:
    """Enforce minimum speech duration and smart-crop excessively long audio."""
    duration = len(data) / float(sample_rate)

    if duration < min_seconds:
        raise InvalidAudioError(
            f"Voice sample is too short ({duration:.1f}s). Please upload at least 3 seconds of spoken audio."
        )

    # If within acceptable range, keep entire sample
    if duration <= max_seconds:
        return data

    # Smart Windowing: select the continuous 18-second segment with the highest speech energy
    window_samples = int(target_crop_seconds * sample_rate)
    step_samples = max(1, int(sample_rate * 1.0))
    best_start = 0
    max_energy = -1.0

    for start in range(0, len(data) - window_samples + 1, step_samples):
        segment = data[start : start + window_samples]
        energy = float(np.mean(segment**2))
        if energy > max_energy:
            max_energy = energy
            best_start = start

    return data[best_start : best_start + window_samples]


def reduce_background_noise(
    data: np.ndarray,
    sample_rate: int,
    reduction_db: float = 6.0,
) -> np.ndarray:
    """Gentle spectral gating filter to suppress stationary background hum, fan noise, and hiss."""
    if len(data) < 1024:
        return data

    n_fft = 1024
    hop_length = 512
    win = np.hanning(n_fft).astype(np.float32)

    # 1. Identify quietest 15% frames as ambient noise floor estimation
    n_frames = (len(data) - n_fft) // hop_length + 1
    if n_frames < 4:
        return data

    frame_energies = []
    for i in range(n_frames):
        frame = data[i * hop_length : i * hop_length + n_fft] * win
        frame_energies.append(float(np.mean(frame**2)))

    sorted_indices = np.argsort(frame_energies)
    noise_frame_count = max(1, int(n_frames * 0.15))
    noise_indices = sorted_indices[:noise_frame_count]

    noise_magnitudes = []
    for idx in noise_indices:
        frame = data[idx * hop_length : idx * hop_length + n_fft] * win
        noise_magnitudes.append(np.abs(np.fft.rfft(frame)))

    avg_noise_floor = np.mean(noise_magnitudes, axis=0) * 1.2

    # 2. Spectral subtraction with flooring (reduction_db floor prevents underwater artifacts)
    attenuation_floor = float(10.0 ** (-reduction_db / 20.0))  # e.g., ~0.5 for 6dB
    out_signal = np.zeros(len(data), dtype=np.float32)
    win_sum = np.zeros(len(data), dtype=np.float32)

    for i in range(n_frames):
        start = i * hop_length
        frame = data[start : start + n_fft] * win
        spec = np.fft.rfft(frame)
        mag = np.abs(spec)
        phase = np.angle(spec)

        # Subtract stationary noise spectrum
        gain = np.maximum(attenuation_floor, (mag - avg_noise_floor) / (mag + 1e-12))
        gain = np.clip(gain, attenuation_floor, 1.0)

        cleaned_spec = gain * mag * np.exp(1j * phase)
        cleaned_frame = np.real(np.fft.irfft(cleaned_spec)) * win

        out_signal[start : start + n_fft] += cleaned_frame
        win_sum[start : start + n_fft] += win**2

    # Normalize overlap-add reconstruction
    mask = win_sum > 1e-6
    out_signal[mask] /= win_sum[mask]
    return out_signal


def normalize_audio_levels(
    data: np.ndarray,
    target_rms_db: float = -20.0,
    peak_ceiling_db: float = -1.0,
) -> np.ndarray:
    """Standardize vocal loudness to consistent RMS level with peak headroom."""
    current_rms = float(np.sqrt(np.mean(data**2) + 1e-12))
    target_rms = float(10.0 ** (target_rms_db / 20.0))

    gain = target_rms / current_rms
    normalized = data * gain

    # Peak Limiter
    peak = float(np.max(np.abs(normalized)) + 1e-12)
    peak_ceiling = float(10.0 ** (peak_ceiling_db / 20.0))

    if peak > peak_ceiling:
        normalized = normalized * (peak_ceiling / peak)

    return normalized.astype(np.float32)


def reduce_noise_subtle(data: np.ndarray, sample_rate: int) -> np.ndarray:
    """Subtly reduce background noise while leaving vocal formants 100% natural and uncolored.

    1. Subsonic zero-phase high-pass filter (cutoff 65 Hz): Eliminates low-frequency AC rumble, desk vibrations,
       and DC offset without touching human speech fundamental frequencies (human pitch F0 >= 85 Hz).
    2. Subtle noise floor expansion: Smoothly attenuates very quiet room pauses (< -45 dBFS) by 2-3 dB
       to clean up background hiss without affecting speech consonants, vowels, or breathing.
    3. Peak headroom ceiling limiter: Prevents digital clipping (max peak <= 0.95).
    """
    if len(data) < 256:
        return data

    # 1. Zero-phase high-pass filter at 65 Hz via vectorized FFT (eliminates DC offset and sub-65Hz rumble)
    fc = 65.0
    freqs = np.fft.rfftfreq(len(data), d=1.0 / sample_rate)
    ratio = (freqs / fc) ** 2
    h_gain = (ratio / (1.0 + ratio)).astype(np.float32)
    filtered = np.real(np.fft.irfft(np.fft.rfft(data) * h_gain, n=len(data))).astype(np.float32)

    # 2. Vectorized subtle soft-floor attenuation for very quiet ambient pauses (< -45 dBFS)
    frame_len = max(1, int(sample_rate * 0.02))  # 20ms frames
    n_frames = len(filtered) // frame_len
    if n_frames < 2:
        return filtered

    threshold_linear = float(10.0 ** (-45.0 / 20.0))
    usable_len = n_frames * frame_len
    frames = filtered[:usable_len].reshape(n_frames, frame_len)
    rms_vec = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    ratio_vec = rms_vec / threshold_linear
    g_vec = np.where(rms_vec < threshold_linear, 0.75 + 0.25 * ratio_vec, 1.0).astype(np.float32)

    gain_curve = np.ones(len(filtered), dtype=np.float32)
    gain_curve[:usable_len] = np.repeat(g_vec, frame_len)

    # Smooth gain curve over 10ms window to prevent clicks
    window = max(1, int(sample_rate * 0.01))
    gain_smooth = np.convolve(gain_curve, np.ones(window, dtype=np.float32) / window, mode="same")
    out = (filtered * gain_smooth).astype(np.float32)

    # 3. Soft peak limiter to prevent clipping
    peak = float(np.max(np.abs(out)) + 1e-12)
    if peak > 0.95:
        out = out * (0.95 / peak)

    return out.astype(np.float32)


def preprocess_reference_audio(
    audio_bytes: bytes,
    target_sample_rate: int = 48000,
    enable_denoise: bool = True,
    enable_normalization: bool = False,
    min_duration: float = 0.5,
    max_duration: float = 120.0,
    enable_trim: bool = False,
) -> tuple[bytes, float, dict[str, Any]]:
    """Universal audio decoding and gentle noise reduction pipeline for voice cloning.

    Preserves 100% of the speaker's original cadence, pitch, emotion, and vocal nuances,
    while applying subtle noise cleaning to remove low-frequency rumble and background hiss.
    Does not aggressively crop, trim, or compress the audio.

    Returns:
        tuple[wav_bytes, duration_seconds, metrics_dict]
    """
    # 1. Validation
    meta = validate_reference_audio(audio_bytes)
    detected_format = meta["format"]

    # 2. Universal Decoding
    data, sample_rate = decode_audio_to_pcm(audio_bytes)

    # 3. Channel Downmix
    if data.ndim > 1:
        data = data.mean(axis=1)

    raw_duration = len(data) / float(sample_rate)

    # Optional silence trimming (disabled by default to preserve natural pauses & timing)
    if enable_trim:
        data = trim_silence(data, sample_rate)

    # 4. Subtle Noise Reduction (gentle rumble filter & soft ambient floor)
    if enable_denoise:
        data = reduce_noise_subtle(data, sample_rate)

    # 5. Optional normalization or gentle peak safety
    if enable_normalization:
        data = normalize_audio_levels(data, target_rms_db=-20.0, peak_ceiling_db=-1.0)
    else:
        # Peak safety limiter only (leaves natural dynamics untouched)
        peak = float(np.max(np.abs(data)) + 1e-12)
        if peak > 0.95:
            data = data * (0.95 / peak)

    final_duration = len(data) / float(sample_rate)

    # 6. Resample if needed
    if sample_rate != target_sample_rate:
        target_length = int(len(data) * target_sample_rate / sample_rate)
        time_orig = np.linspace(0, final_duration, len(data), endpoint=False)
        time_target = np.linspace(0, final_duration, target_length, endpoint=False)
        data = np.interp(time_target, time_orig, data).astype("float32")

    # Write clean 16-bit PCM WAV
    out_buf = io.BytesIO()
    sf.write(out_buf, data, target_sample_rate, format="WAV", subtype="PCM_16")
    clean_wav_bytes = out_buf.getvalue()

    metrics = {
        "detected_format": detected_format,
        "original_duration_seconds": round(raw_duration, 2),
        "processed_duration_seconds": round(final_duration, 2),
        "denoise_applied": enable_denoise,
        "normalization_applied": enable_normalization,
        "sample_rate": target_sample_rate,
    }

    return clean_wav_bytes, final_duration, metrics


def get_audio_duration_seconds(audio_bytes: bytes) -> float:
    """Inspect audio binary and return duration in seconds."""
    try:
        with sf.SoundFile(io.BytesIO(audio_bytes)) as sound_file:
            return float(sound_file.frames) / float(sound_file.samplerate)
    except Exception:
        try:
            data, sr = decode_audio_to_pcm(audio_bytes)
            return len(data) / float(sr)
        except Exception as err:
            raise InvalidAudioError(f"Failed to decode audio duration: {err}") from err


def normalize_audio_to_wav(
    audio_bytes: bytes, target_sample_rate: int = 24000
) -> tuple[bytes, float]:
    """Normalize multi-format audio into standardized 24kHz mono 16-bit PCM WAV."""
    clean_bytes, duration, _ = preprocess_reference_audio(
        audio_bytes,
        target_sample_rate=target_sample_rate,
        enable_denoise=False,
        enable_normalization=True,
        min_duration=0.5,
    )
    return clean_bytes, duration


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


def estimate_pitch_or_centroid(audio_bytes: bytes) -> float:
    """Estimate the dominant acoustic frequency / pitch of the given WAV audio sample."""
    try:
        with io.BytesIO(audio_bytes) as in_buf:
            data, sample_rate = sf.read(in_buf, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if len(data) < 256:
            return 220.0
        max_samples = min(len(data), int(sample_rate * 2))
        fft_vals = np.abs(np.fft.rfft(data[:max_samples]))
        freqs = np.fft.rfftfreq(max_samples, d=1.0 / sample_rate)
        mask = (freqs >= 80.0) & (freqs <= 600.0)
        if np.any(mask):
            peak_freq = freqs[mask][np.argmax(fft_vals[mask])]
            return float(peak_freq)
        return 220.0
    except Exception:
        return 220.0


def extract_acoustic_profile(wav_bytes: bytes) -> dict[str, float | str | int]:
    """Extract fundamental pitch F0, vocal gender, and pitch shift metrics from WAV bytes."""
    try:
        with io.BytesIO(wav_bytes) as in_buf:
            data, sr = sf.read(in_buf, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)

        # Optimize compute: downsample to 16 kHz for pitch extraction (cuts compute time by ~88%)
        # Pitch F0 is max 450 Hz, so 16 kHz sample rate (Nyquist 8000 Hz) preserves 100% pitch precision
        step = max(1, sr // 16000)
        ds_data = data[::step]
        ds_sr = sr // step

        frame_len = int(0.05 * ds_sr)
        hop_len = int(0.025 * ds_sr)
        min_lag = int(ds_sr / 450)
        max_lag = int(ds_sr / 65)

        f0_estimates: list[float] = []
        rms_threshold = np.sqrt(np.mean(ds_data**2)) * 0.4

        for start in range(0, len(ds_data) - frame_len, ds_hop_len):
            frame = ds_data[start : start + frame_len]
            if np.sqrt(np.mean(frame**2)) < rms_threshold:
                continue
            corr = np.correlate(frame, frame, mode="full")[len(frame) - 1 :]
            if max_lag < len(corr):
                lag = min_lag + int(np.argmax(corr[min_lag:max_lag]))
                if corr[lag] > 0.3 * corr[0]:
                    f0_estimates.append(float(ds_sr / lag))

        avg_f0 = float(np.median(f0_estimates)) if f0_estimates else 135.0
        is_female = avg_f0 > 165.0
        gender = "female" if is_female else "male"
        base_f0 = 210.0 if is_female else 135.0

        pitch_factor = round(max(0.75, min(1.35, avg_f0 / base_f0)), 2)
        pitch_hz_offset = int(round(avg_f0 - base_f0))

        return {
            "estimated_f0": round(avg_f0, 1),
            "gender": gender,
            "pitch_factor": pitch_factor,
            "pitch_hz_offset": pitch_hz_offset,
        }
    except Exception:
        return {
            "estimated_f0": 135.0,
            "gender": "male",
            "pitch_factor": 1.0,
            "pitch_hz_offset": 0,
        }
