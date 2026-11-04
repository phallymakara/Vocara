"""Background inference job consumer and execution pipeline."""

import asyncio
from typing import Any

import structlog

from vocara.container import Container
from vocara.domain.entities import Voice
from vocara.domain.enums import AudioFormat, JobStatus, VoiceType, VoiceVisibility

logger = structlog.get_logger("vocara.worker")


class Worker:
    """Consumes asynchronous speech synthesis and voice processing jobs from the queue."""

    def __init__(
        self,
        container: Container,
        queue_name: str | None = None,
        poll_timeout: int | None = None,
    ) -> None:
        self.container = container
        self.queue_name = queue_name or container.settings.WORKER_QUEUE_NAME
        self.poll_timeout = poll_timeout or container.settings.WORKER_POLL_TIMEOUT_SECONDS
        self._is_running = False

    async def run_forever(self) -> None:
        """Main loop polling and executing background tasks until stopped."""
        self._is_running = True
        logger.info("worker_started", queue=self.queue_name, poll_timeout=self.poll_timeout)

        while self._is_running:
            try:
                if not self.container.job_queue:
                    await asyncio.sleep(0.5)
                    continue

                payload = await self.container.job_queue.dequeue(
                    self.queue_name, timeout_seconds=self.poll_timeout
                )
                if payload:
                    await self.process_job_payload(payload)

            except asyncio.CancelledError:
                logger.info("worker_cancelled")
                break
            except Exception as err:
                logger.exception("worker_loop_error", error=str(err))
                await asyncio.sleep(0.5)

        logger.info("worker_stopped")

    async def process_job_payload(self, payload: dict[str, Any]) -> bool:
        """Process a single task payload within an isolated database transaction."""
        job_id = payload.get("job_id")
        if not job_id:
            logger.warning("received_payload_without_job_id", payload=payload)
            return False

        log = logger.bind(job_id=job_id)
        log.info("processing_job_started")

        if not self.container.session_factory:
            log.error("session_factory_not_initialized")
            return False

        async with self.container.session_factory() as session:
            job_repo = self.container.get_job_repo(session)
            voice_repo = self.container.get_voice_repo(session)

            job = await job_repo.get_by_id(job_id)
            if not job:
                log.error("job_not_found_in_database")
                return False

            try:
                # Mark status as PROCESSING
                await job_repo.update_status(job_id, JobStatus.PROCESSING)
                await session.commit()

                # Resolve target voice
                voice: Voice | None = None
                if job.voice_id:
                    voice = await voice_repo.get_by_id(job.voice_id)

                if not voice:
                    # Built-in default voice fallback
                    voice = Voice(
                        id="system-fallback-voice",
                        name="Standard Default",
                        voice_type=VoiceType.BUILT_IN,
                        owner_id=None,
                        language=job.language,
                        visibility=VoiceVisibility.PUBLIC,
                    )

                # Execute synthesis via inference engine
                inference = self.container.inference_engine
                if not inference:
                    raise RuntimeError("Inference engine is not available.")

                audio_bytes, duration = await inference.generate_speech(
                    text=job.input_text or "",
                    voice=voice,
                    language=job.language,
                    speed=job.speed,
                    output_format=job.output_format,
                )

                # Upload audio artifact to storage
                storage = self.container.storage
                if not storage:
                    raise RuntimeError("Storage adapter is not configured.")

                ext = "mp3" if job.output_format == AudioFormat.MP3 else job.output_format.value
                output_key = f"jobs/{job_id}/output.{ext}"
                content_type = "audio/mpeg" if ext == "mp3" else f"audio/{ext}"

                await storage.upload(output_key, audio_bytes, content_type=content_type)

                # Mark job as COMPLETED
                await job_repo.update_status(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    output_audio_key=output_key,
                    duration_seconds=duration,
                )
                await session.commit()
                log.info("job_completed_successfully", duration=duration, output_key=output_key)

                # Dispatch webhook notification
                webhook_service = self.container.get_webhook_service(session)
                await webhook_service.dispatch_event(
                    owner_id=job.owner_id,
                    event_type="job.completed",
                    data={
                        "job_id": job.id,
                        "status": "completed",
                        "audio_duration_seconds": duration,
                        "output_audio_key": output_key,
                    },
                )
                return True

            except Exception as err:
                log.exception("job_processing_failed", error=str(err))
                safe_error_msg = f"Audio generation failed: {type(err).__name__}"
                await job_repo.update_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error_message=safe_error_msg,
                )
                await session.commit()

                # Dispatch failure webhook notification
                webhook_service = self.container.get_webhook_service(session)
                await webhook_service.dispatch_event(
                    owner_id=job.owner_id,
                    event_type="job.failed",
                    data={
                        "job_id": job.id,
                        "status": "failed",
                        "error_message": safe_error_msg,
                    },
                )
                return False

    def stop(self) -> None:
        """Signal the worker loop to stop gracefully."""
        self._is_running = False
