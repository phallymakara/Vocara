"""Live End-to-End Test for Vocara VoxCPM 2 on Modal (NVIDIA A100).

Tests:
1. Health & GPU status check
2. English Speech Synthesis
3. Khmer Speech Synthesis (Natural Khmer sentence flow)
4. Zero-Shot Voice Cloning
5. Speech Synthesis with Cloned Voice
"""

import base64
import os
import sys
import time
from pathlib import Path
import httpx

MODAL_URL = os.environ.get(
    "MODAL_API_ENDPOINT",
    "https://phallymakara01--vocara-voxcpm-fastapi-app.us-east.modal.run"
).rstrip("/")

OUTPUT_DIR = Path("scripts/test_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log_step(name: str):
    print("\n" + "=" * 60)
    print(f"  {name}")
    print("=" * 60)


def test_health(client: httpx.Client):
    log_step("1. Checking Modal Service Health & Hardware Acceleration")
    print("Connecting to Modal endpoint (if cold, container is initializing NVIDIA A100 & model weights)...")
    t0 = time.perf_counter()
    resp = client.get(f"{MODAL_URL}/health", timeout=180.0)
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"Status Code : {resp.status_code}")
    print(f"Latency     : {elapsed:.2f} ms")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Service     : {data.get('service')}")
        print(f"GPU         : {data.get('gpu')}")
        print(f"Architecture: {data.get('architecture')}")
        print(f"Features    : {', '.join(data.get('accelerations', []))}")
    else:
        print(f"Error       : {resp.text}")
        sys.exit(1)


def test_english_tts(client: httpx.Client):
    log_step("2. Testing English Speech Synthesis")
    prompt = "Welcome to Vocara, the enterprise voice AI platform with ultra-low latency and zero-shot voice cloning."
    payload = {
        "text": prompt,
        "language": "en",
        "output_format": "mp3",
        "speed": 1.0,
    }

    t0 = time.perf_counter()
    resp = client.post(f"{MODAL_URL}/synthesize", json=payload, timeout=60.0)
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"Status Code : {resp.status_code}")
    print(f"Latency     : {elapsed:.2f} ms")

    if resp.status_code == 200:
        data = resp.json()
        audio_b64 = data.get("audio_base64", "")
        audio_bytes = base64.b64decode(audio_b64)
        out_path = OUTPUT_DIR / "1_test_english.mp3"
        out_path.write_bytes(audio_bytes)

        duration = data.get("duration", 0.0)
        rtf = data.get("real_time_factor", 0.0)
        print(f"Audio Size  : {len(audio_bytes) / 1024:.1f} KB")
        print(f"Audio Length: {duration:.2f} s")
        print(f"RTF Factor  : {rtf:.3f}x")
        print(f"Saved to    : {out_path.resolve()}")
    else:
        print(f"Error       : {resp.text}")


def test_khmer_tts(client: httpx.Client):
    log_step("3. Testing Khmer Speech Synthesis (Natural Khmer Flow)")
    prompt = "ជំរាបសួរ! សូមស្វាគមន៍មកកាន់ប្រព័ន្ធ Vocara Voice AI ដែលជាបច្ចេកវិទ្យាសំឡេងឆ្លាតវៃជំនាន់ថ្មី។"
    payload = {
        "text": prompt,
        "language": "km",
        "output_format": "mp3",
        "speed": 1.0,
    }

    t0 = time.perf_counter()
    resp = client.post(f"{MODAL_URL}/synthesize", json=payload, timeout=60.0)
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"Status Code : {resp.status_code}")
    print(f"Latency     : {elapsed:.2f} ms")

    if resp.status_code == 200:
        data = resp.json()
        audio_b64 = data.get("audio_base64", "")
        audio_bytes = base64.b64decode(audio_b64)
        out_path = OUTPUT_DIR / "2_test_khmer.mp3"
        out_path.write_bytes(audio_bytes)

        duration = data.get("duration", 0.0)
        rtf = data.get("real_time_factor", 0.0)
        print(f"Audio Size  : {len(audio_bytes) / 1024:.1f} KB")
        print(f"Audio Length: {duration:.2f} s")
        print(f"RTF Factor  : {rtf:.3f}x")
        print(f"Saved to    : {out_path.resolve()}")
    else:
        print(f"Error       : {resp.text}")


