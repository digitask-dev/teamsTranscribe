import argparse
import json
import sys
import types

import pytest

from src.config import Settings


def _make_settings() -> Settings:
    return Settings(
        sample_rate=16000,
        chunk_samples=4000,
        window_seconds=1.5,
        overlap_seconds=0.4,
        whisper_model_path="base",
        whisper_compute_type="int8",
        whisper_beam_size=1,
        whisper_language=None,
    )


def test_handle_config_list_when_missing_file(tmp_path, capsys):
    args = argparse.Namespace(set=[], list=True, config_path=str(tmp_path / "missing.json"))
    from src import main  # Import here if needed, but this test doesn't call main.main()
    main.handle_config_command(args)
    captured = capsys.readouterr()
    assert "No configuration file found." in captured.out


def test_handle_config_set_updates_config_file(tmp_path, capsys):
    config_path = tmp_path / "settings.json"
    config_path.write_text("{}", encoding="utf-8")

    args = argparse.Namespace(
        set=["WHISPER_MODEL_PATH=medium", "whisper_language=en"],
        list=False,
        config_path=str(config_path),
    )

    from src import main
    main.handle_config_command(args)
    captured = capsys.readouterr()
    assert "Updated configuration" in captured.out

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["whisper_model_path"] == "medium"
    assert data["whisper_language"] == "en"


def test_handle_config_set_unknown_key_exits(tmp_path, capsys):
    config_path = tmp_path / "settings.json"
    args = argparse.Namespace(set=["NOT_A_KEY=value"], list=False, config_path=str(config_path))

    from src import main
    with pytest.raises(SystemExit) as excinfo:
        main.handle_config_command(args)

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "Unknown config key" in captured.err
    assert not config_path.exists()


def test_main_list_devices_invokes_helper(monkeypatch):
    called = []

    from src import main

    def mock_parse_args():
        return argparse.Namespace(list_devices=True, command=None)

    monkeypatch.setattr(main, "parse_args", mock_parse_args)
    monkeypatch.setattr(main, "list_audio_devices", lambda: called.append(True))

    main.main()
    assert called == [True]


class _OverlayProbe:
    def __init__(self):
        self.status_calls = []

    def set_status_info(self, model, language, compute):
        self.status_calls.append((model, language, compute))


def _patch_runtime_dependencies(monkeypatch, settings=None):
    overlay_instances = []

    def overlay_factory():
        instance = _OverlayProbe()
        overlay_instances.append(instance)
        return instance

    if settings is None:
        settings = _make_settings()

    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setattr("src.main.OverlayWindow", overlay_factory)
    monkeypatch.setattr("src.main.load_settings", lambda config_path=None: settings)

    thread_args = {}

    def fake_start_thread(*, overlay, settings, mic_only, system_only):
        thread_args["call"] = {
            "overlay": overlay,
            "settings": settings,
            "mic_only": mic_only,
            "system_only": system_only,
        }
        return types.SimpleNamespace()

    monkeypatch.setattr("src.main.start_transcription_thread", fake_start_thread)

    exit_called = {}

    def fake_exit(code=0):
        exit_called["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", fake_exit)

    try:
        from PyQt5.QtWidgets import QApplication
        monkeypatch.setattr(QApplication, "exec_", lambda self: 0)
    except ImportError:
        pass

    return overlay_instances, thread_args, exit_called


def test_main_default_starts_combined_transcription(monkeypatch):
    overlay_instances, thread_args, exit_called = _patch_runtime_dependencies(monkeypatch)

    from src import main
    with pytest.raises(SystemExit):
        main.main()

    assert overlay_instances, "Overlay should be instantiated"
    call = thread_args["call"]
    assert call["mic_only"] is False
    assert call["system_only"] is False
    assert call["overlay"] is overlay_instances[0]
    assert exit_called["code"] == 0


def test_main_mic_only_triggers_mic_transcription(monkeypatch):
    overlay_instances, thread_args, exit_called = _patch_runtime_dependencies(monkeypatch)
    sys.argv.append("--mic-only")

    from src import main
    with pytest.raises(SystemExit):
        main.main()

    call = thread_args["call"]
    assert call["mic_only"] is True
    assert call["system_only"] is False
    assert exit_called["code"] == 0


def test_main_system_only_triggers_system_transcription(monkeypatch):
    overlay_instances, thread_args, exit_called = _patch_runtime_dependencies(monkeypatch)
    sys.argv.append("--system-only")

    from src import main
    with pytest.raises(SystemExit):
        main.main()

    call = thread_args["call"]
    assert call["mic_only"] is False
    assert call["system_only"] is True
    assert exit_called["code"] == 0


def test_main_uses_custom_config_path(monkeypatch, tmp_path):
    custom_config = tmp_path / "custom.json"
    custom_config.write_text("{}", encoding="utf-8")

    settings = _make_settings()

    overlay_instances, thread_args, exit_called = _patch_runtime_dependencies(
        monkeypatch, settings=settings
    )
    sys.argv.extend(["--config-path", str(custom_config)])

    captured_paths = {}

    def fake_load_settings(*, config_path=None):
        captured_paths["config_path"] = config_path
        return settings

    monkeypatch.setattr("src.main.load_settings", fake_load_settings)

    from src import main
    with pytest.raises(SystemExit):
        main.main()

    assert captured_paths["config_path"] == str(custom_config)
    assert exit_called["code"] == 0

