from __future__ import annotations

from functools import lru_cache

from faster_whisper import WhisperModel

from config import Settings


@lru_cache(maxsize=1)
def _load_model(model_path: str, compute_type: str) -> WhisperModel:
    print(
        f"Loading faster-whisper model '{model_path}' (compute_type={compute_type})"
    )
    return WhisperModel(model_path, device="auto", compute_type=compute_type)


def get_model(settings: Settings) -> WhisperModel:
    return _load_model(settings.whisper_model_path, settings.whisper_compute_type)
