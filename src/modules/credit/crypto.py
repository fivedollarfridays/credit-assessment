"""Field-level encryption for sensitive data at rest."""

from __future__ import annotations

import base64
import functools
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Fixed salt — changing this invalidates all existing ciphertexts.
# Identical passphrases will derive identical keys across all environments.
# For per-record salting, store salt alongside ciphertext (future work).
_KDF_SALT = b"credit-assessment-webhook-v1"
_KDF_ITERATIONS = 600_000


# LRU cache retains derived key material in memory for the process lifetime.
# Acceptable tradeoff: avoids re-deriving PBKDF2 on every call; key count is
# bounded by maxsize. Clear via _get_fernet.cache_clear() if needed.
@functools.lru_cache(maxsize=4)
def _get_fernet(passphrase: str) -> Fernet:
    """Return a cached Fernet instance derived via PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=SHA256(),
        length=32,
        salt=_KDF_SALT,
        iterations=_KDF_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return Fernet(key)


@functools.lru_cache(maxsize=4)
def _get_legacy_fernet(passphrase: str) -> Fernet:
    """Return a Fernet instance using the old SHA-256 KDF (backward compat)."""
    digest = hashlib.sha256(passphrase.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_field(plaintext: str, key: str | None) -> str:
    """Encrypt a string field. Returns plaintext unchanged if key is None."""
    if key is None:
        return plaintext
    return _get_fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str, key: str | None) -> str:
    """Decrypt a string field. Tries PBKDF2 first, falls back to legacy SHA-256."""
    if key is None:
        return ciphertext
    try:
        return _get_fernet(key).decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Backward compatibility: try legacy SHA-256 KDF
        logger.info("Decrypted using legacy SHA-256 KDF — re-encrypt to migrate")
        return _get_legacy_fernet(key).decrypt(ciphertext.encode()).decode()
