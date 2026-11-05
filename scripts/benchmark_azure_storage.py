"""Benchmark latency for Azure Blob Storage operations (Upload, SAS, Download, Delete)."""

import asyncio
import time
import os
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from vocara.infrastructure.storage.azure import AzureBlobStorageAdapter


async def run_benchmark():
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    if not conn_str:
        # Check backend/.env
        env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("AZURE_STORAGE_CONNECTION_STRING=") and not line.startswith("#"):
                    conn_str = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not conn_str:
        print("[ERROR] AZURE_STORAGE_CONNECTION_STRING is not set in backend/.env or environment.")
        print("Please add your Azure Storage connection string to backend/.env to run this live benchmark.")
        return

    container_name = "vocara-benchmark"
    print("=" * 60)
    print(" VOCARA AZURE BLOB STORAGE LATENCY BENCHMARK")
    print("=" * 60)

    # 1. Connection & Container Setup
    t0 = time.perf_counter()
    adapter = AzureBlobStorageAdapter(conn_str, container_name)
    init_latency_ms = (time.perf_counter() - t0) * 1000
    print(f"[*] Account Name: {adapter.account_name}")
    print(f"[*] Container:    {adapter.container_name}")
    print(f"[*] Client Init:  {init_latency_ms:.2f} ms")

    # Generate sample 100 KB MP3 audio payload
    sample_payload = b"\xff\xfb\x90\x64" + (b"\x00" * 102400)
    file_key = f"benchmarks/audio_test_{int(time.time())}.mp3"

    # 2. Upload Latency
    t0 = time.perf_counter()
    uploaded_key = await adapter.upload(file_key, sample_payload, content_type="audio/mpeg")
    upload_latency_ms = (time.perf_counter() - t0) * 1000
    print(f"[+] Audio Upload (100 KB): {upload_latency_ms:.2f} ms")

    # 3. SAS URL Generation (Critical for fast streaming response)
    t0 = time.perf_counter()
    sas_url = await adapter.get_download_url(uploaded_key, expires_in_seconds=3600)
    sas_latency_ms = (time.perf_counter() - t0) * 1000
    print(f"[+] SAS Token Generation: {sas_latency_ms:.2f} ms (In-memory HMAC signature)")
    print(f"    Preview URL: {sas_url[:80]}...")

    # 4. Download Latency
    t0 = time.perf_counter()
    downloaded_bytes = await adapter.download(uploaded_key)
    download_latency_ms = (time.perf_counter() - t0) * 1000
    print(f"[+] Audio Download ({len(downloaded_bytes)} bytes): {download_latency_ms:.2f} ms")

    # 5. Cleanup / Delete Latency
    t0 = time.perf_counter()
    deleted = await adapter.delete(uploaded_key)
    delete_latency_ms = (time.perf_counter() - t0) * 1000
    print(f"[+] Audio Cleanup: {delete_latency_ms:.2f} ms (Success: {deleted})")

    print("-" * 60)
    print(" SUMMARY ASSESSMENT:")
    if upload_latency_ms < 150:
        print(f" EXCELLENT: Total Roundtrip Latency is very fast ({upload_latency_ms:.1f} ms)!")
    elif upload_latency_ms < 400:
        print(f" GOOD: Acceptable cloud storage latency ({upload_latency_ms:.1f} ms).")
    else:
        print(f" NOTICE: Latency is {upload_latency_ms:.1f} ms (check if region is near Southeast Asia).")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_benchmark())

