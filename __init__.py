from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent / "src"
_SRC_PATH = str(_SRC_DIR)
if _SRC_DIR.is_dir() and _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

_main_module = import_module("main")
main = _main_module.main

__all__ = ["main"]