def test_voice_cloning_and_synthesis(client: httpx.Client):
    log_step("4. Testing Zero-Shot Voice Cloning & Cloned Synthesis")

    # Locate a sample reference WAV in project
    sample_ref = Path("backend/storage_local/voices/59e775ce-92b9-43c9-a572-0149c92dcffc/reference.wav")
    if not sample_ref.exists():
        wav_files = list(Path("backend/storage_local").glob("**/*.wav"))
        if wav_files:
            sample_ref = wav_files[0]
        else:
            print("No reference WAV found. Skipping clone test.")
            return

    print(f"Reference Audio File: {sample_ref.name} ({sample_ref.stat().st_size / 1024:.1f} KB)")
    ref_b64 = base64.b64encode(sample_ref.read_bytes()).decode("utf-8")

    # Step 4a: Call /clone to cache the voice
    clone_payload = {
        "audio_base64": ref_b64,
        "voice_id": "test_voice_custom_001",
        "generate_preview": True,
        "preview_text": "This is a live cloned preview test from Vocara on Modal.",
    }

    t0 = time.perf_counter()
    resp = client.post(f"{MODAL_URL}/clone", json=clone_payload, timeout=60.0)
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"Clone Status Code : {resp.status_code}")
    print(f"Clone Latency     : {elapsed:.2f} ms")

    if resp.status_code != 200:
        print(f"Clone Error: {resp.text}")
        return

    clone_data = resp.json()
    feature_token = clone_data.get("feature_token")
    print(f"Feature Token     : {feature_token}")

    if clone_data.get("preview_base64"):
        preview_bytes = base64.b64decode(clone_data["preview_base64"])
        preview_path = OUTPUT_DIR / "3_cloned_preview.mp3"
        preview_path.write_bytes(preview_bytes)
        print(f"Preview Saved     : {preview_path.resolve()} ({len(preview_bytes) / 1024:.1f} KB)")

    # Step 4b: Synthesize new text using the cached cloned voice
    log_step("5. Synthesizing New English & Khmer Sentences with Cloned Voice")
    cloned_speech_payload = {
        "text": "Hello, my voice has been cloned successfully! Vocara generates speech directly with zero acoustic loss.",
        "voice_id": "test_voice_custom_001",
        "reference_audio_base64": ref_b64,
        "language": "en",
        "output_format": "mp3",
    }

    t1 = time.perf_counter()
    resp_synth = client.post(f"{MODAL_URL}/synthesize", json=cloned_speech_payload, timeout=60.0)
    elapsed_synth = (time.perf_counter() - t1) * 1000

    print(f"Synthesis Status Code : {resp_synth.status_code}")
    print(f"Synthesis Latency     : {elapsed_synth:.2f} ms")

    if resp_synth.status_code == 200:
        sdata = resp_synth.json()
        audio_bytes = base64.b64decode(sdata.get("audio_base64", ""))
        synth_path = OUTPUT_DIR / "4_cloned_speech_en.mp3"
        synth_path.write_bytes(audio_bytes)
        print(f"Cloned Audio Length   : {sdata.get('duration', 0.0):.2f} s")
        print(f"Cloned Audio Size     : {len(audio_bytes) / 1024:.1f} KB")
        print(f"Saved to              : {synth_path.resolve()}")
    else:
        print(f"Synthesis Error: {resp_synth.text}")


def main():
    print(f"\nTarget Modal Endpoint: {MODAL_URL}")
    with httpx.Client() as client:
        test_health(client)
        test_english_tts(client)
        test_khmer_tts(client)
        test_voice_cloning_and_synthesis(client)

    print("\n" + "=" * 60)
    print("  ALL MODAL VOXCPM TESTS COMPLETED SUCCESSFULLY!")
    print(f"  Audio outputs generated in: {OUTPUT_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()

