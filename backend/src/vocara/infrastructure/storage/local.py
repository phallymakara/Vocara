"""Local filesystem storage adapter implementing BlobStorage port."""

import asyncio
from pathlib import Path

from vocara.core.exceptions import EntityNotFoundError
from vocara.domain.ports import BlobStorage


class LocalStorageAdapter(BlobStorage):
    """File storage adapter storing audio artifacts on the local filesystem."""

    def __init__(self, base_directory: str = "./storage_local") -> None:
        self.base_dir = Path(base_directory).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, file_key: str) -> Path:
        """Resolve and prevent path traversal outside base directory."""
        # Clean relative key
        clean_key = file_key.lstrip("/\\")
        target_path = (self.base_dir / clean_key).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid path traversal attempt for key: {file_key}")
        return target_path

    async def upload(self, file_key: str, data: bytes, content_type: str = "audio/mpeg") -> str:
        """Store bytes to local disk asynchronously."""
        target_path = self._resolve_path(file_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        def _write() -> None:
            target_path.write_bytes(data)

        await asyncio.to_thread(_write)
        return file_key

    async def download(self, file_key: str) -> bytes:
        """Read bytes from local disk."""
        target_path = self._resolve_path(file_key)
        if not target_path.is_file():
            raise EntityNotFoundError(f"Stored file '{file_key}' does not exist.")

        def _read() -> bytes:
            return target_path.read_bytes()

        return await asyncio.to_thread(_read)

    async def get_download_url(self, file_key: str, expires_in_seconds: int = 3600) -> str:
        """Return download reference URL for local file."""
        target_path = self._resolve_path(file_key)
        if not target_path.is_file():
            raise EntityNotFoundError(f"Stored file '{file_key}' does not exist.")
        return f"/api/v1/storage/{file_key}"

    async def delete(self, file_key: str) -> bool:
        """Delete local file."""
        target_path = self._resolve_path(file_key)
        if not target_path.is_file():
            return False

        def _remove() -> None:
            target_path.unlink(missing_ok=True)

        await asyncio.to_thread(_remove)
        return True
