"""Azure Blob Storage adapter implementing BlobStorage port."""

import asyncio
from datetime import datetime, timedelta, timezone

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)

from vocara.core.exceptions import EntityNotFoundError
from vocara.domain.ports import BlobStorage


class AzureBlobStorageAdapter(BlobStorage):
    """Production object storage adapter backed by Microsoft Azure Blob Storage."""

    def __init__(self, connection_string: str, container_name: str = "vocara-audio") -> None:
        """Initialize Azure Blob Storage client and verify/create target container."""
        if not connection_string:
            raise ValueError("Azure storage connection string cannot be empty.")

        self.connection_string = connection_string
        self.container_name = container_name
        self.service_client = BlobServiceClient.from_connection_string(
            connection_string,
            logging_enable=False,
        )
        self.container_client = self.service_client.get_container_client(container_name)

        self.account_name = self.service_client.account_name
        # Extract account key for generating Shared Access Signatures (SAS)
        self.account_key = getattr(self.service_client.credential, "account_key", None)
        self.endpoint = self.service_client.primary_endpoint.rstrip("/")

        self._ensure_container_exists()

    def _ensure_container_exists(self) -> None:
        """Create target container if it does not already exist."""
        try:
            self.container_client.create_container()
        except ResourceExistsError:
            pass
        except Exception:
            # Let caller continue if container already exists or permissions restrict creation
            pass

    async def upload(self, file_key: str, data: bytes, content_type: str = "audio/mpeg") -> str:
        """Upload audio artifact to Azure Blob Storage asynchronously."""
        clean_key = file_key.lstrip("/")
        blob_client = self.container_client.get_blob_client(clean_key)
        content_settings = ContentSettings(content_type=content_type)

        def _upload() -> None:
            blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)

        await asyncio.to_thread(_upload)
        return clean_key

    async def download(self, file_key: str) -> bytes:
        """Download binary audio bytes from Azure Blob Storage."""
        clean_key = file_key.lstrip("/")
        blob_client = self.container_client.get_blob_client(clean_key)

        def _download() -> bytes:
            try:
                stream = blob_client.download_blob()
                return stream.readall()
            except ResourceNotFoundError:
                raise EntityNotFoundError(
                    f"Stored file '{clean_key}' does not exist in Azure Blob Storage."
                )

        return await asyncio.to_thread(_download)

    async def get_download_url(self, file_key: str, expires_in_seconds: int = 3600) -> str:
        """Generate a time-limited Shared Access Signature (SAS) URL for audio streaming/playback."""
        clean_key = file_key.lstrip("/")

        if not self.account_key:
            # Fallback to direct public endpoint if account key is not accessible
            return f"{self.endpoint}/{self.container_name}/{clean_key}"

        def _generate_sas() -> str:
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=clean_key,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds),
            )
            return f"{self.endpoint}/{self.container_name}/{clean_key}?{sas_token}"

        return await asyncio.to_thread(_generate_sas)

    async def delete(self, file_key: str) -> bool:
        """Delete an audio artifact from Azure Blob Storage."""
        clean_key = file_key.lstrip("/")
        blob_client = self.container_client.get_blob_client(clean_key)

        def _delete() -> bool:
            try:
                blob_client.delete_blob()
                return True
            except ResourceNotFoundError:
                return False

        return await asyncio.to_thread(_delete)

