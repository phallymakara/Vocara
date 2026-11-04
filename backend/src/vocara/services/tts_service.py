"""Text-to-Speech (TTS) synthesis service with dynamic real-time and async routing."""

from vocara.core.exceptions import VoiceNotFoundError
from vocara.domain.entities import ApiKey, Job
from vocara.domain.enums import AudioFormat, JobType, VoiceVisibility
from vocara.domain.ports import InferenceEngine, VoiceRepository
from vocara.services.job_service import JobService
from vocara.services.usage_service import UsageService

ASYNC_CHAR_THRESHOLD = 2000


class TtsService:
    """Coordinates TTS synthesis with dynamic routing between instant streaming
    and background jobs.
    """

    def __init__(
        self,
        voice_repo: VoiceRepository,
        usage_service: UsageService,
        inference_engine: InferenceEngine,
        job_service: JobService,
        async_char_threshold: int = ASYNC_CHAR_THRESHOLD,
    ) -> None:
        self.voice_repo = voice_repo
        self.usage_service = usage_service
        self.inference_engine = inference_engine
        self.job_service = job_service
        self.async_char_threshold = async_char_threshold

    async def synthesize_or_enqueue(
        self,
        api_key: ApiKey,
        text: str,
        voice_id: str,
        language: str = "km-KH",
        speed: float = 1.0,
        output_format: AudioFormat = AudioFormat.MP3,
        async_only: bool = False,
    ) -> tuple[bytes | None, float, str, Job | None]:
        """Process TTS request with real-time stream or asynchronous background job dispatch.

        Returns:
            tuple[audio_bytes, duration_seconds, format, job_entity]:
                - If synchronous: audio_bytes and duration are populated, job is None.
                - If asynchronous: audio_bytes is None, job entity is populated.
        """
        char_count = len(text)

        # 1. Enforce monthly quota before executing
        self.usage_service.check_quota(api_key=api_key, chars_needed=char_count)

        # 2. Verify voice exists and is accessible
        voice = await self.voice_repo.get_by_id(voice_id)
        if not voice or not voice.is_active:
            raise VoiceNotFoundError(voice_id)

        if voice.visibility == VoiceVisibility.PRIVATE and voice.owner_id != api_key.owner_id:
            raise VoiceNotFoundError(voice_id)

        # 3. Dynamic routing decision
        is_async = async_only or (char_count >= self.async_char_threshold)

        if not is_async:
            # Synchronous Real-Time Generation
            audio_bytes, duration = await self.inference_engine.generate_speech(
                text=text,
                voice=voice,
                language=language,
                speed=speed,
                output_format=output_format,
            )

            # Record character usage
            await self.usage_service.record_usage(
                api_key=api_key,
                operation="tts_realtime",
                characters=char_count,
                duration_seconds=duration,
            )

            return audio_bytes, duration, output_format.value, None

        # Asynchronous Background Processing
        job = await self.job_service.create_job(
            owner_id=api_key.owner_id,
            job_type=JobType.TTS_BATCH,
            voice_id=voice_id,
            input_text=text,
            language=language,
            speed=speed,
            output_format=output_format,
        )

        # Reserve/meter quota for the dispatched job
        await self.usage_service.record_usage(
            api_key=api_key,
            operation="tts_batch",
            characters=char_count,
            duration_seconds=0.0,
            job_id=job.id,
        )

        return None, 0.0, output_format.value, job
