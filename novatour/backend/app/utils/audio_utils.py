"""PCM audio utilities for Nova Sonic voice pipeline."""

import base64
import struct
from typing import bytes as Bytes


def pcm_to_base64(pcm_data: bytes) -> str:
    """Encode raw PCM bytes to base64 string.

    Args:
        pcm_data: Raw PCM audio bytes (16-bit, 16kHz, mono)

    Returns:
        Base64-encoded string
    """
    return base64.b64encode(pcm_data).decode("ascii")


def base64_to_pcm(b64_data: str) -> bytes:
    """Decode base64 string to raw PCM bytes.

    Args:
        b64_data: Base64-encoded audio string

    Returns:
        Raw PCM bytes
    """
    return base64.b64decode(b64_data)


def silence_pcm(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate silent PCM audio.

    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz

    Returns:
        Raw PCM bytes of silence
    """
    num_samples = int(sample_rate * duration_ms / 1000)
    return struct.pack(f"<{num_samples}h", *([0] * num_samples))
