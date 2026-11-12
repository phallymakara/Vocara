"""Cryptographic security utilities for API keys, passwords, and JWT sessions."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


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


def hash_password(password: str) -> str:
    """Hash a user password with scrypt and a per-user random salt."""
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored scrypt hash in constant time."""
    try:
        algo, salt_hex, hash_hex = stored_hash.split("$", 2)
        if algo != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False

    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=len(expected),
    )
    return secrets.compare_digest(derived, expected)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def create_access_token(
    subject: str,
    email: str,
    secret: str,
    expires_minutes: int = 10080,
) -> str:
    """Create a signed HS256 JWT access token for an authenticated user."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "email": email,
        "iat": now,
        "exp": now + (expires_minutes * 60),
        "type": "session",
    }
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(sig)}"


def verify_access_token(token: str, secret: str) -> dict[str, Any] | None:
    """Verify an HS256 JWT access token and return its payload if valid and unexpired."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        encoded_header, encoded_payload, encoded_sig = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _b64url_decode(encoded_sig)
        if not secrets.compare_digest(provided_sig, expected_sig):
            return None

        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("type") != "session":
            return None
        exp = int(payload.get("exp", 0))
        if exp <= int(time.time()):
            return None
        return payload
    except Exception:
        return None


def create_oauth_state(secret: str, ttl_seconds: int = 600) -> str:
    """Create a short-lived signed OAuth state parameter to prevent CSRF."""
    payload = {"nonce": secrets.token_urlsafe(16), "exp": int(time.time()) + ttl_seconds}
    encoded = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64url_encode(sig)}"


def verify_oauth_state(state: str, secret: str) -> bool:
    """Verify a signed OAuth state parameter."""
    try:
        encoded, encoded_sig = state.split(".", 1)
        expected_sig = hmac.new(
            secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256
        ).digest()
        if not secrets.compare_digest(_b64url_decode(encoded_sig), expected_sig):
            return False
        payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
        return int(payload.get("exp", 0)) > int(time.time())
    except Exception:
        return False
