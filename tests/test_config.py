import json

from src.config import load_settings


def test_load_settings_env_overrides(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.json"
    config_path.write_text(
        json.dumps({"whisper_model_path": "base", "whisper_beam_size": 1}),
        encoding="utf-8",
    )

    monkeypatch.setenv("WHISPER_MODEL_PATH", "large")
    monkeypatch.setenv("WHISPER_BEAM_SIZE", "3")
    monkeypatch.setenv("WHISPER_LANGUAGE", "en")

    settings = load_settings(config_path=str(config_path))
    assert settings.whisper_model_path == "large"
    assert settings.whisper_beam_size == 3
    assert settings.whisper_language == "en"


def test_load_settings_handles_bad_json(tmp_path):
    config_path = tmp_path / "settings.json"
    config_path.write_text("not-json", encoding="utf-8")

    settings = load_settings(config_path=str(config_path))
    assert settings.whisper_model_path == "base"
    assert settings.whisper_compute_type == "int8"
    assert settings.whisper_language is None
