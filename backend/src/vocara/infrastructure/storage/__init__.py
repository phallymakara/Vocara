"""Storage adapters package."""

from vocara.infrastructure.storage.azure import AzureBlobStorageAdapter
from vocara.infrastructure.storage.local import LocalStorageAdapter

__all__ = ["AzureBlobStorageAdapter", "LocalStorageAdapter"]
