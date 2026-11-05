"""Unit tests for AzureBlobStorageAdapter."""

from unittest.mock import MagicMock, patch
import pytest

from azure.core.exceptions import ResourceNotFoundError
from vocara.core.exceptions import EntityNotFoundError
from vocara.infrastructure.storage.azure import AzureBlobStorageAdapter


DUMMY_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=https;AccountName=teststorageaccount;"
    "AccountKey=dGVzdGtleTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=;EndpointSuffix=core.windows.net"
)


@pytest.fixture
def mock_azure_client():
    """Mock BlobServiceClient to isolate tests from real network calls."""
    with patch("vocara.infrastructure.storage.azure.BlobServiceClient") as mock_bsc:
        client_instance = MagicMock()
        client_instance.account_name = "teststorageaccount"
        client_instance.primary_endpoint = "https://teststorageaccount.blob.core.windows.net/"
        client_instance.credential.account_key = "dGVzdGtleTEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI="

        container_mock = MagicMock()
        client_instance.get_container_client.return_value = container_mock
        mock_bsc.from_connection_string.return_value = client_instance

        yield {
            "bsc": mock_bsc,
            "client": client_instance,
            "container": container_mock,
        }


def test_init_validates_connection_string():
    """Should reject empty connection string."""
    with pytest.raises(ValueError, match="connection string cannot be empty"):
        AzureBlobStorageAdapter("")


def test_init_ensures_container(mock_azure_client):
    """Should attempt to create container on startup."""
    adapter = AzureBlobStorageAdapter(DUMMY_CONNECTION_STRING, "vocara-audio")
    assert adapter.container_name == "vocara-audio"
    assert adapter.account_name == "teststorageaccount"
    mock_azure_client["container"].create_container.assert_called_once()


@pytest.mark.asyncio
async def test_upload(mock_azure_client):
    """Should upload binary data to blob client with correct content type."""
    blob_mock = MagicMock()
    mock_azure_client["container"].get_blob_client.return_value = blob_mock

    adapter = AzureBlobStorageAdapter(DUMMY_CONNECTION_STRING, "vocara-audio")
    key = await adapter.upload("audio/test.mp3", b"ID3fakebytes", content_type="audio/mpeg")

    assert key == "audio/test.mp3"
    mock_azure_client["container"].get_blob_client.assert_called_with("audio/test.mp3")
    blob_mock.upload_blob.assert_called_once()
    assert blob_mock.upload_blob.call_args[0][0] == b"ID3fakebytes"


@pytest.mark.asyncio
async def test_download_success(mock_azure_client):
    """Should download and return audio bytes."""
    blob_mock = MagicMock()
    download_stream = MagicMock()
    download_stream.readall.return_value = b"sample_audio_data"
    blob_mock.download_blob.return_value = download_stream
    mock_azure_client["container"].get_blob_client.return_value = blob_mock

    adapter = AzureBlobStorageAdapter(DUMMY_CONNECTION_STRING, "vocara-audio")
    data = await adapter.download("audio/test.mp3")

    assert data == b"sample_audio_data"


@pytest.mark.asyncio
async def test_download_not_found(mock_azure_client):
    """Should raise EntityNotFoundError when blob does not exist."""
    blob_mock = MagicMock()
    blob_mock.download_blob.side_effect = ResourceNotFoundError("Blob not found")
    mock_azure_client["container"].get_blob_client.return_value = blob_mock

    adapter = AzureBlobStorageAdapter(DUMMY_CONNECTION_STRING, "vocara-audio")
    with pytest.raises(EntityNotFoundError, match="does not exist"):
        await adapter.download("audio/missing.mp3")


@pytest.mark.asyncio
async def test_get_download_url(mock_azure_client):
    """Should return SAS URL containing valid token parameters."""
    adapter = AzureBlobStorageAdapter(DUMMY_CONNECTION_STRING, "vocara-audio")
    url = await adapter.get_download_url("audio/output.mp3", expires_in_seconds=1800)

    assert url.startswith("https://teststorageaccount.blob.core.windows.net/vocara-audio/audio/output.mp3?")
    assert "sp=r" in url
    assert "sig=" in url


@pytest.mark.asyncio
async def test_delete_success(mock_azure_client):
    """Should delete blob and return True."""
    blob_mock = MagicMock()
    mock_azure_client["container"].get_blob_client.return_value = blob_mock

    adapter = AzureBlobStorageAdapter(DUMMY_CONNECTION_STRING, "vocara-audio")
    result = await adapter.delete("audio/delete_me.mp3")

    assert result is True
    blob_mock.delete_blob.assert_called_once()


@pytest.mark.asyncio
async def test_delete_not_found(mock_azure_client):
    """Should return False when deleting non-existent blob."""
    blob_mock = MagicMock()
    blob_mock.delete_blob.side_effect = ResourceNotFoundError("Not found")
    mock_azure_client["container"].get_blob_client.return_value = blob_mock

    adapter = AzureBlobStorageAdapter(DUMMY_CONNECTION_STRING, "vocara-audio")
    result = await adapter.delete("audio/missing.mp3")

    assert result is False
