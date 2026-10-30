"""Cryptographic security utilities for API key generation and validation."""

import hashlib
import hmac
import secrets


def generate_api_key(is_live: bool = True) -> tuple[str, str, str]:
    """Generate a high-entropy developer API key.

    Returns:
        tuple[raw_key, key_prefix, hashed_secret]:
            - raw_key: Returned once to developer (e.g. voc_live_a1b2c3d4e5...)
            - key_prefix: Stored in DB for fast indexed lookup (e.g. voc_live_a1b2c3d4)
            - hashed_secret: Salted HMAC-SHA256 digest stored in DB
    """
    env_tag = "live" if is_live else "test"
    random_token = secrets.token_urlsafe(32)
    raw_key = f"voc_{env_tag}_{random_token}"
    # Prefix is first 16 characters including tag
    key_prefix = raw_key[:16]
    return raw_key, key_prefix, ""


def hash_api_key(raw_key: str, salt: str) -> str:
    """Compute HMAC-SHA256 digest of an API key using the application salt."""
    return hmac.new(
        salt.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str, salt: str) -> bool:
    """Verify an API key in constant time to prevent timing attacks."""
    calculated_hash = hash_api_key(raw_key, salt)
    return secrets.compare_digest(calculated_hash, stored_hash)
