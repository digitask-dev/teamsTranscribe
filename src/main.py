import argparse
import sys
import threading
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from dotenv import load_dotenv

from audio_capture import list_audio_devices
from config import Settings, load_settings
from overlay import OverlayWindow
from transcription import transcribe_audio, transcribe_both_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live audio transcription")
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
    return parser.parse_args()


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

    if args.list_devices:
        list_audio_devices()
        return

    settings = load_settings()

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
