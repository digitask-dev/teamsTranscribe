# teamsTranscribe

See also: [README.ja.md](README.ja.md) (Japanese).

`teamsTranscribe` is a Python desktop utility that captures live speech from your microphone and/or system audio output and renders captions in a floating overlay window. It combines PyAudio for audio capture, faster-whisper for high-quality speech recognition, and a PyQt-based overlay so you can keep real-time subtitles on top of applications such as Microsoft Teams, Zoom, or browser-based calls.

> **Proof of concept:** This project is an experimental prototype intended for evaluation and not yet production-hardened.

## Features
- Real-time transcription with low-latency streaming chunks
- Capture sources: microphone only, system loopback only, or a mix of both
- Movable, always-on-top overlay window with a toggleable status panel for live captions and session details
- Automatic language detection with optional overrides via the config file or environment variables
- Simple CLI flags to list available devices and choose the capture mode

## Prerequisites
- Windows 10/11 (WASAPI loopback works out of the box); macOS or Linux are possible but require PortAudio-compatible loopback devices
- Python 3.9 or newer
- Git (optional, for cloning)
- Visual C++ 14+ runtime on Windows (needed for the PyAudio wheel)
- PortAudio development headers on Linux/macOS if you need to compile PyAudio from source
- Optional: a virtual loopback device (e.g., VB-Audio Virtual Cable) if your system does not expose a loopback capture device by default

## Getting Started
1. Clone the repository or download the source zip, then open a terminal in the project root:
   ```powershell
   git clone https://github.com/yourusername/teamsTranscribe.git
   cd teamsTranscribe
   ```
2. Create and activate a virtual environment (recommended):
   ```powershell
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   ```
3. Install the Python dependencies:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   - For GPU acceleration, install a CUDA-enabled wheel by following the official faster-whisper instructions.
4. Review the configuration file at `config/settings.json` and adjust the defaults before launching:
   ```json
   {
     "whisper_model_path": "base",
     "whisper_compute_type": "int8",
     "whisper_language": "auto",
     "whisper_window_seconds": 5,
     "whisper_overlap_seconds": 1,
     "whisper_beam_size": 1
   }
   ```
   - `whisper_model_path`: faster-whisper model name or local path (e.g., `base`, `medium`, `large-v3`).
   - `whisper_compute_type`: `int8`, `float16`, etc., depending on CPU/GPU support.
   - `whisper_language`: `auto` for automatic detection or a language code (e.g., `en`, `ja`).
   - `whisper_window_seconds` / `whisper_overlap_seconds`: control streaming window size and overlap for smoother captions.
   - `whisper_beam_size`: larger values improve accuracy at the cost of speed.
   - Environment variables with the uppercase names (e.g., `WHISPER_MODEL_PATH`) still override the config when set.
   - Set the TEAMS_TRANSCRIBE_CONFIG environment variable to point to an alternate config file if you maintain multiple profiles.

The legacy `.env` file is still loaded automatically, so existing overrides continue to work.

## Managing Configuration from the CLI
Use the `config` subcommand to inspect or update settings without editing JSON manually:

```powershell
python -m src.main config --list
python -m src.main config --set whisper_model_path=medium --set whisper_language=en
```

Key names are case-insensitive and accept either `WHISPER_MODEL_PATH` or `whisper_model_path`. Provide `--config-path` to point at a different JSON file for both the `config` command and the main run mode:

```powershell
python -m src.main config --config-path C:\path\to\custom.json --list
python -m src.main --config-path C:\path\to\custom.json
```

## Running the App
- List available audio devices before launching, so you know which inputs are exposed:
  ```powershell
  python -m src.main --list-devices
  ```
  Look for loopback or virtual devices if you plan to capture system audio.
- Start live transcription (default mixes microphone and system audio when available):
  ```powershell
  python -m src.main
  ```
- Microphone-only capture:
  ```powershell
  python -m src.main --mic-only
  ```
- System-only capture (requires a loopback device, otherwise defaults to microphone):
  ```powershell
  python -m src.main --system-only
  ```

While running, the overlay window stays on top of other apps. Drag it to reposition, use the toggle arrow to reveal per-session status (model, language, compute type), and click the `X` button to close. The terminal logs will show which devices were selected and whether voice activity detection had to fall back due to missing optional dependencies (e.g., `onnxruntime`).

## Building / Installing on Your PC
- Editable install in the active environment (handy for local development):
  ```powershell
  pip install -e .
  ```
- Build a wheel/sdist for distribution (requires `pip install build` once):
  ```powershell
  python -m build
  ```
  The artifacts will be created under `dist/`, and you can install them on another machine with `pip install dist/teamsTranscribe-<version>-py3-none-any.whl`.

## Troubleshooting
- **PyAudio install failures**: install the Visual C++ Build Tools on Windows or PortAudio headers on Linux/macOS, then retry `pip install pyaudio`.
- **No system audio captured**: ensure your audio driver exposes a WASAPI loopback device or install a virtual audio cable.
- **Slow transcription**: switch to a smaller model (`tiny`, `base`) or reduce beam size. For better performance, use a GPU build of faster-whisper.
- **Overlay does not appear**: PyQt needs access to a desktop session; ensure you are not running headless and that `QT_QPA_PLATFORM` is unset or set to `windows`/`xcb` as appropriate.

## License
This project is distributed under the GNU Affero General Public License v3.0 (AGPL-3.0), allowing free use, modification, and redistribution provided that network-accessible deployments also share their source under the same terms.




