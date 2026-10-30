"""Redis-backed queue adapter with in-memory fallback for async job dispatching."""

import asyncio
import json
from collections import defaultdict
from typing import Any

import structlog

from vocara.domain.ports import JobQueue

logger = structlog.get_logger("vocara.queue")


class RedisJobQueue(JobQueue):
    """Job queue implementation supporting Redis with in-memory fallback."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url
        self._redis_client: Any = None
        self._memory_queues: dict[str, list[str]] = defaultdict(list)

    async def _get_client(self) -> Any:
        if self._redis_client is None and self.redis_url:
            try:
                import redis.asyncio as aioredis

                client = aioredis.from_url(self.redis_url, decode_responses=True)
                # Test ping
                await client.ping()
                self._redis_client = client
                logger.info("redis_connected", url=self.redis_url)
            except Exception as err:
                logger.warning("redis_unavailable_fallback_to_memory", error=str(err))
                self._redis_client = False
        return self._redis_client

    async def enqueue(self, queue_name: str, payload: dict[str, Any]) -> str:
        """Serialize and push job payload to queue."""
        data_str = json.dumps(payload)
        client = await self._get_client()

        if client:
            await client.rpush(queue_name, data_str)
        else:
            self._memory_queues[queue_name].append(data_str)

        task_id = payload.get("job_id", "unknown")
        logger.info("job_enqueued", queue=queue_name, job_id=task_id)
        return str(task_id)

    async def dequeue(self, queue_name: str, timeout_seconds: int = 10) -> dict[str, Any] | None:
        """Pop next job payload from queue."""
        client = await self._get_client()

        if client:
            result = await client.blpop([queue_name], timeout=timeout_seconds)
            if result:
                _, raw_data = result
                return json.loads(raw_data)  # type: ignore[no-any-return]
            return None

        # In-memory dequeue with simulated polling
        poll_interval = 0.1
        elapsed = 0.0
        while elapsed < timeout_seconds:
            if self._memory_queues[queue_name]:
                raw_data = self._memory_queues[queue_name].pop(0)
                return json.loads(raw_data)  # type: ignore[no-any-return]
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return None
