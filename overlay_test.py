import sys
from pathlib import Path
root = Path('.').resolve()
for candidate in (root / 'src', root):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

print('before import overlay', flush=True)
from tests.test_transcription import _OverlayRecorder
print('after import overlay', flush=True)
overlay = _OverlayRecorder()
print('overlay created', flush=True)
