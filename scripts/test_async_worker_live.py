"""Live verification script for Vocara Asynchronous Background Worker with Redis & Azure Storage."""

import asyncio
import sys
import uuid
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from dotenv import load_dotenv

# Load backend/.env
env_file = Path(__file__).resolve().parent.parent / "backend" / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from vocara.container import Container
from vocara.core.config import get_settings
from vocara.domain.entities import Job, Voice
from vocara.domain.enums import AudioFormat, JobStatus, JobType, VoiceType, VoiceVisibility
from vocara.worker.handler import Worker


async def run_live_worker_test():
    settings = get_settings()
    print("=" * 65)
    print(" VOCARA ASYNCHRONOUS WORKER LIVE PIPELINE TEST")
    print("=" * 65)
    print(f"[*] Database:       {str(settings.DATABASE_URL).split('@')[-1]}")
    print(f"[*] Redis Queue:    {settings.REDIS_URL}")
    print(f"[*] Storage:        {settings.STORAGE_BACKEND} ({settings.AZURE_STORAGE_CONTAINER_NAME})")
    print(f"[*] Inference:      {settings.INFERENCE_ENGINE_TYPE}")
    print("-" * 65)

    container = Container(settings)
    await container.initialize()

    test_job_id = f"job_live_{uuid.uuid4().hex[:10]}"
    owner_id = "dev_worker_verification_owner"

    try:
        # 1. Resolve an accessible test voice dynamically from PostgreSQL
        async with container.session_factory() as session:
            voice_repo = container.get_voice_repo(session)
            accessible = await voice_repo.list_accessible_voices(owner_id=owner_id, limit=1)
            voice = accessible[0] if accessible else None
            if not voice:
                voice = Voice(
                    id=f"voice-worker-test-{uuid.uuid4().hex[:8]}",
                    name="Worker Test Voice",
                    voice_type=VoiceType.BUILT_IN,
                    owner_id=None,
                    language="km-KH",
                    visibility=VoiceVisibility.PUBLIC,
                    description="Standard test voice.",
                )
                await voice_repo.create(voice)
                await session.commit()
            test_voice_id = voice.id
            print(f"[1] Verified target voice: {voice.name} ({voice.id})")

            # 2. Insert queued job into PostgreSQL
            job_repo = container.get_job_repo(session)
            test_text = "ជំរាបសួរ! នេះជាការសាកល្បងប្រព័ន្ធបំប្លែងសំឡេងខេមរភាសាស្វ័យប្រវត្តិតាមរយៈ Background Worker និង Redis។"
            new_job = Job(
                id=test_job_id,
                job_type=JobType.TTS_BATCH,
                status=JobStatus.QUEUED,
                owner_id=owner_id,
                voice_id=voice.id,
                input_text=test_text,
                char_count=len(test_text),
                language="km",
                speed=1.0,
                output_format=AudioFormat.MP3,
                audio_duration_seconds=0.0,
                metadata={},
            )
            await job_repo.create(new_job)
            await session.commit()
            print(f"[2] Created Job in PostgreSQL: {new_job.id} (status: {new_job.status.value})")

        # 3. Enqueue job into live Redis queue
        payload = {
            "job_id": test_job_id,
            "owner_id": owner_id,
            "action": "tts_batch",
        }
        enqueued_id = await container.job_queue.enqueue(settings.WORKER_QUEUE_NAME, payload)
        print(f"[3] Enqueued task to Redis queue '{settings.WORKER_QUEUE_NAME}': {enqueued_id}")

        # 4. Initialize and run Worker on the enqueued job
        print("[4] Initializing Worker to dequeue and process...")
        worker = Worker(container)
        dequeued_payload = await container.job_queue.dequeue(settings.WORKER_QUEUE_NAME, timeout_seconds=3)
        assert dequeued_payload is not None, "Failed to dequeue payload from Redis!"
        print(f"[+] Worker successfully received payload for Job: {dequeued_payload['job_id']}")

        # 5. Process job
        print("[5] Executing speech synthesis & cloud upload via Worker...")
        success = await worker.process_job_payload(dequeued_payload)
        assert success is True, "Worker processing failed!"
        print("[+] Worker processed task successfully!")

        # 6. Verify job updated in PostgreSQL
        async with container.session_factory() as session:
            job_repo = container.get_job_repo(session)
            completed_job = await job_repo.get_by_id(test_job_id)
            assert completed_job is not None
            assert completed_job.status == JobStatus.COMPLETED
            print(f"[6] PostgreSQL Status: {completed_job.status.value}")
            print(f"[+] Audio Duration:    {completed_job.audio_duration_seconds:.2f} s")
            print(f"[+] Storage Key:       {completed_job.output_audio_key}")

        # 7. Verify audio artifact in Azure Blob Storage
        audio_bytes = await container.storage.download(completed_job.output_audio_key)
        print(f"[7] Azure Blob Storage Download: Verified {len(audio_bytes)} bytes downloaded")
        sas_url = await container.storage.get_download_url(completed_job.output_audio_key, expires_in_seconds=3600)
        print(f"[+] Playable SAS URL:  {sas_url[:80]}...")

        print("-" * 65)
        print(" ASYNCHRONOUS WORKER END-TO-END VERIFICATION: 100% SUCCESS")
        print("=" * 65)

    finally:
        await container.shutdown()


if __name__ == "__main__":
    asyncio.run(run_live_worker_test())
