import argparse
import sys
import threading
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from dotenv import load_dotenv

from audio_capture import list_audio_devices
from config import (
    CONFIG_KEYS,
    Settings,
    load_config_dict,
    load_settings,
    normalize_config_key,
    update_config_file,
)
from overlay import OverlayWindow
from transcription import transcribe_audio, transcribe_both_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live audio transcription")
    parser.add_argument(
        "--config-path",
        help="Path to a JSON config file (defaults to the bundled settings)",
    )
    parser.add_argument(
        "--mic-only",
        action="store_true",
        help="Capture microphone audio only",
    )
    parser.add_argument(
        "--system-only",
        action="store_true",
        help="Capture system audio output only",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )

    subparsers = parser.add_subparsers(dest="command", required=False)
    parser.set_defaults(command="run")

    config_parser = subparsers.add_parser(
        "config",
        help="Inspect or update the persistent configuration file",
    )
    config_parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Update a configuration key (repeat to set multiple values)",
    )
    config_parser.add_argument(
        "--list",
        action="store_true",
        help="Print the current configuration values",
    )

    return parser.parse_args()


def _parse_config_override(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise ValueError(f"Invalid config override '{raw}'. Expected KEY=VALUE.")
    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Invalid config override '{raw}'. Missing key.")
    return key, value


def _collect_config_overrides(raw_pairs: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for raw in raw_pairs:
        key, value = _parse_config_override(raw)
        canonical = normalize_config_key(key)
        if canonical is None:
            raise KeyError(key)
        overrides[canonical] = value
    return overrides


def _print_config_values(config_data: dict[str, object]) -> None:
    if not config_data:
        print("No configuration file found.")
        return

    print("Current configuration:")
    for key in sorted(config_data):
        canonical = normalize_config_key(key)
        display_key = canonical if canonical is not None else key.upper()
        value = config_data[key]
        print(f"  {display_key}={value}")


def handle_config_command(args: argparse.Namespace) -> None:
    try:
        overrides = _collect_config_overrides(args.set or [])
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc
    except KeyError as exc:
        valid = ", ".join(sorted(CONFIG_KEYS))
        print(
            f"Unknown config key '{exc.args[0]}'. Valid keys: {valid}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    if not overrides and not args.list:
        print(
            "No configuration changes specified. Use --set KEY=VALUE or --list.",
            file=sys.stderr,
        )
        return

    snapshot = None
    if overrides:
        snapshot = update_config_file(overrides, config_path=args.config_path)
        print("Updated configuration:")
        for key in sorted(overrides):
            stored_value = snapshot.get(key.lower()) if snapshot else overrides[key]
            print(f"  {key}={stored_value}")

    if args.list:
        if snapshot is None:
            snapshot = load_config_dict(args.config_path)
        if overrides:
            print()
        _print_config_values(snapshot or {})


def start_transcription_thread(
    overlay: OverlayWindow,
    settings: Settings,
    mic_only: bool,
    system_only: bool,
) -> threading.Thread:
    if mic_only:
        target = transcribe_audio
        kwargs = {"overlay": overlay, "settings": settings, "use_system_audio": False}
    elif system_only:
        target = transcribe_audio
        kwargs = {"overlay": overlay, "settings": settings, "use_system_audio": True}
    else:
        target = transcribe_both_audio
        kwargs = {"overlay": overlay, "settings": settings}

    thread = threading.Thread(target=target, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
    args = parse_args()

    if args.command == "config":
        handle_config_command(args)
        return

    if args.list_devices:
        list_audio_devices()
        return

    settings = load_settings(config_path=args.config_path)

    app = QApplication(sys.argv)
    overlay = OverlayWindow()

    start_transcription_thread(
        overlay=overlay,
        settings=settings,
        mic_only=args.mic_only,
        system_only=args.system_only,
    )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()