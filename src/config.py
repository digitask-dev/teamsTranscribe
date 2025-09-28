from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Union


DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_SAMPLES = 4096

_CONFIG_KEYS = {
    "WHISPER_MODEL_PATH",
    "WHISPER_COMPUTE_TYPE",
    "WHISPER_LANGUAGE",
    "WHISPER_WINDOW_SECONDS",
    "WHISPER_OVERLAP_SECONDS",
    "WHISPER_BEAM_SIZE",
}
_CONFIG_KEYS_LOOKUP = {key.lower(): key for key in _CONFIG_KEYS}

CONFIG_ENV_VAR = "TEAMS_TRANSCRIBE_CONFIG"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.json"


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


def _flatten_config_data(raw: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}

    items: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        normalized = key.strip().lower()
        if not normalized:
            continue
        composite = f"{prefix}_{normalized}" if prefix else normalized
        if isinstance(value, Mapping):
            items.update(_flatten_config_data(value, composite))
        else:
            items[composite] = value
    return items


def _resolve_config_path(config_path: Optional[Union[str, Path]]) -> Path:
    if config_path is not None:
        return Path(config_path)
    env_override = os.environ.get(CONFIG_ENV_VAR)
    if env_override:
        return Path(env_override)
    return DEFAULT_CONFIG_PATH


def _load_config_values(config_path: Optional[Union[str, Path]] = None) -> dict[str, Any]:
    path = _resolve_config_path(config_path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}

    flattened = _flatten_config_data(raw)
    values: dict[str, Any] = {}
    for key, value in flattened.items():
        standardized = _CONFIG_KEYS_LOOKUP.get(key)
        if standardized:
            values[standardized] = value
    return values


def _parse_float(value: Optional[Any], default: float, minimum: float) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, minimum)


def _parse_int(value: Optional[Any], default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_to_str(value: Any, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)



def normalize_config_key(key: str) -> str | None:
    if not isinstance(key, str):
        return None
    normalized = key.strip().lower()
    if not normalized:
        return None
    return _CONFIG_KEYS_LOOKUP.get(normalized)


def load_config_dict(config_path: Optional[Union[str, Path]] = None) -> dict[str, Any]:
    path = _resolve_config_path(config_path)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, Mapping):
        return {}
    return dict(data)


def update_config_file(
    updates: Mapping[str, Any],
    *,
    config_path: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    if not updates:
        return load_config_dict(config_path)

    normalized_updates: dict[str, Any] = {}
    for key, value in updates.items():
        canonical = normalize_config_key(key)
        if canonical is None:
            raise KeyError(f"Unknown config key: {key}")
        normalized_updates[canonical] = value

    current = load_config_dict(config_path)
    result = dict(current)
    for canonical, value in normalized_updates.items():
        result[canonical.lower()] = value

    path = _resolve_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return result


def load_settings(
    env: Optional[Mapping[str, Any]] = None,
    *,
    config_path: Optional[Union[str, Path]] = None,
) -> Settings:
    config_values = _load_config_values(config_path)
    merged: dict[str, Any] = dict(config_values)
    source_env = dict(env) if env is not None else dict(os.environ)
    merged.update(source_env)

    window_seconds = _parse_float(merged.get("WHISPER_WINDOW_SECONDS"), 1.5, 0.5)
    overlap_seconds = _parse_float(merged.get("WHISPER_OVERLAP_SECONDS"), 0.4, 0.0)
    beam_size = _parse_int(merged.get("WHISPER_BEAM_SIZE"), 1)

    language_raw = merged.get("WHISPER_LANGUAGE")
    if language_raw is None:
        language_str = "auto"
    elif isinstance(language_raw, str):
        language_str = language_raw
    else:
        language_str = str(language_raw)
    language = None if language_str.lower() == "auto" else language_str

    return Settings(
        sample_rate=DEFAULT_SAMPLE_RATE,
        chunk_samples=DEFAULT_CHUNK_SAMPLES,
        window_seconds=window_seconds,
        overlap_seconds=overlap_seconds,
        whisper_model_path=_coerce_to_str(merged.get("WHISPER_MODEL_PATH"), "base"),
        whisper_compute_type=_coerce_to_str(merged.get("WHISPER_COMPUTE_TYPE"), "int8"),
        whisper_beam_size=beam_size,
        whisper_language=language,
    )


CONFIG_KEYS = frozenset(_CONFIG_KEYS)