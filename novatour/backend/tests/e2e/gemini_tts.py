"""Gemini TTS client for generating test audio fixtures.

Synthesizes English utterances via gemini-2.5-flash-preview-tts,
resamples to 16kHz mono PCM (NovaTour's input format), and caches
results to avoid re-generation across test runs.
"""

from __future__ import annotations

import base64
import hashlib
import io
import subprocess
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from google import genai
from google.genai import types

TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_VOICE = "Kore"  # English female voice
TARGET_SAMPLE_RATE = 16000
CACHE_DIR = Path("/tmp/novatour_tts_cache")


def _parse_sample_rate_from_mime(mime_type: str, default: int = 24000) -> int:
    import re
    m = re.search(r"rate=(\d+)", mime_type or "", re.IGNORECASE)
    return int(m.group(1)) if m else default


def _wav_bytes_to_mono_int16(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    if sw == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.int16)
    elif sw == 1:
        u8 = np.frombuffer(raw, dtype=np.uint8).astype(np.int16)
        samples = ((u8 - 128) << 8).astype(np.int16)
    elif sw == 4:
        samples = (np.frombuffer(raw, dtype="<i4") >> 16).astype(np.int16)
    else:
        raise ValueError(f"Unsupported WAV sample width: {sw}")

    if channels > 1:
        samples = samples.reshape(-1, channels).astype(np.int32).mean(axis=1).astype(np.int16)
    return samples, sr


def _resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or len(samples) == 0:
        return np.asarray(samples, dtype=np.int16)
    src_len = len(samples)
    dst_len = max(1, int(round(src_len * (dst_rate / float(src_rate)))))
    src_x = np.linspace(0, 1, src_len, endpoint=False, dtype=np.float64)
    dst_x = np.linspace(0, 1, dst_len, endpoint=False, dtype=np.float64)
    dst = np.interp(dst_x, src_x, samples.astype(np.float64))
    return np.clip(np.round(dst), -32768, 32767).astype(np.int16)


def _smoothness(samples: np.ndarray) -> float:
    if samples.size < 2:
        return float("inf")
    return float(np.abs(np.diff(samples.astype(np.int32))).mean())


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()[:16]


class GeminiTTS:
    """Generates test audio via Gemini TTS with local file caching."""

    def __init__(self, api_key: str, cache_dir: Path = CACHE_DIR):
        self.client = genai.Client(api_key=api_key)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to 16kHz mono PCM bytes. Uses cache if available."""
        key = _cache_key(text)
        cached = self.cache_dir / f"{key}.pcm"
        if cached.exists():
            return cached.read_bytes()

        try:
            pcm = self._generate_via_gemini(text)
        except Exception as e:
            print(f"[GeminiTTS] API failed ({e}), falling back to macOS say")
            pcm = self._fallback_macos_say(text)

        cached.write_bytes(pcm)
        return pcm

    def _generate_via_gemini(self, text: str) -> bytes:
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE)
            ),
        )
        response = self.client.models.generate_content(
            model=TTS_MODEL,
            contents=text.strip(),
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config,
            ),
        )
        audio_data, mime_type = self._extract_audio(response)
        mime_lower = mime_type.lower()

        if "audio/wav" in mime_lower or "audio/x-wav" in mime_lower:
            src_samples, src_rate = _wav_bytes_to_mono_int16(audio_data)
        elif "audio/pcm" in mime_lower or "audio/l16" in mime_lower:
            src_rate = _parse_sample_rate_from_mime(mime_type, 24000)
            usable = len(audio_data) - (len(audio_data) % 2)
            if "audio/l16" in mime_lower:
                le = np.frombuffer(audio_data[:usable], dtype="<i2").astype(np.int16)
                be = np.frombuffer(audio_data[:usable], dtype=">i2").astype(np.int16)
                src_samples = le if _smoothness(le) <= _smoothness(be) else be
            else:
                src_samples = np.frombuffer(audio_data[:usable], dtype="<i2").astype(np.int16)
        else:
            raise RuntimeError(f"Unsupported TTS mime type: {mime_type}")

        dst_samples = _resample(src_samples, src_rate, TARGET_SAMPLE_RATE)
        return dst_samples.tobytes()

    @staticmethod
    def _extract_audio(response: types.GenerateContentResponse) -> tuple[bytes, str]:
        for part in (response.parts or []):
            if part.inline_data and part.inline_data.data:
                data = part.inline_data.data
                if isinstance(data, str):
                    try:
                        data = base64.b64decode(data, validate=True)
                    except Exception:
                        data = data.encode("utf-8")
                return data, part.inline_data.mime_type or "application/octet-stream"
        raise RuntimeError("TTS response contains no inline audio data")

    @staticmethod
    def _fallback_macos_say(text: str) -> bytes:
        """Use macOS 'say' command as TTS fallback."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
            aiff_path = f.name
        try:
            subprocess.run(
                ["say", "-o", aiff_path, "--data-format=LEI16@16000", text],
                check=True, capture_output=True, timeout=30,
            )
            with wave.open(aiff_path, "rb") as wf:
                raw = wf.readframes(wf.getnframes())
            return raw
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Generate 2 seconds of silence as last resort
            return np.zeros(TARGET_SAMPLE_RATE * 2, dtype=np.int16).tobytes()
        finally:
            Path(aiff_path).unlink(missing_ok=True)


def generate_silence(duration_ms: int = 500) -> bytes:
    """Generate silent PCM audio (16kHz, 16-bit, mono)."""
    num_samples = int(TARGET_SAMPLE_RATE * duration_ms / 1000)
    return np.zeros(num_samples, dtype=np.int16).tobytes()
