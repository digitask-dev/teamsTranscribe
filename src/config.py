from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Mapping


DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_SAMPLES = 4096


@dataclass(frozen=True)
class Settings:
    sample_rate: int
    chunk_samples: int
    window_seconds: float
    overlap_seconds: float
    whisper_model_path: str
    whisper_compute_type: str
    whisper_beam_size: int
    whisper_language: Optional[str]


def _parse_float(value: Optional[str], default: float, minimum: float) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, minimum)


def _parse_int(value: Optional[str], default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = env or os.environ

    window_seconds = _parse_float(env.get("WHISPER_WINDOW_SECONDS"), 1.5, 0.5)
    overlap_seconds = _parse_float(env.get("WHISPER_OVERLAP_SECONDS"), 0.4, 0.0)
    beam_size = _parse_int(env.get("WHISPER_BEAM_SIZE"), 1)

    language_override = env.get("WHISPER_LANGUAGE", "auto")
    language = None if language_override.lower() == "auto" else language_override

    return Settings(
        sample_rate=DEFAULT_SAMPLE_RATE,
        chunk_samples=DEFAULT_CHUNK_SAMPLES,
        window_seconds=window_seconds,
        overlap_seconds=overlap_seconds,
        whisper_model_path=env.get("WHISPER_MODEL_PATH", "base"),
        whisper_compute_type=env.get("WHISPER_COMPUTE_TYPE", "int8"),
        whisper_beam_size=beam_size,
        whisper_language=language,
    )
