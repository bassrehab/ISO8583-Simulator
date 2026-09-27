"""Block cipher primitives shared by the PIN block and MAC modules."""

from __future__ import annotations

from typing import Any

# subhadipmitra@: cryptography is an optional dependency (the security extra), so a missing
# package is reported when a function is called, not when iso8583sim is imported.
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    try:
        # subhadipmitra@: cryptography 43+ moved TripleDES to the "decrepit" module because
        # DES is legacy crypto. Payment networks still require it, so import it from there
        # and fall back to the old location for older releases.
        from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
    except ImportError:  # pragma: no cover - depends on the installed cryptography version
        TripleDES = algorithms.TripleDES  # type: ignore[misc]

    _CRYPTO_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the extra
    _CRYPTO_AVAILABLE = False


class SecurityError(ValueError):
    """Raised for invalid keys, PINs, PANs or blocks."""


def _require_crypto() -> None:
    if not _CRYPTO_AVAILABLE:
        raise SecurityError("This feature needs the security extra: pip install 'iso8583sim[security]'")


def parse_key(key: str | bytes, allowed_lengths: tuple[int, ...]) -> bytes:
    """Accept a key as bytes or hex and check its length.

    Args:
        key: Key as raw bytes or a hex string
        allowed_lengths: Permitted key lengths in bytes

    Returns:
        The key as bytes
    """
    if isinstance(key, str):
        try:
            key = bytes.fromhex(key)
        except ValueError:
            raise SecurityError("Key must be bytes or a hex string") from None
    if len(key) not in allowed_lengths:
        lengths = ", ".join(str(n * 8) for n in allowed_lengths)
        raise SecurityError(f"Key must be {lengths} bits, got {len(key) * 8}")
    return key


def _ecb(algorithm: Any, block: bytes, decrypt: bool) -> bytes:
    _require_crypto()
    # subhadipmitra@: ECB on a single block is the raw block cipher operation. The PIN block
    # and MAC algorithms build their own chaining on top of it, as the ISO standards define.
    cipher = Cipher(algorithm, modes.ECB())
    op = cipher.decryptor() if decrypt else cipher.encryptor()
    return op.update(block) + op.finalize()


def tdes(key: bytes, block: bytes, decrypt: bool = False) -> bytes:
    """Triple DES on one 8-byte block. An 8-byte key gives single DES (K1 = K2 = K3)."""
    # subhadipmitra@: Single DES is expressed as TDES with the same key three times, since
    # EDE with identical keys reduces to one DES operation. This keeps one code path for
    # the retail MAC, which needs both.
    if len(key) == 8:
        key = key * 3
    # subhadipmitra@: A double length key K1K2 is the same cipher as the triple length key
    # K1K2K1. Expanding it here avoids cryptography's deprecation warning for 16-byte keys,
    # which are still the norm for payment keys.
    elif len(key) == 16:
        key = key + key[:8]
    return _ecb(TripleDES(key), block, decrypt)


def aes(key: bytes, block: bytes, decrypt: bool = False) -> bytes:
    """AES on one 16-byte block."""
    return _ecb(algorithms.AES(key), block, decrypt)


def xor(a: bytes, b: bytes) -> bytes:
    """XOR two equal-length byte strings."""
    return bytes(x ^ y for x, y in zip(a, b, strict=True))
